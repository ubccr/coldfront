# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from coldfront.context import current_request


def send_email_template(context, template, subject, to):
    """Send an email from a template"""

    # TODO add better error handling.

    if not context:
        context = {}

    context["settings"] = settings
    request = current_request.get()
    if request:
        context["home_link"] = request.build_absolute_uri(reverse("home"))
        context["login_link"] = request.build_absolute_uri(reverse("login"))

    text_content = render_to_string(f"email/txt/{template}.txt", context)
    html_content = render_to_string(f"email/html/{template}.html", context)

    if settings.EMAIL_SUBJECT_PREFIX:
        subject = f"{settings.EMAIL_SUBJECT_PREFIX} {subject}"

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.EMAIL_SENDER,
        to=to,
    )

    msg.attach_alternative(html_content, "text/html")
    msg.send()
