# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += ["coldfront.plugins.system_monitor"]

SYSTEM_MONITOR_PANEL_TITLE = ENV.str("SYSMON_TITLE", default="HPC Cluster Status")
SYSTEM_MONITOR_ENDPOINT = ENV.str("SYSMON_ENDPOINT")
SYSTEM_MONITOR_DISPLAY_MORE_STATUS_INFO_LINK = ENV.str("SYSMON_LINK")
SYSTEM_MONITOR_DISPLAY_XDMOD_LINK = ENV.str("SYSMON_XDMOD_LINK")
