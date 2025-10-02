# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront auto_compute_allocation plugin fairshare_institution_name.py"""

import logging

from coldfront.core.utils.common import import_from_settings

AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION_NAME_FORMAT = import_from_settings(
    "AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION_NAME_FORMAT"
)

logger = logging.getLogger(__name__)


def generate_fairshare_institution_name(project_obj):
    """Method to generate a fairshare_institution_name using predefined variables"""

    # Get the uppercase characters from institution
    institution_abbr_raw = "".join([c for c in project_obj.institution if c.isupper()])

    FAIRSHARE_INSTITUTION_NAME_VARS = {
        "institution_abbr_upper_lower": institution_abbr_raw.lower(),
        "institution_abbr_upper_upper": institution_abbr_raw,
        "institution": project_obj.institution.replace(" ", ""),
        "institution_formatted": project_obj.institution.replace(" ", "_").lower(),
    }

    # if a faishare institution name format is defined as a string (use env var), else use format suggested
    if AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION_NAME_FORMAT:
        gen_fairshare_institution_name = AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION_NAME_FORMAT.format(
            **FAIRSHARE_INSTITUTION_NAME_VARS
        )
    else:
        gen_fairshare_institution_name = "{institution}".format(**FAIRSHARE_INSTITUTION_NAME_VARS)

    logger.info(f"Generated fairshare institution name {gen_fairshare_institution_name}")

    return gen_fairshare_institution_name
