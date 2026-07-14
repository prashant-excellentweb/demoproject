from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0010_rename_chat_messag_user_msg_hid_idx_chat_messag_user_id_bcc8db_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConversationFavourite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favourited_by",
                        to="chat.conversation",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favourite_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("conversation", "user")},
            },
        ),
        migrations.AddIndex(
            model_name="conversationfavourite",
            index=models.Index(fields=["user", "-created_at"], name="chat_fav_user_created_idx"),
        ),
    ]
