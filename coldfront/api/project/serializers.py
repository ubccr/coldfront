from coldfront.core.project.models import Project
from rest_framework import serializers


class ProjectSerializer(serializers.ModelSerializer):
    """A serializer for the Project model."""

    class Meta:
        model = Project
        fields = '__all__'
