# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront auto_compute_allocation plugin slurm_account_name.py"""

import logging

from coldfront.core.utils.common import import_from_settings

AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT = import_from_settings(
    "AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT"
)

logger = logging.getLogger(__name__)


def generate_slurm_account_name(allocation_obj, project_obj):
    """Method to generate a slurm_account_name using predefined variables"""

    # define valid vars for naming slurm account in dictionary
    SLURM_ACCOUNT_NAME_VARS = {
        "allocation_id": allocation_obj.pk,
        "PI_first_initial": project_obj.pi.first_name[0].lower(),
        "PI_first_name": project_obj.pi.first_name.lower(),
        "PI_last_initial": project_obj.pi.last_name[0].lower(),
        "PI_last_name_formatted": project_obj.pi.last_name.replace(" ", "_").lower(),
        "PI_last_name": project_obj.pi.last_name.lower(),
        "project_code": project_obj.project_code,
        "project_id": project_obj.pk,
    }

    if hasattr(project_obj, "institution"):
        # Get the uppercase characters from institution
        institution_abbr_raw = "".join([c for c in project_obj.institution if c.isupper()])

        SLURM_ACCOUNT_NAME_VARS.update(
            {
                "institution_abbr_upper_lower": institution_abbr_raw.lower(),
                "institution_abbr_upper_upper": institution_abbr_raw,
                "institution": project_obj.institution.replace(" ", "_"),
                "institution_formatted": project_obj.institution.replace(" ", "_").lower(),
            }
        )

    # if a slurm account name format is defined as a string (use env var), else use format suggested
    if AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT:
        gen_slurm_account_name = AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT.format(**SLURM_ACCOUNT_NAME_VARS)
    else:
        gen_slurm_account_name = "{project_code}_{PI_first_initial}_{PI_last_name_formatted}_{allocation_id}".format(
            **SLURM_ACCOUNT_NAME_VARS
        )

    logger.info(f"Generated slurm account name {gen_slurm_account_name}")

    return gen_slurm_account_name
