from django import template

register = template.Library()

@register.filter
def get_icon(expand_accordion):
    print(expand_accordion)
    if expand_accordion == 'show':
        return 'fa-minus'
    else:
        return 'fa-plus'
