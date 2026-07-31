from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

def custom_exception_handler(exc, context):
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, 'message_dict') else {'error': exc.messages}
        return Response(detail, status=status.HTTP_400_BAD_REQUEST)

    if response is not None:
        if isinstance(response.data, dict) and 'detail' in response.data:
            response.data = {'error': response.data['detail']}
        elif isinstance(response.data, list):
            response.data = {'errors': response.data}

    return response
