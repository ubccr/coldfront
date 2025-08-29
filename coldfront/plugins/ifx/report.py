# -*- coding: utf-8 -*-

'''
Report runners for ColdFront IFX plugin.
'''
from decimal import Decimal
from django.db import connection
from django.utils import timezone
from datetime import datetime
from ifxreport.report import BaseReportRunner, excel_date


class HcsphSeasReportRunner(BaseReportRunner):
    '''Run a report for HCSPH and SEAS usage, billing'''


    def get_sql(self):
        '''
        The sql
        '''

        sql = '''
            select
                o.name as 'Lab Name',
                pu.decimal_quantity as 'Allocation TB',
                t.decimal_charge as 'Charge',
                CONCAT(pu.year, '-', LPAD(pu.month, 2, '0')) as 'Billing Month',
                a.code as 'Code',
                p.product_name as 'Resource'
            from
                product_usage pu
                    inner join product p on p.id = pu.product_id
                    inner join nanites_organization o on pu.organization_id = o.id
                    left join billing_record br on pu.id = br.product_usage_id
                    left join account a on a.id = br.account_id
                    left join transaction t on br.id = t.billing_record_id
            where
                pu.start_date >= %s and pu.start_date < %s
                and a.code in ('325-28541-8250-000001-584571-0001-00000', '275-23355-8250-000001-559620-0000-00000')
        '''
        print(f'Running HCSHPSEASReportRunner with SQL: {sql}')

        return sql

    def run_query(self, start_date, end_date):
        '''
        Run the query using the SQL from get_sql substituting the start and end year / month

        :param start_date: Start date.  The year and month values are used.
        :type start_date: Date

        :param end_date: End date.  The year and month values are used.
        :type end_date: Date

        :return: List of dictionaries keyed by the column names
        :rtype: list
        '''
        sql = self.get_sql()
        cursor = connection.cursor()

        date_format = '%Y-%m-%d'
        query_args = [
            start_date.strftime(date_format),
            end_date.strftime(date_format),
        ]
        if self.organization:
            query_args.append(self.organization.id)
        cursor.execute(sql, query_args)

        print(f'Running SQL: {cursor.db.ops.last_executed_query(cursor, sql, query_args)}')

        results = []
        desc = cursor.description
        self.field_names = [col[0] for col in desc]

        for row in cursor.fetchall():
            row_dict = dict(zip(self.field_names, row))
            results.append(row_dict)

        return results


class AllocationBillingReportRunner(BaseReportRunner):
    '''
    Run a report that accumulates the total TBs allocated for a lab by resource, year, and month
    and the total charges for that resource, year, and month.
    '''

    def get_sql(self):
        '''
        The sql
        '''

        sql = '''
            select
                proj.title as 'Project Title',
                r.name as 'Resource Name',
                r.requires_payment as 'Current Resource Requires Payment Value',
                rp.value as 'Current Allocation Requires Payment Value',
                alloc.id as 'Allocation ID',
                p.product_name as 'Product Name',
                asch.name as 'Current Allocation Status',
                sq.value as 'Storage Quota',
                o.name as 'Lab Billing Name',
                CONCAT(pu.year, '-', LPAD(pu.month, 2, '0')) as 'Month',
                sum(br.decimal_charge) as 'Charge'
            from
                allocation_allocation alloc
                    inner join allocation_allocation_resources ar on alloc.id = ar.allocation_id
                    inner join resource_resource r on ar.resource_id = r.id
                    inner join project_project proj on alloc.project_id = proj.id
                    inner join resource_resourcetype rt on r.resource_type_id = rt.id
                    inner join allocation_allocationstatuschoice asch on alloc.status_id = asch.id
                    left join (allocation_allocationattribute sq inner join allocation_allocationattributetype sqt on sq.allocation_attribute_type_id = sqt.id and (sqt.name = 'Storage Quota (TiB)' or sqt.name = 'Storage Quota (TB)')) on sq.allocation_id = alloc.id
                    left join (allocation_allocationattribute rp inner join allocation_allocationattributetype rpt on rp.allocation_attribute_type_id = rpt.id and rpt.name = 'RequiresPayment') on rp.allocation_id = alloc.id
                    left join (ifx_projectorganization projo inner join nanites_organization o on projo.organization_id = o.id) on proj.id = projo.project_id
                    left join allocation_historicalallocationuser au on alloc.id = au.allocation_id
                    left join ifx_allocationuserproductusage aupu on au.history_id = aupu.allocation_user_id
                    left join (product_usage pu inner join product p on p.id = pu.product_id) on aupu.product_usage_id = pu.id
                    left join billing_record br on pu.id = br.product_usage_id
            where
                rt.name = 'Storage' and
                r.name not in ('holylabs', 'vast-holylabs')
            group by
                proj.title,
                r.name,
                r.requires_payment,
                rp.value,
                alloc.id,
                p.product_name,
                asch.name,
                sq.value,
                o.name,
                Month
            order by
                proj.title,
                alloc.id,
                pu.year,
                pu.month
        '''

        return sql
    def run_query(self, start_date=None, end_date=None):
        '''
        Not going to bother with the date range

        :return: List of dictionaries keyed by the column names
        :rtype: list
        '''
        sql = self.get_sql()
        cursor = connection.cursor()

        cursor.execute(sql)

        results = []
        desc = cursor.description
        self.field_names = [col[0] for col in desc]

        for row in cursor.fetchall():
            row_dict = dict(zip(self.field_names, row))
            results.append(row_dict)

        return results

class StandardReportRunner(BaseReportRunner):
    '''Run a standard report for MRI usage'''

    def __init__(self, report, file_root, url_root, organization=None):
        '''Setup some formats'''
        super().__init__(report, file_root, url_root, organization)
        self.xls_hours_format_str = '#,##0.0'
        self.min_start_date  = timezone.make_aware(datetime(2023, 4, 1)).date()

    def get_fy_start_and_end_dates(self):
        '''
        Make sure start_date is min_start_date or later

        :return: A tuple of start date and end date
        :rtype: tuple
        '''
        start_date, end_date = super().get_fy_start_and_end_dates()
        if start_date < self.min_start_date:
            start_date = self.min_start_date

        return (start_date, end_date)

    def get_start_and_end_dates_from_date_range(self, date_range):
        '''
        Make sure start_date is min_start_date or later

        :param date_range: Text date range for the report.  Can be YYYY-MM:YYYY-MM, a single YYYY-MM, or "fy" for fiscal year to date.
        :type date_range: str

        :return: A tuple of start date and end date
        :rtype: tuple
        '''
        start_date, end_date = super().get_start_and_end_dates_from_date_range(date_range)
        if start_date < self.min_start_date:
            start_date = self.min_start_date

        return (start_date, end_date)

    def get_sql(self):
        '''
        The sql
        '''
        local_tz = timezone.get_current_timezone()

        sql = f'''
            select
                o.name as 'Lab Name',
                u.full_name as 'User',
                CONVERT_TZ(pu.start_date, 'UTC', '{local_tz}') as 'Usage Date',
                pu.decimal_quantity as 'Usage TB',
                br.decimal_quantity as 'Billed Time',
                t.decimal_charge as 'Charge',
                CONCAT(pu.year, '-', LPAD(pu.month, 2, '0')) as 'Billing Month',
                SUBSTRING_INDEX(SUBSTRING_INDEX(t.rate, ')', 1), '(', -1) as 'Rate Name',
                SUBSTRING_INDEX(t.rate, ' ', 1) as 'Rate',
                a.code as 'Code',
                a.name as 'Account Name',
                a.account_type as 'Account Type',
                p.product_name as 'Resource'
            from
                product_usage pu
                    inner join product p on p.id = pu.product_id
                    inner join ifxuser u on pu.product_user_id = u.id
                    inner join nanites_organization o on pu.organization_id = o.id
                    left join billing_record br on pu.id = br.product_usage_id
                    left join account a on a.id = br.account_id
                    left join transaction t on br.id = t.billing_record_id
            where
                pu.start_date >= %s and pu.end_date < %s
        '''

        return sql

    def write_xls_cell(self, workbook, worksheet, row, col, field_name, field_value):
        '''
        Write an XLS cell.  Overridable to apply formatting.
        This implementation writes anything with "date" in the field name as a date,
        anything with "charge" in the field name as a money field, and
        anything with "quantity" in the field name as a decimal

        :param workbook: The workbook being written to.  Needed for formatting.
        :type workbook: `~xlsxwriter.workbook.Workbook`

        :param worksheet: The worksheet being written to
        :type worksheet: `~xlsxwriter.worksheet.Worksheet`

        :param row: Worksheet row
        :type row: int

        :param col: Worksheet column
        :type col: int

        :param field_name: Name of the field being written (e.g. Start Date)
        :type field_name: str

        :param field_value: Value being written
        :type row: obj
        '''
        date_format = workbook.add_format({'num_format': self.xls_date_format_str})
        money_format = workbook.add_format({'num_format': self.xls_accounting_format_str})
        hours_format = workbook.add_format({'num_format': self.xls_hours_format_str})

        if field_value is None:
            worksheet.write_blank(row, col, field_value)
        elif 'date' in field_name.lower():
            date_number = excel_date(field_value)
            worksheet.write_number(row, col, date_number, date_format)
        elif 'charge' in field_name.lower():
            worksheet.write_number(row, col, field_value, money_format)
        elif 'time' in field_name.lower():
            hours_value = Decimal(field_value / 60)
            worksheet.write_number(row, col, hours_value, hours_format)
        else:
            worksheet.write(row, col, field_value)
