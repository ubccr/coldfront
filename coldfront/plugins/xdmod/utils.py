from xdmod_data.warehouse import DataWarehouse
from coldfront.core.utils.common import import_from_settings
import logging

XDMOD_API_URL = import_from_settings("XDMOD_API_URL", "https://localhost")

logger = logging.getLogger(__name__)


def get_usage_data(_metric: str, _slurm_acccount_name: str):
    logger.info(
        f"attempting to fetch usage \
                associated with {_slurm_acccount_name}"
    )
    try:
        dw = DataWarehouse(XDMOD_API_URL)
        with dw:
            data = dw.get_data(
                duration="90day",
                realm="Jobs",
                metric=_metric,
                filters={
                    "pi": _slurm_acccount_name,
                },
            )
    except Exception as err:
        logger.warning(f"Unexpected {err=}, {type(err)=}")
        return

    return data
