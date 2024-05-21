import django.dispatch


project_create = django.dispatch.Signal()
    #providing_args=["project_title"]
project_post_create = django.dispatch.Signal()
    #providing_args=["project_obj"]

project_add_projectuser = django.dispatch.Signal()
    #providing_args=["user_name", "group_name"]

project_preremove_projectuser = django.dispatch.Signal()
    #providing_args=["user_name", "group_name"]

project_filter_users_to_remove = django.dispatch.Signal()
    #providing_args=["project_user_list"]
    # return tuple of (no_removal, can_remove)

project_activate_user = django.dispatch.Signal()
    #providing_args=["project_user_pk"]
project_remove_user = django.dispatch.Signal()
    #providing_args=["project_user_pk"]
