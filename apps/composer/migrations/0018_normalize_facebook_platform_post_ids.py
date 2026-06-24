from django.db import migrations


def normalize_facebook_platform_post_ids(apps, schema_editor):
    PlatformPost = apps.get_model("composer", "PlatformPost")

    queryset = PlatformPost.objects.filter(
        social_account__platform="facebook",
        platform_post_id__contains="_",
    ).exclude(platform_post_id="")

    for platform_post in queryset.iterator():
        platform_post.platform_post_id = str(platform_post.platform_post_id).rsplit("_", 1)[1]
        platform_post.save(update_fields=["platform_post_id"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("composer", "0017_post_proposed_publish_at"),
    ]

    operations = [
        migrations.RunPython(normalize_facebook_platform_post_ids, noop_reverse),
    ]
