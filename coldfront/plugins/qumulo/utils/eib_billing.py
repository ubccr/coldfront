import logging
from datetime import datetime

from coldfront.plugins.qumulo.utils.billing_report import BillingReport

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

YYYY_MM_DD = "%Y-%m-%d"


class EIBBilling(BillingReport):
    def __init__(self, timestamp):
        super().__init__("monthly", timestamp)

    def generate_monthly_billing_report(self) -> bool:
        args = dict()
        args["document_date"] = datetime.today().strftime("%m/%d/%Y")
        args["billing_month"] = self.billing_month
        args["delivery_date"] = self.delivery_date
        args["usage_date"] = self.usage_date

        monthly_billing_query = super().get_query(args, "monthly")

        super().generate_report(monthly_billing_query)
