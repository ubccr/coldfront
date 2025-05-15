from django import template
from django.utils.html import format_html
from coldfront.core.utils.fasrc import get_resource_rate

register = template.Library()

@register.simple_tag(takes_context=True)
def cost_bytes(context, amount):
    a_price = get_resource_rate(context['allocation'].get_resources_as_string)
    amount_tb = int(amount) / 1099511627776
    if a_price:
        return "${:,.2f}".format(a_price * amount_tb)
    return None

@register.simple_tag(takes_context=True)
def cost_tb(context, amount):
    a_price = get_resource_rate(context['allocation'].get_resources_as_string)
    if a_price:
        return "${:,.2f}".format(a_price * amount)
    return None

@register.simple_tag(takes_context=True)
def cost_cpuhours(context, amount):
    a_price = get_resource_rate(context['allocation'].get_resources_as_string)
    if amount and a_price:
        return "${:,.2f}".format(float(a_price) * float(amount))
    return None

@register.inclusion_tag('resource_summary_table.html')
def resource_summary_table(resource):
    """
    """
    res_attr_table = {
        'Resource': resource,
    }
    label = resource.quantity_label
    if resource.capacity:
        res_attr_table['Total space'] = f"{round(resource.capacity, 2)} {label}"
        allocated_tb = resource.allocated_tb
        if allocated_tb:
            allocated_tb = round(resource.allocated_tb, 2)
            allocated_pct = round(allocated_tb / resource.capacity * 100, 2)
            res_attr_table['Space Committed'] = f'{allocated_tb} {label} ({allocated_pct}%)'
            remaining_space = round(resource.capacity * .85 - allocated_tb, 2)
            res_attr_table['Remaining Space (assuming 85% limit)'] = f'{remaining_space} {label}'
        else:
            res_attr_table['Space Committed'] = 'Information not available; check the sheet.'
    if resource.used_tb:
        res_attr_table['Space Occupied'] = f'{round(resource.used_tb, 2)} {label} ({resource.used_percentage}%)'

    return {'res_attr_table': res_attr_table}

@register.simple_tag()
def resource_fullness_badge(resource):
    badge_type = "info"
    pct = None
    if resource.allocated_tb:
        label = 'allocated'
        pct = round(resource.allocated_tb / resource.capacity * 100, 2)
    elif resource.used_percentage:
        label = 'in use'
        pct = resource.used_percentage
    if pct:
        if pct > 79.5:
            badge_type = "danger"
        elif pct > 75:
            badge_type = "warning"
        return format_html('<span class="badge badge-{}">{}% {}</span>',
            badge_type, pct, label
        )
    return ''
