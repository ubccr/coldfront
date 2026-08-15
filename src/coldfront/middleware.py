# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import uuid

from .registry import apply_request_processors


class ColdFrontMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Assign a random unique ID to the request. This will be used for change logging.
        request.id = uuid.uuid4()

        # Apply all registered request processors
        with apply_request_processors(request):
            response = self.get_response(request)

        # Attach the unique request ID as an HTTP header.
        response["X-Request-ID"] = request.id

        # Enable the Vary header to help with caching of HTMX responses
        response["Vary"] = "HX-Request"

        return response
