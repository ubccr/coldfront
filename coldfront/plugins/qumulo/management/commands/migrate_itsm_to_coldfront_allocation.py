from icecream import ic

from django.core.management.base import BaseCommand

from coldfront.plugins.qumulo.services.itsm.migrate_to_coldfront import (
    MigrateToColdfront,
)

from icecream import ic


class Command(BaseCommand):

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "fileset", type=str, help="The fileset_name or fileset_alias"
        )
        parser.add_argument(
            "--fileset_alias",
            action="store_true",
            help="Queries by fileset_alias instead of by fileset_name",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Execute validations but does not create any records",
        )

    def handle(self, *args, **options) -> None:
        fileset = options["fileset"]
        ic(fileset)
        find_by_alias = options["fileset_alias"]
        ic(find_by_alias)
        dry_run = options["--dry-run"]
        ic(dry_run)

        migrate_from_itsm_to_coldfront = MigrateToColdfront(dry_run)
        if find_by_alias:
            result = migrate_from_itsm_to_coldfront.by_fileset_alias(fileset)
        else:
            result = migrate_from_itsm_to_coldfront.by_fileset_name(fileset)

        ic(result)
