import csv
import datetime
import os

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.core.subscription.models import (AttributeType, Subscription,
                                                 SubscriptionAttribute,
                                                 SubscriptionAttributeType,
                                                 SubscriptionAttributeUsage,
                                                 SubscriptionStatusChoice,
                                                 SubscriptionUser,
                                                 SubscriptionUserStatusChoice)

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding subscriptions ...')
        AttributeType.objects.all().delete()
        filepath = os.path.join(base_dir, 'local_data', 's_atttriute_type.tsv')
        with open(filepath, 'r') as fp:
            for line in fp:
                AttributeType.objects.create(name=line.strip())

        SubscriptionAttributeType.objects.all().delete()
        filepath = os.path.join(base_dir, 'local_data', 'subscription_attribute_type.tsv')
        # print(filepath)
        with open(filepath, 'r') as fp:
            for line in fp:
                attribute_type, name, has_usage = line.strip().split('\t')
                if has_usage == "True":
                    has_usage = True
                else:
                    has_usage = False
                # print(attribute_type, name, has_usage)
                subscription_attribute_type_obj = SubscriptionAttributeType.objects.create(
                    attribute_type=AttributeType.objects.get(name=attribute_type),
                    name=name,
                    has_usage=has_usage
                )
                # print(subscription_attribute_type_obj)

        Subscription.objects.all().delete()
        SubscriptionUser.objects.all().delete()
        SubscriptionAttribute.objects.all().delete()
        SubscriptionAttributeUsage.objects.all().delete()

        subscription_status_choices = {}
        subscription_status_choices['ACT'] = SubscriptionStatusChoice.objects.get(name='Active')
        subscription_status_choices['PEN'] = SubscriptionStatusChoice.objects.get(name='Pending')
        subscription_status_choices['EXP'] = SubscriptionStatusChoice.objects.get(name='Expired')
        subscription_status_choices['DEN'] = SubscriptionStatusChoice.objects.get(name='Denied')
        subscription_status_choices['REV'] = SubscriptionStatusChoice.objects.get(name='Revoked')
        subscription_status_choices['UNP'] = SubscriptionStatusChoice.objects.get(name='Unpaid')
        subscription_status_choices['NEW'] = SubscriptionStatusChoice.objects.get(name='New')
        subscription_status_choices['INA'] = SubscriptionStatusChoice.objects.get(name='Inactive (Renewed)')
        subscription_status_choices['APR'] = SubscriptionStatusChoice.objects.get(name='Approved')

        subscription_user_status_choices = {}
        subscription_user_status_choices['ACT'] = SubscriptionUserStatusChoice.objects.get(name='Active')
        subscription_user_status_choices['PEA'] = SubscriptionUserStatusChoice.objects.get(name='Denied')
        subscription_user_status_choices['PER'] = SubscriptionUserStatusChoice.objects.get(name='Pending - Add')
        subscription_user_status_choices['DEN'] = SubscriptionUserStatusChoice.objects.get(name='Pending - Remove')
        subscription_user_status_choices['REM'] = SubscriptionUserStatusChoice.objects.get(name='Removed')

        filepath = os.path.join(base_dir, 'local_data', 'subscriptions.tsv')
        with open(filepath, 'r') as fp:
            lines = fp.read().split('$$$$$$$$$$-new-line-$$$$$$$$$$')
            for line in lines:
                if not line.strip():
                    continue
                created, modified, title, pi_username, project_status, quantity, resource_name, status, active_util, justification, attributes, users = line.split(
                    '\t')

                # print(title, pi_username, project_status, quantity, resource_name, status, active_util, justification, attributes, users)

                # print(title, pi_username, project_status)
                pi_user = User.objects.get(username=pi_username)
                try:
                    project_obj = Project.objects.get(
                        title=title.strip(), pi__username=pi_username.strip(), status__name=project_status)
                except:
                    print(title.strip(), pi_username.strip())

                resource_obj = Resource.objects.get(name=resource_name)
                end_date_datetime_obj = datetime.datetime.strptime(active_util, '%Y-%m-%d')

                created = datetime.datetime.strptime(created.strip(), '%Y-%m-%d %H:%M:%S').date()
                modified = datetime.datetime.strptime(modified.strip(), '%Y-%m-%d %H:%M:%S').date()
                subscription_obj = Subscription.objects.create(
                    created=created,
                    modified=modified,
                    project=project_obj,
                    status=subscription_status_choices[status],
                    end_date=end_date_datetime_obj,
                    quantity=int(quantity),
                    justification=justification.strip()
                )
                subscription_obj.resources.add(resource_obj)

                for linked_resource in resource_obj.linked_resources.all():
                    subscription_obj.resources.add(linked_resource)

                subscription_attribute_type_obj = SubscriptionAttributeType.objects.get(name='slurm_user_specs')
                subscription_attribute_obj = SubscriptionAttribute.objects.create(
                    subscription=subscription_obj,
                    subscription_attribute_type=subscription_attribute_type_obj,
                    value='Fairshare=parent',
                    is_private=True
                )

                if attributes != 'N/A':
                    for subscription_attribute in attributes.split(';'):
                        name, value, is_private, usage_value = subscription_attribute.split(',')
                        if is_private == 'True':
                            is_private = True
                        else:
                            is_private = False
                        # print(subscription_attribute)
                        subscription_attribute_type_obj = SubscriptionAttributeType.objects.get(name=name)
                        subscription_attribute_obj = SubscriptionAttribute.objects.create(
                            subscription=subscription_obj,
                            subscription_attribute_type=subscription_attribute_type_obj,
                            value=value,
                            is_private=is_private
                        )

                        if subscription_attribute_obj.subscription_attribute_type.has_usage and usage_value != 'N/A':
                            subscription_attribute_usage_obj = SubscriptionAttributeUsage(
                                subscription_attribute=subscription_attribute_obj,
                                value=usage_value
                            )
                            subscription_attribute_usage_obj.save()

                try:
                    if users != 'N/A':
                        for user in users.split(';'):
                            username, user_status = user.split(',')
                            user_obj = User.objects.get(username=username)
                            subscription_user_obj = SubscriptionUser.objects.create(
                                subscription=subscription_obj,
                                user=user_obj,
                                status=subscription_user_status_choices[user_status]
                            )
                except:
                    print(title, pi_username, project_status, quantity, resource_name,
                          status, active_util, justification, attributes, users)

                # subscription_user_array = []
                # for subscription_user in subscription.subscriptionuserstatus_set.all():
                #     subscription_user_array.append(','.join((subscription_user.user.username, subscription_user.status)))

                # subscription_user_array_joined = ';'.join(subscription_user_array)
                # row.append(subscription_user_array_joined)
                # print(row)
                # csvfile.writerow(row)

        print('Finished adding subscriptions.')
