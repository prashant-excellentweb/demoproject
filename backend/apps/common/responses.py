from rest_framework import status
from rest_framework.response import Response


def api_success(data=None, message="Success", status_code=status.HTTP_200_OK):
    """Standard success response: { success: true, message, data }."""
    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
        },
        status=status_code,
    )


def api_error(message="Error", data=None, status_code=status.HTTP_400_BAD_REQUEST):
    """Standard error response: { success: false, message, data }."""
    return Response(
        {
            "success": False,
            "message": message,
            "data": data,
        },
        status=status_code,
    )
