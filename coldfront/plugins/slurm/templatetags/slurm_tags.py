from django import template

register = template.Library()

@register.filter
def dictitem(dictionary, key):
    return dictionary.get(key)
