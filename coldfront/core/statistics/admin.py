from django.contrib import admin

from coldfront.core.statistics.models import CPU
from coldfront.core.statistics.models import Job
from coldfront.core.statistics.models import Node


admin.register(CPU)
admin.register(Job)
admin.register(Node)
