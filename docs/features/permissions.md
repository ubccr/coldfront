# Permissions

ColdFront has a robust object-based permission system with role based access control.

## Object-Based Permissions

Assigning permissions in ColdFront involves several parts:

- The type of object to which the permission applies
- The users or groups being granted the permissions
- The action permitted by the permission (view, add, change, delete)
- Any constraints that limit the permission to a subset of objects

Constraints let administrators assign per-object permissions. Users can
be limited to viewing or interacting with subsets of objects based on the
objects' attributes. For example, you can restrict a user to viewing only
resources within a particular tenant.

Permission constraints are declared in JSON format when creating a
permission. They operate similarly to Django ORM queries.

## Roles

ColdFront adds a Roles feature that extends the permission model.
Roles let you define named sets of permissions that can be assigned to
users or groups. This makes it easier to manage permissions for common
job functions such as "Center Director" or "Principal Investigator".

## Model Actions

Models can register custom permission actions beyond the standard view,
add, change, and delete actions. For example, a SlurmCluster model can
register a "sync" action. These actions appear as checkboxes in the
permission form when the model is selected.
