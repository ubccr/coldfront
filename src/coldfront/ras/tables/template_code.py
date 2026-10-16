# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

CUSTOM_ATTRIBUTES = """
{% if value %}{% for attr in value %}{{ attr }}{% if not forloop.last %}, {% endif %}{% endfor %}{% endif %}
"""

RESOURCES_LIST = """
{% for r in value.all %}
{% cotton cf.badge variant="{{ r.resource_type.color|default:'neutral' }}" href="{{ r.get_absolute_url }}" %}{{ r }}{% endcotton %}
{% empty %}
{{ ""|placeholder }}
{% endfor %}
"""
