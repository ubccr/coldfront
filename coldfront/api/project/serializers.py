from datetime import datetime

from django.contrib.auth.models import User
from rest_framework import serializers

from coldfront.core.project.models import Project, \
    ProjectUserRemovalRequestStatusChoice, ProjectUserRemovalRequest, \
    ProjectUser, ProjectUserStatusChoice, ProjectUserRoleChoice


class ProjectSerializer(serializers.ModelSerializer):
    """A serializer for the Project model."""

    class Meta:
        model = Project
        fields = '__all__'


class ProjectUserSerializer(serializers.ModelSerializer):
    """A serializer for the ProjectUser model."""

    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ProjectUserStatusChoice.objects.all())
    role = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ProjectUserRoleChoice.objects.all())
    user = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all())
    project = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Project.objects.all())

    class Meta:
        model = ProjectUser
        fields = ('id', 'user', 'project', 'role', 'status')


class ProjectUserRemovalRequestSerializer(serializers.ModelSerializer):
    """A serializer for the ProjectUserRemovalRequest model."""
    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ProjectUserRemovalRequestStatusChoice.objects.all())

    project_user = ProjectUserSerializer(read_only=True,
                                         allow_null=True,
                                         required=False)

    class Meta:
        model = ProjectUserRemovalRequest
        fields = ('id', 'completion_time', 'status', 'project_user')
        extra_kwargs = {
            'id': {'read_only': True},
            'completion_time': {'required': False, 'allow_null': True},
        }

    def validate(self, data):
        """If the status is being changed to 'Complete', ensure that a
        completion_time is given."""
        if ('status' in data and
                data['status'] == 'Complete' and
                not isinstance(data.get('completion_time', None), datetime)):
            message = 'No completion time is given.'
            raise serializers.ValidationError(message)
        return data
