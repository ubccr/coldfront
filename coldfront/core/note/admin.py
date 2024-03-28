from django.contrib import admindocs

from coldfront.core.note.models import Note
from django.contrib import admin

# Register your models here.
@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title','message','pk')
