from django import template
from coldfront.core.utils.fasrc import get_resource_rate

register = template.Library()

@register.simple_tag(takes_context=True)
def cost_bytes(context, amount):
    a_price = get_resource_rate(context['allocation'].get_resources_as_string)
    amount_tb = amount / 1099511627776
    return "${:,.2f}".format(a_price * amount_tb)

@register.simple_tag(takes_context=True)
def cost_tb(context, amount):
    a_price = get_resource_rate(context['allocation'].get_resources_as_string)
    return "${:,.2f}".format(a_price * amount)
