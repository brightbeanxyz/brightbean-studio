"""Bump StudioCheckoutAttempt.checkout_url from max_length=200 (URLField
default) to max_length=2000.

Mirror of the same change on Intelligence side
(``apps/internal_api/migrations/0004_alter_studiocheckoutattempt_checkout_url.py``).
Stripe's hosted Checkout URL is ~500-1000+ characters once the fragment
hash is included; 200 was the silent default from ``URLField`` and would
cause ``DataError: value too long for type character varying(200)`` on
Postgres when Studio's TX2 tried to persist the URL returned by
Intelligence.

Metadata-only ALTER COLUMN — runs in milliseconds.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("intelligence", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="studiocheckoutattempt",
            name="checkout_url",
            field=models.URLField(blank=True, default="", max_length=2000),
        ),
    ]
