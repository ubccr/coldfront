from coldfront.core.allocation.models import Allocation

# Create your models here.
class MovableAllocation(Allocation):
            
    class Meta:
        proxy = True
        default_permissions = ()
        permissions = ( 
            ('can_move_allocations', 'Can move allocations'),  
        )
