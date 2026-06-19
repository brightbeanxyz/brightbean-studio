from pathlib import Path

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.urls import reverse

from apps.composer.views import preview
from apps.social_accounts.models import SocialAccount

from .test_unsplash import ComposerTestCase


class ComposerPreviewTests(ComposerTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.preview_url = reverse("composer:preview", kwargs={"workspace_id": self.workspace.id})
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="facebook",
            account_platform_id="facebook-page-1",
            account_name="Facebook Page",
        )

    def _preview_post(self, data):
        request = self.factory.post(self.preview_url, data)
        request.user = self.user
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        return preview(request, self.workspace.id)

    def test_compose_page_posts_live_preview_form_data(self):
        template = Path("templates/composer/compose.html").read_text()

        self.assertIn("hx-post=\"{% url 'composer:preview' workspace_id=workspace.id %}\"", template)
        self.assertNotIn("hx-get=\"{% url 'composer:preview' workspace_id=workspace.id %}\"", template)

    def test_preview_accepts_large_caption_in_post_body(self):
        caption = "Long preview caption. " * 300

        response = self._preview_post(
            {
                "title": "Preview title",
                "caption": caption,
                "selected_accounts": str(self.account.id),
            },
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Facebook Page", content)
        self.assertIn("6600/63206", content)
        self.assertIn("Long preview caption. Long preview caption.", content)

    def test_preview_rejects_get_requests(self):
        response = self.client.get(
            self.preview_url,
            {
                "caption": "This belongs in the request body.",
                "selected_accounts": str(self.account.id),
            },
        )

        self.assertEqual(response.status_code, 405)
