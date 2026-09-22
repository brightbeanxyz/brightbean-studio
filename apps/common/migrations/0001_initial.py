"""The outbound-email budget and suppression tables.

CreateModel only — two brand-new tables, no schema change to anything that
already holds rows, so this is safe to run against a live database while the
previous release is still serving.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EmailSuppression',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.EmailField(max_length=254, unique=True)),
                ('reason', models.CharField(choices=[('bounced', 'Hard bounce'), ('complained', 'Spam complaint'), ('manual', 'Added by hand')], default='manual', max_length=20)),
                ('detail', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'common_email_suppression',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='EmailSendCounter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scope', models.CharField(choices=[('global_day', 'Global (day)'), ('recipient_hour', 'Recipient (hour)'), ('recipient_day', 'Recipient (day)'), ('invite_org_day', 'Invitations per organization (day)')], max_length=20)),
                ('key', models.CharField(blank=True, default='', max_length=64)),
                ('period_start', models.DateTimeField()),
                ('count', models.PositiveIntegerField(default=0)),
            ],
            options={
                'db_table': 'common_email_send_counter',
                'unique_together': {('scope', 'key', 'period_start')},
            },
        ),
    ]
