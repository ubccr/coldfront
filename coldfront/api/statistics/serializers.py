from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.statistics.models import Job
from coldfront.core.statistics.models import Node
from coldfront.core.user.models import UserProfile
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
import logging


class NodeSerializer(serializers.ModelSerializer):
    """A serializer for the Node model."""

    class Meta:
        model = Node
        fields = ('name',)
        extra_kwargs = {
            'name': {'validators': []}
        }


class JobUserSerializerField(serializers.Field):
    """A serializer field that handles the conversion between a User
    object and its cluster_uid, stored in its UserProfile object."""

    def to_representation(self, user):
        return UserProfile.objects.get(user=user).cluster_uid

    def to_internal_value(self, cluster_uid):
        return UserProfile.objects.get(cluster_uid=cluster_uid).user


class JobSerializer(serializers.ModelSerializer):
    """A serializer for the Job model."""

    userid = JobUserSerializerField()
    accountid = serializers.SlugRelatedField(
        slug_field='name', queryset=Project.objects.all())
    nodes = NodeSerializer(many=True, required=False)

    logger = logging.getLogger(__name__)

    class Meta:
        model = Job
        fields = (
            'jobslurmid', 'submitdate', 'startdate', 'enddate', 'userid',
            'accountid', 'amount', 'jobstatus', 'partition', 'qos', 'nodes',
            'num_cpus', 'num_req_nodes', 'num_alloc_nodes', 'raw_time',
            'cpu_time'
        )
        extra_kwargs = {
            'amount': {'required': False, 'allow_null': False},
            'num_cpus': {'required': False, 'allow_null': True},
            'num_req_nodes': {'required': False, 'allow_null': True},
            'num_alloc_nodes': {'required': False, 'allow_null': True},
            'raw_time': {'required': False, 'allow_null': True},
            'cpu_time': {'required': False, 'allow_null': True}
        }

    def create(self, validated_data):
        nodes_data = []
        if 'nodes' in validated_data:
            nodes_data = validated_data.pop('nodes')
        job = Job.objects.create(**validated_data)
        for node_data in nodes_data:
            node = Node.objects.get_or_create(**node_data)[0]
            job.nodes.add(node)
        job.save()
        return job

    def update(self, instance, validated_data):
        instance.jobslurmid = validated_data.get(
            'jobslurmid', instance.jobslurmid)
        instance.submitdate = validated_data.get(
            'submitdate', instance.submitdate)
        instance.startdate = validated_data.get(
            'startdate', instance.startdate)
        instance.enddate = validated_data.get('enddate', instance.enddate)
        instance.userid = validated_data.get('userid', instance.userid)
        instance.accountid = validated_data.get(
            'accountid', instance.accountid)
        instance.amount = validated_data.get('amount', instance.amount)
        instance.jobstatus = validated_data.get(
            'jobstatus', instance.jobstatus)
        instance.partition = validated_data.get(
            'partition', instance.partition)
        instance.qos = validated_data.get('qos', instance.qos)
        if 'nodes' in validated_data:
            nodes_data = validated_data.get('nodes')
            for node_data in nodes_data:
                node = Node.objects.get_or_create(**node_data)[0]
                instance.nodes.add(node)
        instance.num_cpus = validated_data.get('num_cpus', instance.num_cpus)
        instance.num_req_nodes = validated_data.get(
            'num_req_nodes', instance.num_req_nodes)
        instance.num_alloc_nodes = validated_data.get(
            'num_alloc_nodes', instance.num_alloc_nodes)
        instance.raw_time = validated_data.get('raw_time', instance.raw_time)
        instance.cpu_time = validated_data.get('cpu_time', instance.cpu_time)
        instance.save()
        return instance

    def validate(self, data):
        # Check that the specified dates occur in chronological order.
        submitdate = data['submitdate'] if 'submitdate' in data else None
        startdate = data['startdate'] if 'startdate' in data else None
        enddate = data['enddate'] if 'enddate' in data else None
        if submitdate and startdate and startdate < submitdate:
            message = (
                f'Job start date {startdate} occurs before Job submit date '
                f'{submitdate}.')
            self.logger.error(message)
            raise serializers.ValidationError(message)
        if startdate and enddate and enddate < startdate:
            message = (
                f'Job end date {enddate} occurs before Job start date '
                f'{startdate}.')
            self.logger.error(message)
            raise serializers.ValidationError(message)
        if submitdate and enddate and enddate < submitdate:
            message = (
                f'Job end date {enddate} occurs before Job submit date '
                f'{submitdate}.')
            self.logger.error(message)
            raise serializers.ValidationError(message)

        # Check that necessary, expected objects exist.
        user = data['userid']
        account = data['accountid']
        try:
            get_accounting_allocation_objects(user, account)
        except ProjectUser.DoesNotExist:
            message = (
                f'User {user.cluster_uid} is not a member of Project '
                f'{account.name}.')
            self.logger.error(message)
            raise serializers.ValidationError(message)
        except Allocation.DoesNotExist:
            message = (
                f'Account {account.name} has no active compute allocation.')
            self.logger.error(message)
            raise serializers.ValidationError(message)
        except Allocation.MultipleObjectsReturned:
            self.logger.error(
                f'Account {account.name} has more than one active compute '
                f'allocation.')
            raise serializers.ValidationError(
                'An unexpected error occurred during request validation.')
        except AllocationUser.DoesNotExist:
            message = (
                f'User {user} is not a member of the compute allocation for '
                f'Account {account.name}.')
            self.logger.error(message)
            raise serializers.ValidationError(message)
        except (MultipleObjectsReturned, ObjectDoesNotExist) as e:
            self.logger.error(
                f'Failed to retrieve a required database object. Details: {e}')
            raise serializers.ValidationError(
                'An unexpected error occurred during request validation.')

        return data

    def validate_userid(self, user):
        # If the Job already exists, check that the user matches the existing
        # one.
        if self.instance:
            if self.instance.userid and user.pk != self.instance.userid.pk:
                message = (
                    f'Specified user {user} does not match already associated '
                    f'user {self.instance.userid}.')
                self.logger.error(message)
                raise serializers.ValidationError(message)
        return user

    def validate_accountid(self, account):
        # If the Job already exists, check that the account matches the
        # existing one.
        if self.instance:
            if (self.instance.accountid and
                    account.pk != self.instance.accountid.pk):
                message = (
                    f'Specified account {account} does not match already '
                    f'associated account {self.instance.accountid}.')
                self.logger.error(message)
                raise serializers.ValidationError(message)
        return account

    def validate_partition(self, partition):
        # If the Job already exists, and it has a partition, check that the
        # partition matches the existing one.
        if self.instance:
            if partition and self.instance.partition:
                if partition != self.instance.partition:
                    message = (
                        f'Specified partition {partition} does not match '
                        f'already associated partition '
                        f'{self.instance.partition}.')
                    self.logger.error(message)

                    # Temporary: A job script may list multiple partitions. At
                    # submission time, only one is used. At completion time,
                    # the partition value is read from the job script, leading
                    # to a discrepancy. The completion plugin should be
                    # modified to use the actual partition used. This check
                    # should be relaxed until then.
                    # raise serializers.ValidationError(message)

        return partition

    def validate_qos(self, qos):
        # If the Job already exists, and it has a qos, check that the qos
        # matches the existing one.
        if self.instance:
            if qos and self.instance.qos:
                if qos != self.instance.qos:
                    message = (
                        f'Specified qos {qos} does not match already '
                        f'associated qos {self.instance.qos}.')
                    self.logger.error(message)

                    # Temporary: The QoS should never change, but this check
                    # should be relaxed until confirmation is received.
                    # raise serializers.ValidationError(message)

        return qos
