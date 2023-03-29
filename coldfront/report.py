# -*- coding: utf-8 -*-

'''
reports for coldfront

Created on  2023-03-27

@author: Aaron Kitzmiller <akitzmiller@g.harvard.edu>
@copyright: 2023 The Presidents and Fellows of Harvard College.
All rights reserved.
@license: GPL v2.0
'''
from decimal import Decimal
from ifxreport.report import BaseReportRunner, excel_date

class StandardReportRunner(BaseReportRunner):
    '''Run a standard report for storage'''

    def __init__(self, report, file_root, url_root):
        '''Setup some formats'''
        super().__init__(report, file_root, url_root)
        self.xls_tb_format_str = '#,##0.00'

    def get_sql(self):
        '''
        The sql
        '''

        sql = '''
           select
                o.name as 'Lab Name',
                p.title as 'Project',
                s.name as 'Project Status',
                a.id as 'Allocation ID',
                a.quantity as 'Allocation TB',
                u.full_name as 'User',
                pi.full_name as 'PI',
                pu.decimal_quantity as 'Usage TB',
                br.decimal_charge as 'Charge',
                CONCAT(br.year, '-', br.month) as 'Billing Month',
                r.name as 'Rate Name',
                r.decimal_price as 'Rate',
                a.code as 'Code',
                a.name as 'Account Name',
                a.account_type as 'Account Type'
            from
                project_project p
                    inner join project_projectstatuschoice s on s.id = p.status_id
                    inner join allocation_allocation a on p.id = a.project_id
                    inner join allocation_historicalallocationuser au on au.allocation_id = a.id
                    left join ifx_allocationuserproductusage aupu on au.id = aupu.allocation_user_id
                    left join product_usage pu on aupu.product_usage_id = pu.id
                    left join billing_record br on pu.id = br.product_usage_id
                    left join ifx_projectorganization po on p.id = po.project_id
                    left join nanites_organization o on po.organization_id = o.id
                    left join account a on a.id = br.account_id
                    left join rate r on r.id = br.rate_obj_id
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
        tb_format = workbook.add_format({'num_format': self.xls_tb_format_str})

        if field_value is None:
            worksheet.write_blank(row, col, field_value)
        elif 'date' in field_name.lower():
            date_number = excel_date(field_value)
            worksheet.write_number(row, col, date_number, date_format)
        elif 'charge' in field_name.lower():
            worksheet.write_number(row, col, field_value, money_format)
        elif 'tb' in field_name.lower():
            worksheet.write_number(row, col, field_value, tb_format)
        else:
            worksheet.write(row, col, field_value)

