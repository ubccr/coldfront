import django.dispatch


project_create = django.dispatch.Signal()
    #providing_args=["project_title"]
project_post_create = django.dispatch.Signal()

project_activate_user = django.dispatch.Signal()
    #providing_args=["project_user_pk"]
project_remove_user = django.dispatch.Signal()
    #providing_args=["project_user_pk"]
