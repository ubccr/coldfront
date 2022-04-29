import logging


logger = logging.getLogger(__name__)


class ExceptionMiddleware:
    """Log exceptions raised by views."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    @staticmethod
    def process_exception(request, exception):
        message = (
            f'{request.user} encountered an uncaught exception at '
            f'{request.path}. Details:')
        logger.error(message)
        logger.exception(exception)
        return None
