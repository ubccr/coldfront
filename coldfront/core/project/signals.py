import django.dispatch

project_create = django.dispatch.Signal()
    #providing_args=["project_title"]
project_post_create = django.dispatch.Signal()
    #providing_args=["project_obj"]

project_make_projectuser = django.dispatch.Signal()
    #providing_args=["user_name", "group_name"]

project_preremove_projectuser = django.dispatch.Signal()
    #providing_args=["user_name", "group_name"]

project_filter_users_to_remove = django.dispatch.Signal()
    #providing_args=["project_user_list"]
    # return tuple of (no_removal, can_remove)
