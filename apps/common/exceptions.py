from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Standardizes all API error responses to:
    {
        "error": "Short descriptive message",
        "details": { ... } or null
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_message = "An error occurred."
        details = response.data

        if isinstance(response.data, dict):
            if "detail" in response.data:
                error_message = str(response.data["detail"])
                details = None
            elif "non_field_errors" in response.data:
                error_message = str(response.data["non_field_errors"][0])
            else:
                first_key = next(iter(response.data))
                val = response.data[first_key]
                if isinstance(val, list) and len(val) > 0:
                    error_message = f"{first_key}: {val[0]}"
                else:
                    error_message = f"Invalid data for {first_key}."
        elif isinstance(response.data, list) and len(response.data) > 0:
            error_message = str(response.data[0])
            details = None

        response.data = {
            "error": error_message,
            "details": details,
        }
        return response

    # Unhandled 500 exceptions
    logger.exception(f"Unhandled exception in API: {str(exc)}", exc_info=exc)
    return Response(
        {
            "error": "An unexpected server error occurred.",
            "details": None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )