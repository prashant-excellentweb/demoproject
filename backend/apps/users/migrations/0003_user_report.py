# Generated manually for UserReport

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0015_conversation_pin"),
        ("users", "0002_profile_setup_complete"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("spam", "Spam"),
                            ("harassment", "Harassment"),
                            ("inappropriate", "Inappropriate content"),
                            ("fake", "Fake account"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=32,
                    ),
                ),
                ("details", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="user_reports",
                        to="chat.conversation",
                    ),
                ),
                (
                    "reported_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports_received",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reporter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports_filed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="userreport",
            index=models.Index(fields=["reported_user", "-created_at"], name="users_repor_reporte_idx"),
        ),
        migrations.AddIndex(
            model_name="userreport",
            index=models.Index(fields=["reporter", "-created_at"], name="users_repor_reporte_idx2"),
        ),
    ]
