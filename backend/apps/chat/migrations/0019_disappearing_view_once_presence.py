# Generated manually for disappearing messages + view once

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0018_mentions_admins_only"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="disappearing_messages",
            field=models.CharField(
                choices=[
                    ("off", "Off"),
                    ("24h", "24 hours"),
                    ("7d", "7 days"),
                    ("90d", "90 days"),
                ],
                default="off",
                help_text="Auto-delete new messages after this duration (per chat).",
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="expires_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When set, message is auto-deleted after this time (disappearing messages).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="is_view_once",
            field=models.BooleanField(
                default=False,
                help_text="Image/video that can be opened once by each recipient.",
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="view_once_opened_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="message",
            name="view_once_opened_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="opened_view_once_messages",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["expires_at"], name="chat_messag_expires_3f8a2c_idx"),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["conversation", "message_type", "-created_at"],
                name="chat_messag_convers_9a1b4d_idx",
            ),
        ),
    ]
