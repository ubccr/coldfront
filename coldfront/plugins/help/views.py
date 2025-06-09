import logging
from django.shortcuts import render
from django.core.mail import send_mail
from django.views.generic import TemplateView
from django.contrib import messages

from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.help.forms import HelpForm

EMAIL_HELP_SUPPORT_EMAILS = import_from_settings("EMAIL_HELP_SUPPORT_EMAILS", {})
EMAIL_HELP_TEMPLATE = import_from_settings("EMAIL_HELP_TEMPLATE", "")
EMAIL_HELP_DEFAULT_EMAIL = import_from_settings("EMAIL_HELP_DEFAULT_EMAIL", "")

logger = logging.getLogger(__name__)


class HelpView(TemplateView):
    template_name = "help/help.html"

    def get_initial_data(self):
        initial_data = {"first_name": "", "last_name": "", "user_email": "", "queue_email": ""}

        user = self.request.user
        if user.is_authenticated:
            initial_data["first_name"] = user.first_name
            initial_data["last_name"] = user.last_name
            initial_data["user_email"] = user.email

        queue = self.request.GET.get("queue", "")
        initial_data["queue_email"] = EMAIL_HELP_SUPPORT_EMAILS.get(queue, EMAIL_HELP_DEFAULT_EMAIL)
        return initial_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = HelpForm(initial=self.get_initial_data())
        return context

    def post(self, request, *args, **kwargs):
        form = HelpForm(request.POST, initial=self.get_initial_data())
        if form.is_valid():
            form_data = form.cleaned_data
            queue_email = form_data.get("queue_email")
            user_email = form_data.get("user_email")
            first = form_data.get("first_name")
            last = form_data.get("last_name")
            message = form_data.get("message")
            send_mail(
                subject=form_data.get("subject", "Help Request"),
                message=EMAIL_HELP_TEMPLATE.format(first=first, last=last, message=message),
                from_email=user_email,
                recipient_list=[queue_email],
                fail_silently=False,
            )
        else:
            messages.error(
                request,
                f"Something went wrong, please try again. If the issue persists contact {EMAIL_HELP_DEFAULT_EMAIL}.",
            )
            logger.error(f"An error occured in the help form. Error: {form.errors.as_text()}")
            return self.render_to_response(self.get_context_data())

        return render(request, "help/form_completed.html")
