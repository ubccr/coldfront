# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import re

import requests
from bs4 import BeautifulSoup

from coldfront.core.utils.common import import_from_settings


def get_system_monitor_context():
    context = {}
    system_monitor = SystemMonitor()
    system_monitor_data = system_monitor.get_data()
    system_monitor_panel_title = system_monitor.get_panel_title()

    context["last_updated"] = system_monitor_data.get("last_updated")
    context["utilization_data"] = system_monitor_data.get("utilization_data")
    context["jobs_data"] = system_monitor_data.get("jobs_data")
    context["system_monitor_panel_title"] = system_monitor_panel_title
    context["SYSTEM_MONITOR_DISPLAY_XDMOD_LINK"] = import_from_settings("SYSTEM_MONITOR_DISPLAY_XDMOD_LINK", None)
    context["SYSTEM_MONITOR_DISPLAY_MORE_STATUS_INFO_LINK"] = import_from_settings(
        "SYSTEM_MONITOR_DISPLAY_MORE_STATUS_INFO_LINK", None
    )

    return context


class SystemMonitor:
    """If anything fails, the home page will still work"""

    RESPONSE_PARSER_FUNCTION = "parse_html_using_beautiful_soup"
    primary_color = "#002f56"
    info_color = "#2f9fd0"
    secondary_color = "#666666"

    def __init__(self):
        self.SYSTEM_MONITOR_ENDPOINT = import_from_settings("SYSTEM_MONITOR_ENDPOINT")
        self.SYSTEM_MONITOR_PANEL_TITLE = import_from_settings("SYSTEM_MONITOR_PANEL_TITLE")
        self.response = None
        self.data = {}
        self.parse_function = getattr(self, self.RESPONSE_PARSER_FUNCTION)
        self.fetch_data()

    def fetch_data(self):
        try:
            r = requests.get(self.SYSTEM_MONITOR_ENDPOINT, timeout=5)
        except Exception:
            r = None

        if r and r.status_code == 200:
            self.response = r

    def parse_html_using_beautiful_soup(self):
        try:
            soup = BeautifulSoup(self.response.text, "html.parser")
        except Exception:
            print("Error in parsing HTML response")
            return

        pattern = re.compile(r"Last updated: (?P<time>[A-Za-z\t :\d.]+)")

        for elm in soup.find_all("div", text=pattern):
            last_updated = pattern.search(elm.text).groups()[0]

        tables = soup.findAll("table")
        tables_dict = {}
        table_names = ["utilization", "jobs", "core_usage", "node_usage"]

        for table_idx, table in enumerate(tables):
            rows = table.find_all("tr")
            table_content = []
            for idx, tr in enumerate(rows, 1):
                if idx == 1:
                    header = str(tr)
                    header = header.replace("<tr>", "")
                    header = header.replace("</tr>", "")
                    header = header.replace("<th>", "")
                    header = header.replace("</th>", ",")
                    header = [ele.strip() for ele in header.split(",")]
                else:
                    table_data = str(tr)
                    table_data = table_data.replace("<tr>", "")
                    table_data = table_data.replace("</tr>", "")
                    table_data = table_data.replace("<td>", "")
                    table_data = table_data.replace("</td>", ",")
                    table_data = [ele.strip() for ele in table_data.split(",")]

                    table_content.append(dict(zip(header, table_data)))
            tables_dict[table_names[table_idx]] = table_content
        try:
            processors_utilized = [
                int(ele.strip()) for ele in tables_dict["utilization"][0]["Processors Utilized"].split("of")
            ]
            jobs = [
                (ele.get("Running"), ele.get("Queued")) for ele in tables_dict["jobs"] if ele.get("Partition") == ""
            ][0]
            job_numbers = [int(ele.split()[0]) for ele in jobs]

            free = processors_utilized[1] - processors_utilized[0]
            utilized_percent = round(processors_utilized[0] / processors_utilized[1] * 1000) / 10
            free_percent = round(free / processors_utilized[1] * 1000) / 10

            utilized_label = "Processors Utilized: %s (%s%%)" % (processors_utilized[0], utilized_percent)
            free_label = "Processors Free: %s (%s%%)" % (free, free_percent)
            utilized_value = processors_utilized[0]
            free_value = free
            running_label = "Running: %s" % (jobs[0])
            queued_label = "Queued: %s" % (jobs[1])
            running_value = job_numbers[0]
            queued_value = job_numbers[1]
        except Exception:
            print("Error in parsing Table. Maybe data is missing")
            return

        utilization_data = {
            "columns": [
                [utilized_label, utilized_value],
                [free_label, free_value],
            ],
            "type": "donut",
            "colors": {
                utilized_label: self.primary_color,
                free_label: self.secondary_color,
            },
        }

        jobs_data = {
            "columns": [
                [running_label, running_value],
                [queued_label, queued_value],
            ],
            "type": "donut",
            "colors": {
                running_label: self.primary_color,
                queued_label: self.info_color,
            },
        }

        self.data = {"utilization_data": utilization_data, "jobs_data": jobs_data, "last_updated": last_updated}

    def parse_response(self):
        self.parse_function()

    def get_data(self):
        self.parse_response()
        return self.data

    def get_panel_title(self):
        return self.SYSTEM_MONITOR_PANEL_TITLE
