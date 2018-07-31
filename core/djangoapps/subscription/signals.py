import django.dispatch

subscription_activate_user = django.dispatch.Signal(providing_args=["subscription_user_pk"])
subscription_remove_user = django.dispatch.Signal(providing_args=["subscription_user_pk"])
