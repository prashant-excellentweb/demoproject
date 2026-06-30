from rest_framework.views import exception_handler

from apps.common.responses import api_error


def _extract_message(data):
    if isinstance(data, dict):
        if "detail" in data:
            detail = data["detail"]
            if isinstance(detail, str):
                return detail, None
            return "Request failed", detail
        return "Validation failed", data
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, str):
            return first, data
        if isinstance(first, dict) and "detail" in first:
            return str(first["detail"]), data
        return "Validation failed", data
    return "An error occurred", data


def custom_exception_handler(exc, context):
    """Wrap all DRF exceptions in { success, message, data }."""
    response = exception_handler(exc, context)
    if response is None:
        return response

    message, data = _extract_message(response.data)
    return api_error(message=message, data=data, status_code=response.status_code)
