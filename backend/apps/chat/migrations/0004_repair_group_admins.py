from django.db import migrations


def repair_missing_group_admins(apps, schema_editor):
    Conversation = apps.get_model("chat", "Conversation")
    for conv in Conversation.objects.filter(is_group=True, created_by__isnull=True):
        admin = conv.participants.order_by("id").first()
        if admin:
            conv.created_by_id = admin.id
            conv.save(update_fields=["created_by_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_conversation_created_by"),
    ]

    operations = [
        migrations.RunPython(repair_missing_group_admins, migrations.RunPython.noop),
    ]
