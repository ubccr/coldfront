# -*- coding: utf-8 -*-

'''
Report runners for ColdFront IFX plugin.
'''
from django.db import connection
from ifxreport.report import BaseReportRunner


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
