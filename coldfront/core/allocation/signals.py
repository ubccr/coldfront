import django.dispatch

allocation_new = django.dispatch.Signal()
    #providing_args=["allocation_pk"]
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
allocation_change = django.dispatch.Signal()

allocation_expire = django.dispatch.Signal()
    # providing_args=["allocation_pk"])
allocation_change_user_role = django.dispatch.Signal()
    # providing_args=["allocation_user_pk"])
visit_allocation_detail = django.dispatch.Signal()
    #providing_args=["allocation_pk"])
