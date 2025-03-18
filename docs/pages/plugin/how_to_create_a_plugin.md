# How to Create Your Own Plugin For ColdFront

ColdFront plugins are synonymous to Django apps. To create a plugin, all you have to do is create a Django app and link it to ColdFront by editing configuration settings.

The tutorial below assumes that you are comfortable with Django. If not, check out [these docs](https://docs.djangoproject.com/en/4.2/intro/tutorial01/) for an introduction to how to build a Django app.

Throughout this tutorial, to effectively illustrate the structure of a linked ColdFront plugin, the Weekly Report plugin [linked here](https://github.com/rg663/weeklyreportapp) will be used as an example.

## Option 1: Connect Your App Manually

!!! info
    Note: To override any other default ColdFront templates, follow these instructions from our docs. This option is best if you would not like to use pip to install your app. It is important to note, however, that when updating your ColdFront version, that you would need to keep in mind that these files are placed within the app's own files.

### Set Up Your App

1. Create your app, complete with a file structure as demonstrated below (for the example app, download the Git repository):
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
2. Ensure that your app's __\_\_init\_\_.py__ file contents have the following format:
```
default_app_config = "coldfront.plugins.weeklyreportapp.apps.WeeklyreportappConfig"
```

3. Ensure that your app's **apps.py** file contents look like this:
```
from django.apps import AppConfig


class WeeklyreportappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'coldfront.plugins.weeklyreportapp'
```

4. Make sure to include these lines (or similar for your app) in your app's **urls.py** file:
```
from django.urls import path

from . import views

app_name = "weeklyreportapp"
urlpatterns = [
    path("", views.index, name="weeklyreportapp"),
]
```

5. In your app's **views.py** file, add this line:
```
from .models import *
```
   
6. Import ColdFront models in the following manner in your **models.py** file in your app:
```
from coldfront.core.allocation.models import *
from coldfront.core.project.models import *
from coldfront.core.resource.models import *
from coldfront.core.user.models import *
```
   
7. Add ColdFront's skeleton HTML/CSS by adding the following lines to all of your template files:
```
{% extends "common/base.html" %}
{% load crispy_forms_tags %}
{% load humanize %}
{% load static %}
```

### Link Your App to ColdFront

1. Add the following app to your list of ```INSTALLED_APPS``` by creating a new file in the ColdFront plugins directory (`coldfront/config/plugins`) and adding these lines to the new file (i.e. `weeklyreportapp.py`):
```
from coldfront.config.base import INSTALLED_APPS

INSTALLED_APPS += [
    'coldfront.plugins.weeklyreportapp',
]
```

2. Edit the ColdFront **urls.py** (`coldfront/config/urls.py`) file to include the new urls info:
```
urlpatterns += [
    path('weeklyreportapp/', include('coldfront.plugins.weeklyreportapp.urls')),
]
```

3. In the ColdFront **settings.py** (`coldfront/config/settings.py`) file, add the following lines:
```
plugin_configs['PLUGIN_WEEKLYREPORTAPP'] = 'plugins/weeklyreportapp.py'
``` 

4. Set the ```PLUGIN_WEEKLYREPORTAPP``` config variable to TRUE in your environment file.

5. Add your app's folder to the ```coldfront/plugins``` directory.

5. Since the example Weekly Report plugin is intended for admins, to add it to the navbar for admins, update the **navbar_admin.html** (```templates/common/navbar_admin.html```) file or its equivalent in your ColdFront setup like so:
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

      <!-- Add the Weekly Report url to the navbar dropdown here -->
      <a id="navbar-weekly-report" class="dropdown-item" href="{% url 'weeklyreportapp:weeklyreportapp' %}">Weekly Report</a>

    </div>
  </li>
  ```

!!! Tip
    Note: To override any other default ColdFront templates, follow [these instructions](../config.md#custom-branding) from our docs.

Your app should now be linked to ColdFront.

## Option 2: Connect Your App Using Pip

!!! info 
    Note: This option is recommended since it does not interfere with your ColdFront files and the process feels familiar for many, much like downloading an app to your phone or laptop.

### Download Your App
To use pip, **pip install [package_name]** in your virtual environment to make upgrading ColdFront more efficient (if applicable). To learn how to create a pip package, check out [this link](https://packaging.python.org/en/latest/tutorials/packaging-projects/). If you are creating a pip package from a GitHub repo, we found [this blog](https://dev.to/rf_schubert/how-to-create-a-pip-package-and-host-on-private-github-repo-58pa) information useful in doing so. To pip install the example plugin, run the following command in your terminal (preferably in a [Python virtual environment](https://docs.python.org/3/library/venv.html) to install it specifically for your instance of ColdFront):
  ```
  pip install -e git+https://github.com/rg663/weeklyreportapppip#egg=weeklyreportapp
  ```

### Link Your App to ColdFront

1. Add the following app to your list of ```INSTALLED_APPS``` by creating a new file in the ColdFront plugins directory (`coldfront/config/plugins`) and adding these lines to the new file (i.e. `weeklyreportapp.py`):
```
from coldfront.config.base import INSTALLED_APPS

INSTALLED_APPS += [
    'weeklyreportapp',
]
```

2. Edit the ColdFront **urls.py** (`coldfront/config/urls.py`) file to include the new urls info:
```
urlpatterns += [
    path('weeklyreportapp/', include('weeklyreportapp.urls')),
]
```

3. In the ColdFront **settings.py** (`coldfront/config/settings.py`) file, add the following lines:
```
plugin_configs['PLUGIN_WEEKLYREPORTAPP'] = 'plugins/weeklyreportapp.py'
``` 

4. Set the ```PLUGIN_WEEKLYREPORTAPP``` config variable to TRUE in your environment file.

5. Since the example Weekly Report plugin is intended for admins, to add it to the navbar for admins, update the **navbar_admin.html** (```templates/common/navbar_admin.html```) file or its equivalent in your ColdFront setup like so:
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

      <!-- Add the Weekly Report url to the navbar dropdown here -->
      <a id="navbar-weekly-report" class="dropdown-item" href="{% url 'weeklyreportapp:weeklyreportapp' %}">Weekly Report</a>

    </div>
  </li>
  ```

!!! Tip
    Note: To override any other default ColdFront templates, follow [these instructions](../config.md#custom-branding) from our docs.

Your app should now be linked to ColdFront.
