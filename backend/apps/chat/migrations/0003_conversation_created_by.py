from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def set_existing_group_admins(apps, schema_editor):
    Conversation = apps.get_model("chat", "Conversation")
    for conv in Conversation.objects.filter(is_group=True, created_by__isnull=True):
        admin = conv.participants.order_by("id").first()
        if admin:
            conv.created_by_id = admin.id
            conv.save(update_fields=["created_by_id"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_groups",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(set_existing_group_admins, migrations.RunPython.noop),
    ]
