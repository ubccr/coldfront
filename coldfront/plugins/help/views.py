from django.shortcuts import render
from django.core.mail import send_mail

from django.contrib.auth.models import User
from coldfront.config.plugins.help import SUPPORT_EMAILS, EMAIL_HELP_TEMPLATE, EMAIL_HELP_DEFAULT_TARGET

def get_help(request):
    return get_targeted_help(request, None)


def get_targeted_help(request, tgt):
    context = {}
    context["titles"] = [e["title"] for e in SUPPORT_EMAILS]
    sel_index = next((i for i, e in enumerate(SUPPORT_EMAILS) if tgt and e["address"].startswith(tgt)), None)
    context["target_index"] = sel_index if sel_index is not None else -1
    context["request_user_info"] = not request.user.is_authenticated

    return render(request, "help/help.html", context)


def send_help(request):
    form_data = request.POST
    if form_data:
        target_id = int(form_data.get("target_index", -1))
        if target_id == -1:
            target_email = EMAIL_HELP_DEFAULT_TARGET
        else:
            target_email = SUPPORT_EMAILS[target_id]["address"]

        if request.user.is_authenticated:
            user = User.objects.get(username=request.user.username)
            user_email = user.email
            first = user.first_name
            last = user.last_name
        else:
            user_email = form_data.get("email", "")
            first = form_data.get("first_name", "")
            last = form_data.get("last_name", "")

        message=form_data.get("message", ""),

        send_mail(
            subject=form_data.get("subject", "Help Request"),
            message=EMAIL_HELP_TEMPLATE.format(first=first, last=last, message=message),
            from_email=user_email,
            recipient_list=[target_email],
            fail_silently=False,
        )

    context = None
    return render(request, "help/form_completed.html", context)
