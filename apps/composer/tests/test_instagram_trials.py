from apps.composer.models import PlatformPost
from apps.composer.services import require_publishable
from apps.composer.tests.test_account_scope import AccountScopeTestsBase
from apps.social_accounts.models import SocialAccount


class InstagramTrialTests(AccountScopeTestsBase):
    def setUp(self):
        super().setUp()
        self.instagram = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="instagram_login",
            account_platform_id="ig-1",
            account_name="Creator",
        )
        self.pp = PlatformPost.objects.create(post=self.post, social_account=self.instagram)
        self.video = self._attach("video", "trial.mp4", post=self.post)

    def payload(self, strategy, action="save_draft"):
        account_id = str(self.instagram.id)
        return self._payload(
            **{
                "action": action,
                "selected_accounts": account_id,
                "account_scope": account_id,
                f"instagram_trial_panel_{account_id}": "1",
                f"instagram_trial_strategy_{account_id}": strategy,
            }
        )

    def test_choice_survives_save_version_and_clone(self):
        from apps.composer.services import clone_post

        response = self.client.post(self.save_url, self.payload("MANUAL"))
        self.assertIn(response.status_code, (200, 204, 302))
        self.pp.refresh_from_db()
        self.assertEqual(self.pp.platform_extra, {"trial_reel_graduation_strategy": "MANUAL"})
        snapshot = self.post.versions.latest("created_at").snapshot
        self.assertTrue(
            any(
                x["platform_extra"].get("trial_reel_graduation_strategy") == "MANUAL"
                for x in snapshot["platform_posts"]
            )
        )
        cloned = clone_post(self.post, author=self.user)
        self.assertEqual(
            cloned.platform_posts.get(social_account=self.instagram).platform_extra, self.pp.platform_extra
        )

    def test_non_composer_save_preserves_trial(self):
        self.pp.platform_extra = {"trial_reel_graduation_strategy": "MANUAL"}
        self.pp.save()
        data = self.payload("MANUAL")
        del data[f"instagram_trial_panel_{self.instagram.id}"]
        del data[f"instagram_trial_strategy_{self.instagram.id}"]
        self.client.post(self.save_url, data)
        self.pp.refresh_from_db()
        self.assertEqual(self.pp.platform_extra["trial_reel_graduation_strategy"], "MANUAL")

    def test_regular_choice_removes_only_trial_setting(self):
        self.pp.platform_extra = {"trial_reel_graduation_strategy": "MANUAL", "other": "kept"}
        self.pp.save()
        self.client.post(self.save_url, self.payload(""))
        self.pp.refresh_from_db()
        self.assertEqual(self.pp.platform_extra, {"other": "kept"})

    def test_trial_media_replacement_cannot_publish_as_regular(self):
        self.pp.platform_extra = {"trial_reel_graduation_strategy": "MANUAL"}
        self.pp.save()
        self.video.media_type = "image"
        self.video.save()
        with self.assertRaisesMessage(ValueError, "exactly one video"):
            require_publishable(self.pp)

    def test_multiple_videos_cannot_schedule_as_trial(self):
        self.pp.platform_extra = {"trial_reel_graduation_strategy": "MANUAL"}
        self.pp.save()
        self._attach("video", "second.mp4", post=self.post)
        with self.assertRaisesMessage(ValueError, "exactly one video"):
            require_publishable(self.pp)

    def test_changed_mode_requires_fresh_approval(self):
        self.workspace.approval_workflow_mode = "required_internal"
        self.workspace.save()
        self.pp.status = "approved"
        self.pp.platform_extra = {"trial_reel_graduation_strategy": "MANUAL"}
        self.pp.save()
        self.client.post(self.save_url, self.payload("SS_PERFORMANCE"))
        self.pp.refresh_from_db()
        self.assertEqual(self.pp.status, "pending_review")

    def test_trial_sharing_mode_is_visible_to_reviewer(self):
        from django.template.loader import render_to_string

        self.pp.platform_extra = {"trial_reel_graduation_strategy": "SS_PERFORMANCE"}
        self.pp.save()
        html = render_to_string(
            "approvals/partials/_approval_row.html", {"post": self.post, "workspace": self.workspace}
        )
        self.assertIn("automatic sharing if it performs well", html)

    def test_autosave_keeps_mode_and_reopens_approval(self):
        self.pp.status = "approved"
        self.pp.platform_extra = {"trial_reel_graduation_strategy": "MANUAL"}
        self.pp.save()
        response = self.client.post(self.autosave_url, self.payload("SS_PERFORMANCE"))
        self.assertEqual(response.status_code, 200)
        self.pp.refresh_from_db()
        self.assertEqual(self.pp.platform_extra["trial_reel_graduation_strategy"], "SS_PERFORMANCE")
        self.assertEqual(self.pp.status, "pending_review")

    def test_client_reviewer_sees_trial_mode(self):
        from django.template.loader import render_to_string

        self.pp.platform_extra = {"trial_reel_graduation_strategy": "MANUAL"}
        self.pp.save()
        html = render_to_string("partials/_instagram_trial_mode.html", {"pp": self.pp})
        self.assertIn("manual sharing", html)

    def test_scheduled_and_client_reviewed_audiences_are_locked(self):
        for status in ("scheduled", "pending_client", "on_hold"):
            for url in (self.save_url, self.autosave_url):
                with self.subTest(status=status, url=url):
                    self.pp.status = status
                    self.pp.platform_extra = {"trial_reel_graduation_strategy": "MANUAL"}
                    self.pp.save()
                    response = self.client.post(url, self.payload("SS_PERFORMANCE"))
                    self.assertEqual(response.status_code, 400)
                    self.pp.refresh_from_db()
                    self.assertEqual(self.pp.status, status)
                    self.assertEqual(self.pp.platform_extra["trial_reel_graduation_strategy"], "MANUAL")
