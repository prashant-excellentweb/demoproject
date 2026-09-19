# Generated manually for message edit window

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0016_message_reply_forward_draft"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="edited_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Set when the sender edits content within the allowed window.",
                null=True,
            ),
        ),
    ]
