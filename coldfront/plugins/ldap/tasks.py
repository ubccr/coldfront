from coldfront.plugins.ldap.utils import collect_update_project_status_membership

def update_group_membership_ldap():
    '''Update ProjectUsers for active Projects using ADGroup and ADUser data
    '''
    collect_update_project_status_membership()

def id_add_projects():
    '''ID and add new projects from ADGroup and ADUser data
    '''
