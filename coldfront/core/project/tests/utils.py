from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest


def create_fca_project_and_request(project_name, project_status_name,
                                   allocation_period, requester, pi,
                                   request_status_name):
    """Create an FCA project and a corresponding new project request
    with the given parameters. Return both."""
    project_status = ProjectStatusChoice.objects.get(name=project_status_name)
    new_project = Project.objects.create(
        name=project_name,
        status=project_status,
        title=project_name,
        description=f'Description of {project_name}.')
    request_status = ProjectAllocationRequestStatusChoice.objects.get(
        name=request_status_name)
    new_project_request = SavioProjectAllocationRequest.objects.create(
        requester=requester,
        allocation_type=SavioProjectAllocationRequest.FCA,
        allocation_period=allocation_period,
        pi=pi,
        project=new_project,
        survey_answers={},
        status=request_status)
    return new_project, new_project_request
