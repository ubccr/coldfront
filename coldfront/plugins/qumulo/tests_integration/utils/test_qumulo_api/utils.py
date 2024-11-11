from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI


def create_test_export(
    qumulo_api: QumuloAPI,
    export_fs_path="/test-project",
    description="test-test_project-active",
):
    return qumulo_api.create_allocation(
        protocols=["nfs"],
        export_path=export_fs_path,
        fs_path=export_fs_path,
        name=description,
        limit_in_bytes=10**6,
    )


def print_all_quotas_with_usage(qumulo_api: QumuloAPI) -> None:
    response_quotas = qumulo_api.rc.quota.get_all_quotas_with_status(page_size=None)
    for all_quotas in response_quotas:
        for quota in all_quotas["quotas"]:
            print(
                "%(path)s - id: %(id)s - %(capacity_usage)s bytes used of %(limit)s"
                % quota
            )
