import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from apps.common.encryption import EncryptedJSONField, EncryptedTextField


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True, default="")
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # 2FA fields
    totp_secret = EncryptedTextField(blank=True, null=True)
    totp_recovery_codes = EncryptedJSONField(blank=True, null=True)
    totp_enabled = models.BooleanField(default=False)

    # Workspace persistence
    last_workspace_id = models.UUIDField(blank=True, null=True)

    # Terms of Service acceptance (null = not yet accepted)
    tos_accepted_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        if self.name:
            return self.name
        if self.email:
            return self.email.split("@")[0]
        return "User"


class OAuthConnection(models.Model):
    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        GITHUB = "github", "GitHub"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="oauth_connections")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_user_id = models.CharField(max_length=255)
    provider_email = models.EmailField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_oauth_connection"
        unique_together = [("provider", "provider_user_id")]

    def __str__(self):
        return f"{self.user.email} - {self.provider}"


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_sessions")
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    device_info = models.CharField(max_length=500, blank=True, default="")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    last_active_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "accounts_session"

    def __str__(self):
        return f"Session for {self.user.email}"


class ApiToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_tokens")
    name = models.CharField(max_length=100)
    token_prefix = models.CharField(max_length=12, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    scoped_workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="api_tokens",
    )
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_api_token"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.token_prefix}…) for {self.user.email}"

    @property
    def is_active(self):
        from django.utils import timezone

        if self.revoked_at is not None:
            return False
        return not (self.expires_at is not None and self.expires_at < timezone.now())
