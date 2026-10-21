# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

SEARCH_RESULT_ATTRS = """
{% for name, value in record.display_attrs.items %}
  {% cotton cf.badge variant="secondary" %}
    {{ name|bettertitle }}:
    {% with url=value.get_absolute_url %}
      {% if url %}<a href="{{ url }}">{% endif %}
      {% if value|length > 40 %}
        {{ value|truncatechars:"40" }}
      {% else %}
        {{ value }}
      {% endif %}
      {% if url %}</a>{% endif %}
    {% endwith %}
  {% endcotton %}
{% endfor %}
"""
