"""LinkedIn document posts: a PDF uploaded through the Documents API and posted as media.

No network: ``_request`` and the binary upload are mocked, and the status
poll is checked call by call.
"""

from unittest.mock import MagicMock, patch

import pytest

from providers.exceptions import PublishError
from providers.linkedin import LinkedInProvider
from providers.types import PostType, PublishContent

ORG = "urn:li:organization:42"
DOC = "urn:li:document:D123"


def _response(payload=None, headers=None):
    resp = MagicMock()
    resp.json = MagicMock(return_value=payload or {})
    resp.headers = headers or {}
    return resp


def _content(**kwargs):
    defaults = dict(
        text="Our process (in 5 steps)",
        media_files=["/tmp/report.pdf"],
        media_urls=["https://studio.example/media/media_library/2026/11/Sales%20playbook.pdf"],
        media_types=["document"],
        post_type=PostType.DOCUMENT,
        extra={"author": ORG},
    )
    defaults.update(kwargs)
    return PublishContent(**defaults)


@pytest.fixture
def provider():
    with (
        patch.object(LinkedInProvider, "_request") as request,
        patch.object(LinkedInProvider, "_upload_binary") as upload,
        patch("providers.base.time.sleep"),
    ):
        request.side_effect = [
            _response({"value": {"uploadUrl": "https://upload.example/doc", "document": DOC}}),
            _response({"status": "WAITING_UPLOAD"}),
            _response({"status": "AVAILABLE"}),
            _response(headers={"x-restli-id": "urn:li:share:7"}),
        ]
        p = LinkedInProvider()
        p.request, p.upload = request, upload
        yield p


def test_linkedin_supports_document_posts():
    p = LinkedInProvider()
    assert PostType.DOCUMENT in p.supported_post_types


def test_uploads_waits_and_posts_the_document_with_its_title(provider):
    result = provider.publish_post("token", _content(title="Sales playbook"))

    init, first_check, second_check, post = provider.request.call_args_list
    assert init.args == ("POST", "https://api.linkedin.com/rest/documents")
    assert init.kwargs["params"] == {"action": "initializeUpload"}
    assert init.kwargs["json"] == {"initializeUploadRequest": {"owner": ORG}}
    provider.upload.assert_called_once_with("token", "https://upload.example/doc", "/tmp/report.pdf")
    assert first_check.args == ("GET", "https://api.linkedin.com/rest/documents/urn%3Ali%3Adocument%3AD123")
    assert second_check.args == first_check.args
    assert post.args == ("POST", "https://api.linkedin.com/rest/posts")
    body = post.kwargs["json"]
    assert body["author"] == ORG
    assert body["commentary"] == "Our process \\(in 5 steps\\)"
    assert body["content"] == {"media": {"id": DOC, "title": "Sales playbook"}}
    assert result.platform_post_id == "urn:li:share:7"
    assert result.extra["document_urn"] == DOC


def test_without_a_title_the_file_name_is_used(provider):
    provider.publish_post("token", _content(title=""))

    body = provider.request.call_args_list[-1].kwargs["json"]
    assert body["content"]["media"]["title"] == "Sales playbook.pdf"


def test_a_document_linkedin_rejects_fails_before_posting():
    with (
        patch.object(LinkedInProvider, "_request") as request,
        patch.object(LinkedInProvider, "_upload_binary"),
    ):
        request.side_effect = [
            _response({"value": {"uploadUrl": "https://upload.example/doc", "document": DOC}}),
            _response({"status": "PROCESSING_FAILED", "processingFailureReason": "too many pages"}),
        ]
        with pytest.raises(PublishError, match="rejected the document during processing: too many pages"):
            LinkedInProvider().publish_post("token", _content())

    assert request.call_count == 2  # never reached /rest/posts


def test_a_failed_initialize_raises():
    with (
        patch.object(LinkedInProvider, "_request", return_value=_response({"value": {}})),
        pytest.raises(PublishError, match="initialize LinkedIn document upload"),
    ):
        LinkedInProvider().publish_post("token", _content())
