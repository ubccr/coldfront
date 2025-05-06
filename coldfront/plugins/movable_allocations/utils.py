def check_over_allocation_limit(allocation_obj_moving, allocation_objs):
        resource = allocation_obj_moving.get_parent_resource
        limit_obj = resource.resourceattribute_set.filter(
            resource_attribute_type__name="allocation_limit"
        ).first()
        if not limit_obj:
            return False

        return int(limit_obj.value) < allocation_objs.filter(resources=resource).count() + 1

def check_resource_is_allowed(allocation_obj_moving, project_obj):
    forbidden_resources = project_obj.get_env.get("forbidden_resources")
    resource = allocation_obj_moving.get_parent_resource.name
    return resource not in forbidden_resources
