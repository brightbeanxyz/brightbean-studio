from django.db import migrations


def set_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.update_or_create(
        id=1,
        defaults={"domain": "studio.brightbean.xyz", "name": "Brightbean"},
    )


def reset_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.filter(id=1).update(domain="example.com", name="example.com")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_add_tos_accepted_at"),
        ("sites", "0002_alter_domain_unique"),
    ]
    operations = [migrations.RunPython(set_site, reset_site)]
