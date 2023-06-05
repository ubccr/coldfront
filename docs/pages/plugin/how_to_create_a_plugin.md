# How to Create Your Own Plugin For ColdFront

ColdFront plugins are synonymous to Django apps. To create a plugin, all you have to do is create a Django app and link it to ColdFront by editing configuration settings.

The tutorial below assumes that you are comfortable with Django. If not, check out [these docs]("https://docs.djangoproject.com/en/4.2/intro/tutorial01/") for an introduction to how to build a Django app.

Throughout this tutorial, to effectively illustrate the structure of a linked ColdFront plugin, the Weekly Report plugin [linked here](https://github.com/rg663/weeklyreportapp) will be used as an example.

## Set Up Your App

1. Create your app, complete with a file structure as demonstrated below:
```
weeklyreportapp
│   README.md  
│   __init__.py
│   admin.py
│   apps.py
│   models.py
│   tests.py
│   urls.py
│   views.py
│
└───templates (you can include as many as needed)
    │   index.html

```
2. Ensure that your **__init__.py** file contents have the following format:
```
default_app_config = "coldfront.core.weeklyreportapp.apps.WeeklyreportappConfig"
```

3. Ensure that your **apps.py** file contents look like this:
```
from django.apps import AppConfig


class WeeklyreportappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'coldfront.core.weeklyreportapp'
```

4. Make sure to include this line in your **urls.py** file!
```
app_name = "weeklyreportapp"
```

## Link Your App to ColdFront

1. Add the following app to your list of ```INSTALLED_APPS``` in your ColdFront **base.py** file:
```
# ColdFront Apps
INSTALLED_APPS += [
    'coldfront.core.weeklyreportapp',
]
```
2. Edit your main ColdFront **urls.py** file to include the new urls:
```
urlpatterns += [
    path('weekly-report/', include('coldfront.core.weeklyreportapp.urls')),
]
```
3. Since the example Weekly Report plugin is intended for admins, to add it to the navbar for admins, update the **templates/common/navbar_admin.html** file or its equivalent in your ColdFront setup like so:
```
<li id="navbar-admin" class="nav-item dropdown">
  <a class="nav-link dropdown-toggle" href="#" data-toggle="dropdown">Admin</a>
  <div class="dropdown-menu">
    <a class="dropdown-item" href="/admin">ColdFront Administration</a>
    <a id="navbar-user-search" class="dropdown-item" href="{% url 'user-search-home' %}">User Search</a>
    <a class="dropdown-item" href="{% url 'project-list' %}?show_all_projects=on">All Projects</a>
    <a class="dropdown-item" href="{% url 'allocation-list' %}?show_all_allocations=on">All Allocations</a>
    <a class="dropdown-item" href="{% url 'resource-list' %}">All Resources</a>
    <a id="navbar-project-reviews" class="dropdown-item" href="{% url 'project-review-list' %}">Project Reviews</a>
    <a id="navbar-allocation-requests" class="dropdown-item" href="{% url 'allocation-request-list' %}">
      Allocation Requests</a>
    <a id="navbar-allocation-change-requests" class="dropdown-item" href="{% url 'allocation-change-list' %}">
      Allocation Change Requests</a>
    <a id="navbar-grant-report" class="dropdown-item" href="{% url 'grant-report' %}">Grant Report</a>

    <!-- Add the Weekly Report url to the navbar here -->
    <a id="navbar-weekly-report" class="dropdown-item" href="{% url 'weeklyreportapp:weekly-report' %}">Weekly Report</a>

  </div>
</li>
```
   