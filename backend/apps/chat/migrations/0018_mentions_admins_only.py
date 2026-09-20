# Generated manually for group mentions and admins-only messaging

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0017_message_edited_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="admins_only_messages",
            field=models.BooleanField(
                default=False,
                help_text="When True, only group admins can send messages.",
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="mention_everyone",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="MessageMention",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mention_links",
                        to="chat.message",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="message_mentions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="message",
            name="mentioned_users",
            field=models.ManyToManyField(
                blank=True,
                related_name="mentioned_in_messages",
                through="chat.MessageMention",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name="messagemention",
            constraint=models.UniqueConstraint(fields=("message", "user"), name="chat_mention_message_user_uniq"),
        ),
        migrations.AddIndex(
            model_name="messagemention",
            index=models.Index(fields=["user", "-created_at"], name="chat_mention_user_created"),
        ),
        migrations.AddIndex(
            model_name="messagemention",
            index=models.Index(fields=["message"], name="chat_mention_msg_idx"),
        ),
    ]
