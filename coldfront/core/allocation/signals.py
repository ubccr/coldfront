import django.dispatch

allocation_activate_user = django.dispatch.Signal(
    providing_args=["allocation_user_pk"])
allocation_remove_user = django.dispatch.Signal(
    providing_args=["allocation_user_pk"])
