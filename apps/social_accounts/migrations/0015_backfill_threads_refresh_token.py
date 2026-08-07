from django.db import migrations


def backfill_threads_refresh_token(apps, schema_editor):
    """Adopt the long-lived access token as the refresh credential for Threads.

    Threads issues no separate refresh token — the access token is replayed
    against ``th_refresh_token``. Until the provider started returning it as
    ``OAuthTokens.refresh_token``, connects stored an empty ``oauth_refresh_token``,
    and every refresh path skips accounts with an empty one. Those accounts would
    keep sitting out the refresh cycle until their 60-day token lapsed, so seed
    the credential they should have had.

    Tokens are encrypted at rest, so this iterates instead of using .update():
    the column holds ciphertext, so neither the empty-value filter nor the copy
    can be expressed in SQL. ``.iterator()`` keeps the decrypted tokens from
    piling up in memory on a large deployment.
    """
    SocialAccount = apps.get_model("social_accounts", "SocialAccount")
    for account in SocialAccount.objects.filter(platform="threads").iterator():
        if account.oauth_refresh_token or not account.oauth_access_token:
            continue
        account.oauth_refresh_token = account.oauth_access_token
        account.save(update_fields=["oauth_refresh_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("social_accounts", "0014_socialaccount_webhook_error_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_threads_refresh_token, migrations.RunPython.noop),
    ]
