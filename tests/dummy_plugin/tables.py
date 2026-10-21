# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_tables2 as tables

from coldfront.lib.tables import register_table_column
from coldfront.ras.tables import ProjectTable

mycol = tables.Column(
    verbose_name="My column",
    accessor=tables.A("description"),
)

register_table_column(mycol, "foo", ProjectTable)
