from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0008_rename_chat_messag_message_emoji_idx_chat_messag_message_ce4293_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageHidden",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hidden_at", models.DateTimeField(auto_now_add=True)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hidden_for",
                        to="chat.message",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hidden_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("message", "user")},
            },
        ),
        migrations.AddIndex(
            model_name="messagehidden",
            index=models.Index(fields=["user", "message"], name="chat_messag_user_msg_hid_idx"),
        ),
    ]
