# Generated manually for privacy visibility settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_user_report"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="about_privacy",
            field=models.CharField(
                choices=[
                    ("everyone", "Everyone"),
                    ("contacts", "My contacts"),
                    ("nobody", "Nobody"),
                ],
                default="everyone",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_seen_privacy",
            field=models.CharField(
                choices=[
                    ("everyone", "Everyone"),
                    ("contacts", "My contacts"),
                    ("nobody", "Nobody"),
                ],
                default="everyone",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="profile_photo_privacy",
            field=models.CharField(
                choices=[
                    ("everyone", "Everyone"),
                    ("contacts", "My contacts"),
                    ("nobody", "Nobody"),
                ],
                default="everyone",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="status_privacy",
            field=models.CharField(
                choices=[
                    ("everyone", "Everyone"),
                    ("contacts", "My contacts"),
                    ("nobody", "Nobody"),
                ],
                default="contacts",
                max_length=16,
            ),
        ),
    ]
