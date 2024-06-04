import django.dispatch

allocation_autocreate = django.dispatch.Signal()
    #providing_args=["approval_form_data", "allocation_obj"]

allocation_activate = django.dispatch.Signal()
    #providing_args=["allocation_pk"]
allocation_disable = django.dispatch.Signal()
    #providing_args=["allocation_pk"]

allocation_activate_user = django.dispatch.Signal()
    #providing_args=["allocation_user_pk"]
allocation_remove_user = django.dispatch.Signal()
    #providing_args=["allocation_user_pk"]

allocation_change_approved = django.dispatch.Signal()
    #providing_args=["allocation_pk", "allocation_change_pk"]
