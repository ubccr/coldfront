# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import requests


def get_bib(doi_number):
    api_url = "http://api.crossref.org/works/{}/transform/application/x-bibtex"
    api_url = api_url.format(doi_number)
    req = requests.get(api_url)
    valid = True
    if req.status_code != 200:
        valid = False
    bib_entry = str(req.content, encoding="utf-8")

    return valid, bib_entry
