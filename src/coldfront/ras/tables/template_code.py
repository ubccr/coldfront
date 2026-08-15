# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

CUSTOM_ATTRIBUTES = """
{% if value %}{% for attr in value %}{{ attr }}{% if not forloop.last %}, {% endif %}{% endfor %}{% endif %}
"""

RESOURCES_LIST = """
{% for r in value.all %}
<span class="badge" style="color: {{ r.resource_type.color|fgcolor }}; background-color: #{{ r.resource_type.color }}">
<a href="{{ r.get_absolute_url }}">{{ r }}</a>
</span>
{% empty %}
{{ ""|placeholder }}
{% endfor %}
"""
