import os


class BillingGenerator:
    def _get_item_description(cols: list[str]):

        item_description_format = """('"' %s '"') AS item_description"""
        item_description_contents = f"|| {' || '.join(cols)} ||"

        return item_description_format % item_description_contents

    def _get_current_fiscal_year() -> str:
        # TODO - get current fiscal year from environment variable
        # ITDEV-36278
        return os.getenv("CURRENT_FISCAL_YEAR", "FY25")

    def get_billing_query(self, args, report_type: str) -> str:
        MONTHLY_COLS = [
            "'WashU IT RIS '",
            "report.service_name",
            "' - '",
            "report.service_rate_category",
            "'; Usage: '",
            "report.billing_amount",
            "' X Rate: '",
            "report.rate",
            "' X Per: '",
            "report.service_unit",
        ]

        PREPAID_COLS = [
            "'WashU IT RIS '",
            "report.service_name",
            "' - '",
            "report.service_rate_category",
            "'; Usage: '",
            "report.prepaid_time",
            "' X Rate: '",
            "report.rate",
            "' X Per: '",
            "report.service_unit",
            "' = Total Cost: '",
            "report.total_cost",
        ]
        fiscal_year = BillingGenerator._get_current_fiscal_year()
        prepaid_custom_columns_from_select_top_level = ""
        prepaid_custom_columns_from_select_lower_level = ""
        prepaid_custom_columns_from_select_lowest_level = ""
        additional_category_case_monthly = ""
        join_clause = ""
        monthly_specific_where_clause = ""
        monthly_specific_columns = ""
        additional_category_case_monthly_cast = ""
        additional_category_case_monthly_unit = ""
        final_where_clause = ""
        if report_type == "monthly":
            report_header_type = "Monthly for"
            item_description = BillingGenerator._get_item_description(MONTHLY_COLS)
            monthly_specific_columns = "report.billing_amount usage_amount,"
            additional_category_case_monthly = "WHEN 'consumption' THEN 13"
            additional_category_case_monthly_cast = "WHEN 'consumption' THEN CAST(storage_usage_of_the_day.storage_usage AS FLOAT8) /1024/1024/1024/1024"
            additional_category_case_monthly_unit = "WHEN 'consumption' THEN 'TB'"
            join_clause = f"""
                JOIN (
                    SELECT haau.allocation_attribute_id, haau.value storage_usage
                    FROM allocation_historicalallocationattributeusage haau
                    JOIN (
                        SELECT allocation_attribute_id aa_id, MAX(modified) usage_timestamp
                        FROM allocation_historicalallocationattributeusage
                        WHERE DATE(modified) = '{args["usage_date"]}'
                        GROUP BY aa_id, DATE(modified)
                    ) AS aa_id_usage_timestamp
                    ON haau.allocation_attribute_id = aa_id_usage_timestamp.aa_id
                        AND haau.modified = aa_id_usage_timestamp.usage_timestamp
                ) AS storage_usage_of_the_day
                    ON storage_quota.id = storage_usage_of_the_day.allocation_attribute_id
            """
            monthly_specific_where_clause = """
                AND
                    a.id NOT IN (
                    SELECT allocation_id FROM allocation_allocationlinkage_children
                )
            """
            final_where_clause = "WHERE billing_cycle = 'monthly'"

        elif report_type == "prepaid":
            report_header_type = "Prepaid for"
            item_description = BillingGenerator._get_item_description(PREPAID_COLS)
            prepaid_custom_columns_from_select_top_level = "report.prepaid_expiration prepaid_expiration,\n            report.prepaid_time prepaid_time,"
            prepaid_custom_columns_from_select_lower_level = "data.prepaid_expiration,\ndata.prepaid_time,\n            data.rate * data.prepaid_time AS total_cost"
            prepaid_custom_columns_from_select_lowest_level = (
                "prepaid_billing_date,\nprepaid_expiration,\n            prepaid_time,"
            )
            join_clause = """
                LEFT JOIN (SELECT aa.allocation_id, aa.id, aa.value prepaid_billing_date FROM allocation_allocationattribute aa JOIN allocation_allocationattributetype aat ON aa.allocation_attribute_type_id=aat.id WHERE aat.name='prepaid_billing_date') AS prepaid_billing_date ON a.id=prepaid_billing_date.allocation_id
                LEFT JOIN (SELECT aa.allocation_id, aa.id, aa.value prepaid_expiration FROM allocation_allocationattribute aa JOIN allocation_allocationattributetype aat ON aa.allocation_attribute_type_id=aat.id WHERE aat.name='prepaid_expiration') AS prepaid_expiration ON a.id=prepaid_expiration.allocation_id
                LEFT JOIN (SELECT aa.allocation_id, aa.id, aa.value prepaid_time FROM allocation_allocationattribute aa JOIN allocation_allocationattributetype aat ON aa.allocation_attribute_type_id=aat.id WHERE aat.name='prepaid_time') AS prepaid_time ON a.id=prepaid_time.allocation_id
            """
            final_where_clause = (
                f"WHERE prepaid_billing_date = '{args['delivery_date']}'"
            )

        query_text = f"""
            SELECT
                NULL fields,
                ROW_NUMBER() OVER (ORDER BY report.service_name) spreadsheet_key,
                'N' add_only,
                'N' auto_complete,
                NULL internal_service_delivery_id,
                'Y' submit,
                'CP0001' company,
                'ISP0000030' internal_service_provider,
                'USD' currency,
                '{args["document_date"]}' document_date,
                ('{fiscal_year} ' || '{args["billing_month"]}' || ' {report_header_type} ' || report.sponsor) AS memo,
                '1' row_id,
                NULL internal_service_delivery_line_id,
                '1' internal_service_delivery_line_number,
                {item_description},
                'SC510' spend_category,
                '1' quantity,
                'EA' unit_of_measure,
                report.billing_amount*report.rate unit_cost,
                report.billing_amount*report.rate extended_amount,
                NULL requester,
                report.delivery_date delivery_date,
                ('"' || report.storage_name || '"') AS fileset_memo,
                report.cost_center cost_center,
                {prepaid_custom_columns_from_select_top_level}
                NULL fund,
                NULL,
                NULL,
                NULL,
                {monthly_specific_columns}
                report.rate rate,
                report.service_unit unit
            FROM (
                SELECT
                    '{args["delivery_date"]}' delivery_date,
                    data.service_unit,
                    data.storage_name,
                    data.service_name,
                    data.sponsor,
                    CASE service_rate_category
                        WHEN 'consumption' THEN
                            CASE subsidized
                                WHEN TRUE THEN
                                    CASE (billing_amount_tb - 5) > 0
                                        WHEN TRUE THEN (billing_amount_tb -5)
                                        ELSE 0
                                    END
                                ELSE billing_amount_tb
                            END
                        ELSE billing_amount_tb
                    END billing_amount,
                    data.rate,
                    data.service_rate_category,
                    data.department_number,
                    {"data.cost_center" if prepaid_custom_columns_from_select_lower_level == "" else "data.cost_center,"}
                    {prepaid_custom_columns_from_select_lower_level}
                FROM (
                    SELECT
                        '1' service_id,
                        department_number,
                        storage_name,
                        'Storage2 Active' service_name,
                        u.username sponsor,
                        service_rate_category,
                        cost_center,
                        {prepaid_custom_columns_from_select_lowest_level}
                        'monthly' billing_cycle,
                        TRUE subsidized,
                        FALSE exempt,
                        CASE service_rate_category
                            {additional_category_case_monthly}
                            WHEN 'subscription' THEN 634
                            WHEN 'subscription_500tb' THEN 2643
                            WHEN 'condo' THEN 529
                        END rate,
                        storage_quota,
                        CASE service_rate_category
                            {additional_category_case_monthly_cast}
                            WHEN 'subscription' THEN CEILING(CAST(storage_quota AS FLOAT8) /100)
                            WHEN 'subscription_500tb' THEN CEILING(CAST(storage_quota AS FLOAT8) /500)
                            WHEN 'condo' THEN CEILING(CAST(storage_quota AS FLOAT8) /500)
                        END billing_amount_tb,
                        CASE service_rate_category
                            {additional_category_case_monthly_unit}
                            WHEN 'subscription' THEN '100TB'
                            WHEN 'subscription_500tb' THEN '500TB'
                            WHEN 'condo' THEN '500TB'
                        END service_unit,
                        storage_filesystem_path
                    FROM allocation_allocation a
                    JOIN allocation_allocationstatuschoice astatus ON a.status_id=astatus.id
                    JOIN project_project p ON a.project_id=p.id
                    JOIN auth_user u ON p.pi_id=u.id
                    LEFT JOIN (SELECT aa.allocation_id, aa.value storage_name FROM allocation_allocationattribute aa JOIN allocation_allocationattributetype aat ON aa.allocation_attribute_type_id=aat.id WHERE aat.name='storage_name') AS storage_name ON a.id=storage_name.allocation_id
                    LEFT JOIN (SELECT aa.allocation_id, aa.value storage_filesystem_path FROM allocation_allocationattribute aa JOIN allocation_allocationattributetype aat ON aa.allocation_attribute_type_id=aat.id WHERE aat.name='storage_filesystem_path') AS storage_filesystem_path ON a.id=storage_filesystem_path.allocation_id
                    LEFT JOIN (SELECT aa.allocation_id, aa.value cost_center FROM allocation_allocationattribute aa JOIN allocation_allocationattributetype aat ON aa.allocation_attribute_type_id=aat.id WHERE aat.name='cost_center') AS cost_center ON a.id=cost_center.allocation_id
                    LEFT JOIN (SELECT aa.allocation_id, aa.value department_number FROM allocation_allocationattribute aa JOIN allocation_allocationattributetype aat ON aa.allocation_attribute_type_id=aat.id WHERE aat.name='department_number') AS department_number ON a.id=department_number.allocation_id
                    LEFT JOIN (SELECT aa.allocation_id, aa.value service_rate_category FROM allocation_allocationattribute aa JOIN allocation_allocationattributetype aat ON aa.allocation_attribute_type_id=aat.id WHERE aat.name='service_rate') AS service_rate_category ON a.id=service_rate_category.allocation_id
                    LEFT JOIN (SELECT aa.allocation_id, aa.id, aa.value storage_quota FROM allocation_allocationattribute aa JOIN allocation_allocationattributetype aat ON aa.allocation_attribute_type_id=aat.id WHERE aat.name='storage_quota') AS storage_quota ON a.id=storage_quota.allocation_id
                    {join_clause}
                    JOIN allocation_allocation_resources ar ON ar.allocation_id=a.id
                    JOIN resource_resource r ON r.id=ar.resource_id
                    WHERE
                        r.name = 'Storage2'
                    AND
                    astatus.name = 'Active'
                    {monthly_specific_where_clause}
                ) AS data
                {final_where_clause}
                    AND exempt <> TRUE
            ) AS report 
            WHERE report.billing_amount > 0;
        """

        return query_text
