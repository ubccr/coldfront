import os
import csv
import datetime

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from coldfront.core.project.models import (Project,
                                           ProjectTypeChoice,
                                           ProjectStatusChoice,
                                           ProjectUser,
                                           ProjectUserRoleChoice,
                                           ProjectUserStatusChoice)
from coldfront.core.allocation.models import (Allocation,
                                              AllocationStatusChoice,
                                              AllocationAttributeType,
                                              AllocationAttribute,
                                              AllocationUserNote,
                                              AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.core.resource.models import Resource


class Command(BaseCommand):
    def generate_slurm_account_name(self, project_obj):
        num = str(project_obj.pk)
        string = '00000'
        string = string[:-len(num)] + num
        project_type = project_obj.type.name
        letter = 'r'
        if project_type == 'Class':
            letter = 'c'

        return letter + string

    def get_new_end_date_from_list(self, expire_dates, check_date=None, buffer_days=0):
        """
        Finds a new end date based on the given list of expire dates.

        :param expire_dates: List of expire dates
        :param check_date: Date that is checked against the list of expire dates. If None then it's
        set to today
        :param buffer_days: Number of days before the current expire date where the end date should be
        set to the next expire date
        :return: A new end date
        """
        if check_date is None:
            check_date = datetime.date.today()

        expire_dates.sort()

        buffer_dates = [date - datetime.timedelta(days=buffer_days) for date in expire_dates]

        end_date = None
        total_dates = len(expire_dates)
        for i in range(total_dates):
            if check_date < expire_dates[i]:
                if check_date >= buffer_dates[i]:
                    end_date = expire_dates[(i + 1) % total_dates]
                    if (i + 1) % total_dates == 0:
                        end_date = end_date.replace(end_date.year + 1)
                else:
                    end_date = expire_dates[i]
                break
            elif i == total_dates - 1:
                expire_date = expire_dates[0]
                end_date = expire_date.replace(expire_date.year + 1)

        return end_date

    def handle(self, *args, **kwargs):
        print("Importing Geode Projects...")
        cwd = os.getcwd()
        file_name = "geode-projects.csv"
        with open(os.path.join(cwd, file_name), 'r') as csv_file:
            reader = csv.DictReader(csv_file)

            organizations = dict()
            for row in reader:
                organization = row["Org"].strip()
                project_obj = None
                if organization == "BL-COAS":
                    self.import_geode_project(row)
                else:
                    if organizations.get(organization) is None:
                        project_obj = self.import_geode_project(row)
                    else:
                        project_obj = self.import_geode_project(row, organizations[organization])

                    if project_obj is None:
                        continue

                    organizations[organization] = project_obj

        print("Finished importing Geode-Projects")

    def import_geode_project(self, row, project_obj=None):
        pi_username = row["Primary Contact"]
        if not pi_username:
            return

        pi_username = pi_username.strip()
        pi_username_split = []
        if ',' in pi_username:
            pi_username_split = pi_username.split(',')
            pi_username = pi_username.split(',')[0]
            pi_username = pi_username.strip()

        use_indefinitely = False
        end_date_raw = row["End Date"]
        if not end_date_raw or end_date_raw == "n/a" or end_date_raw == '?':
            use_indefinitely = True
            end_date = None
        else:
            end_date_split = row["End Date"].split("/")
            end_date = datetime.datetime(
                int(end_date_split[2]), int(end_date_split[0]), int(end_date_split[1])
            )
            if end_date < datetime.datetime.today():
                return

        if project_obj is None:
            project_obj = self.create_project(pi_username, end_date)
        elif project_obj.pi.username != pi_username:
            project_obj = self.create_project(pi_username, end_date)

        start_date = row["Start Date"]
        if not start_date:
            start_date = datetime.datetime.today()
        else:
            start_date_split = start_date.split("/")
            start_date = datetime.datetime(
                int(start_date_split[2]), int(start_date_split[0]), int(start_date_split[1])
            )

        billing_start_date = row[" Billing Start Date "]
        if not billing_start_date or billing_start_date == " n/a " or billing_start_date == "n/a":
            billing_start_date = None
        else:
            billing_start_date_split = billing_start_date.split("/")
            billing_start_date = datetime.datetime(
                int(billing_start_date_split[2]), int(billing_start_date_split[0]), int(billing_start_date_split[1])
            )

        billing_end_date = row[" Billing End Date "]
        if not billing_end_date or billing_end_date == " n/a " or billing_end_date == "n/a":
            billing_end_date = None
        else:
            billing_end_date_split = billing_end_date.split("/")
            billing_end_date = datetime.datetime(
                int(billing_end_date_split[2]), int(billing_end_date_split[0]), int(billing_end_date_split[1])
            )

        quota_files = row["Quota Files (M)"].strip()
        if not quota_files:
            quota_files = 0.0
        quota_files = float(quota_files)

        account_num = row["Account_Num"].strip()
        if not account_num or account_num == "n/a":
            account_num = ""

        sub_account_num = row["Sub_account"].strip()
        if not sub_account_num or sub_account_num == "n/a":
            sub_account_num = ""

        quota_data = int(row["Quota Data (GiBs)"])
        billing_rate = float(row["Billing Rate"])
        billable_amount_annual = quota_data * billing_rate
        billable_amount_monthly = billable_amount_annual / 12
        allocation_obj = Allocation.objects.create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name="Active"),
            start_date=start_date,
            end_date=end_date,
            use_indefinitely=use_indefinitely,
            storage_space=quota_data,
            storage_space_unit="GB",
            primary_contact=pi_username,
            secondary_contact=row["Secondary Contact"].strip(),
            fiscal_officer=row["Fiscal Officer"].strip(),
            account_number=account_num,
            sub_account_number=sub_account_num,
            it_pros=row["IT Pro Contact"].strip(),
            first_name=project_obj.pi.first_name,
            last_name=project_obj.pi.last_name,
            email=project_obj.pi.email,
            terms_of_service=True,
            data_management_responsibilities=True,
            admin_ads_group=row["Admin Group"].strip(),
            user_ads_group=row["Users Group"].strip(),
            confirm_best_practices=True,
            data_management_plan="N/A. Allocation was imported.",
            share_name=row["Share Name"].strip(),
            share_path=row["MountPath"].strip(),
            organization=row["Org"].strip(),
            billing_rate=billing_rate,
            billable_amount_annual=billable_amount_annual,
            billable_amount_monthly=billable_amount_monthly,
            actively_billing=row[" Billing? "].strip(),
            billing_start_date=billing_start_date,
            billing_end_date=billing_end_date,
            quota_files=quota_files,
            fileset=row["Fileset"].strip(),
            mou_link=row["MOU Link"].strip()
        )
        allocation_obj.resources.add(Resource.objects.get(name="Geode-Projects"))

        AllocationUser.objects.create(
            allocation=allocation_obj,
            user=project_obj.pi,
            status=AllocationUserStatusChoice.objects.get(name="Active")
        )

        if len(pi_username_split) > 1:
            manager_username = pi_username_split[1]
            self.create_project_and_allocation_user(manager_username, project_obj, allocation_obj)

        for username in [row["Secondary Contact"], row["IT Pro Contact"], row["Fiscal Officer"], row["Primary Contact"]]:
            if not username:
                continue

            if ',' in username:
                if '@' in username or username == 'College MOU':
                    continue

                usernames = username.split(',')
                for username in usernames:
                    self.create_project_and_allocation_user(username, project_obj, allocation_obj)
            else:
                if '@' in username or username == 'College MOU':
                    continue
                self.create_project_and_allocation_user(username, project_obj, allocation_obj)

        if account_num:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Account Number"),
                allocation=allocation_obj,
                value=account_num
            )

        if sub_account_num:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Sub-Account Number"),
                allocation=allocation_obj,
                value=sub_account_num
            )

        if row["Share Name"]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Share Name"),
                allocation=allocation_obj,
                value=row["Share Name"].strip()
            )

        if row["MountPath"]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Share Path"),
                allocation=allocation_obj,
                value=row["MountPath"].strip()
            )

        if row["Org"]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Organization"),
                allocation=allocation_obj,
                value=row["Org"].strip()
            )

        if billing_rate > 0:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Billing Rate"),
                allocation=allocation_obj,
                value=billing_rate
            )

        if billable_amount_annual > 0:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Billable Amount Annual"),
                allocation=allocation_obj,
                value=billable_amount_annual
            )

        if billable_amount_monthly > 0:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Billable Amount Monthly"),
                allocation=allocation_obj,
                value=billable_amount_monthly
            )

        if row[" Billing? "]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Actively Billing"),
                allocation=allocation_obj,
                value=row[" Billing? "].strip()
            )

        if billing_start_date:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Billing Start Date"),
                allocation=allocation_obj,
                value=billing_start_date
            )

        if billing_end_date:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Billing End Date"),
                allocation=allocation_obj,
                value=billing_end_date
            )

        if quota_files > 0:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Quota Files"),
                allocation=allocation_obj,
                value=quota_files
            )

        if row["Fileset"]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Fileset"),
                allocation=allocation_obj,
                value=row["Fileset"].strip()
            )

        if row["MOU Link"]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="MOU Link"),
                allocation=allocation_obj,
                value=row["MOU Link"].strip()
            )

        if row["Admin Group"]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Admin Group"),
                allocation=allocation_obj,
                value=row["Admin Group"].strip()
            )

        if row["Users Group"]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Users Group"),
                allocation=allocation_obj,
                value=row["Users Group"].strip()
            )

        if row["Fiscal Officer"]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Fiscal Officer"),
                allocation=allocation_obj,
                value=row["Fiscal Officer"].strip()
            )

        if row["IT Pro Contact"]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="IT Pro Contact"),
                allocation=allocation_obj,
                value=row["IT Pro Contact"].strip()
            )

        if row["Primary Contact"]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Primary Contact"),
                allocation=allocation_obj,
                value=row["Primary Contact"].strip()
            )

        if row["Secondary Contact"]:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Secondary Contact"),
                allocation=allocation_obj,
                value=row["Secondary Contact"].strip()
            )

        if quota_data > 0:
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(name="Storage Quota (GB)"),
                allocation=allocation_obj,
                value=quota_data
            )

        if row["Notes"]:
            AllocationUserNote.objects.create(
                allocation=allocation_obj,
                is_private=True,
                note=row["Notes"],
                author=User.objects.get(username="cmcclary")
            )

        return project_obj

    def create_project(self, pi_username, end_date):
        pi_obj, _ = User.objects.get_or_create(
            username=pi_username
        )

        project_description = "This project was imported."

        if end_date is None:
            project_end_date = self.get_new_end_date_from_list(
                [datetime.datetime(datetime.datetime.today().year, 6, 30), ],
                datetime.datetime.today(),
                90
            )
        else:
            project_end_date = self.get_new_end_date_from_list(
                [datetime.datetime(end_date.year, 6, 30), ],
                datetime.datetime.today(),
                90
            )

        project_obj = Project.objects.create(
            title="",
            description=project_description,
            pi=pi_obj,
            max_managers=3,
            requestor_id=pi_obj.pk,
            type=ProjectTypeChoice.objects.get(name="Research"),
            status=ProjectStatusChoice.objects.get(name="Active"),
            end_date=project_end_date
        )
        project_obj.slurm_account_name = self.generate_slurm_account_name(project_obj)
        project_obj.title = f"New Project {project_obj.pk}"
        project_obj.save()

        ProjectUser.objects.create(
            user=pi_obj,
            project=project_obj,
            role=ProjectUserRoleChoice.objects.get(name="Manager"),
            status=ProjectUserStatusChoice.objects.get(name="Active")
        )

        return project_obj

    def create_project_and_allocation_user(self, username, project_obj, allocation_obj):
        username = username.strip()
        user_obj, _ = User.objects.get_or_create(username=username)

        ProjectUser.objects.get_or_create(
            user=user_obj,
            project=project_obj,
            role=ProjectUserRoleChoice.objects.get(name="Manager"),
            status=ProjectUserStatusChoice.objects.get(name="Active")
        )

        AllocationUser.objects.get_or_create(
            allocation=allocation_obj,
            user=user_obj,
            status=AllocationUserStatusChoice.objects.get(name="Active")
        )
