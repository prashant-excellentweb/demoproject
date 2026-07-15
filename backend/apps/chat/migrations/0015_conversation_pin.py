from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0014_rename_archive_block_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConversationPin",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pinned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pinned_by",
                        to="chat.conversation",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pinned_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("conversation", "user")},
            },
        ),
        migrations.AddIndex(
            model_name="conversationpin",
            index=models.Index(fields=["user", "-pinned_at"], name="chat_pin_user_pinned_idx"),
        ),
    ]
