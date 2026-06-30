from rest_framework import serializers


class StandardResponseSerializer(serializers.Serializer):
    """Standard API envelope used by every endpoint."""

    success = serializers.BooleanField(help_text="true on success, false on error")
    message = serializers.CharField(help_text="Human-readable status message")
    data = serializers.JSONField(allow_null=True, help_text="Payload (object, array, or null)")
