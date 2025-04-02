from django.db import models
from django.contrib.auth.models import User
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.core.allocation.models import Allocation, AllocationStatusChoice


class AllocationRemovalStatusChoice(TimeStampedModel):
    """ An allocation removal status choice indicates the status of the allocation removal
    
    Attributes:
        name (str): name of the allocation removal status choice
    """
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class AllocationRemovalRequest(TimeStampedModel):
    """ An allocation removal request represents a request to remove an allocation from a project.
    
    Attributes:
        project_pi (User): the user who is the PI of the project the allocation is in
        requestor (User): the user who requested the removal
        allocation (Allocation): the allocation being removed
        allocation_prior_status (AllocationStatusChoice): prior status the allocation had
        status (AllocationRemovalStatusChoice): current status of the removal request
        history (HistoricalRecords): historical record of the removal request
    """
    project_pi = models.ForeignKey(User, on_delete=models.CASCADE, related_name='%(class)s_project_pi')
    requestor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='%(class)s_requestor')
    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE)
    allocation_prior_status = models.ForeignKey(AllocationStatusChoice, on_delete=models.CASCADE)
    status = models.ForeignKey(AllocationRemovalStatusChoice, on_delete=models.CASCADE)
    history = HistoricalRecords()
