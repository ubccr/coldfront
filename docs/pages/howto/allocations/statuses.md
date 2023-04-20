# Allocation Statuses

Allocations in ColdFront have many status options.  Some tie to ColdFront plugins, some trigger other actions, and others are simply placeholders used in a center's policy process.  The current status options available in ColdFront are:

#### Active  
When an allocation is in 'active' status:  

- The FreeIPA plugin syncs the allocation attribute freeipa_group for all allocation users, adding users to the group if they are not already members  
- The Slurm plugin syncs Slurm attributes with the Slurm database for all allocations users  
- It's important to point out that unless these plugins are run to properly sync the systems, or the center is using some other mechanism for granting access to a resource, the allocation users' access will not yet be active on the systems, despite this allocation status being 'active'  
- Emails are sent to all allocation users letting them know the request has been activated  

#### Approved  
- This status currently provides no automation for any plugins.  It can be used as part of a center's business process.  For example, your center may have a committee that reviews allocation requests prior to the system administrators activating them.  This status could be used by the allocation request reviewers to mark it for the admins to activate.  
- When in this status, the allocation users would not have access to the resource yet.  

#### Denied  
- This status currently provides no automation for any plugins.  It can be used as part of a center's business process.  This status could be used by a committee reviewing allocation requests or by system administrators who desire to deny the request for whatever reason.  
- A reason for denying the allocation request should be provided so allocation users can view this information  
- When in this status, the allocation users would not have access to the resource.  
- Emails are sent to all allocation users letting them know the request has been denied  

#### Expired  
When an allocation is in 'expired' status:  

- The FreeIPA plugin syncs the allocation attribute freeipa_group for all allocation users, removing users from the group unless they're on another active allocation with the same group membership  
- The Slurm plugin (slurm_check) syncs Slurm attributes with the Slurm database for all allocations users, removing Slurm associations and accounts if necessary
- It's important to point out that unless these plugins are run to properly remove access, or the center is using some other mechanism for granting access to a resource, the allocation users' access will still be active on the systems, despite this allocation status being 'expired'  
- Emails are sent to all allocation users letting them know the allocation has expired   


#### Inactive (Renewed)  
- When an allocation is renewed, a new allocation is created and the original allocation is set to this status  
- Changes can not be made to this allocation  
- It remains for historical purposes  


#### New  
- This is the status an allocation is placed in when first created   
- An email gets sent to 'EMAIL_TICKET_SYSTEM_ADDRESS' configured in coldfront.env  
- Emails are sent to all allocation users letting them know the request has been submitted  
- Allocation is listed in 'Allocation Requests' list for administrators to process  
- When in this status, the allocation users would not have access to the resource yet   

#### Paid  
- This status currently provides no automation for any plugins.  It can be used as part of a center's business process.
- The allocation will display for staff on the 'Invoice' list  

#### Payment Declined  
- This status currently provides no automation for any plugins.  It can be used as part of a center's business process.
- The allocation will display for staff on the 'Invoice' list  

#### Payment Pending  
- This status currently provides no automation for any plugins.  It can be used as part of a center's business process.  
- The allocation will display for staff on the 'Invoice' list  

#### Payment Requested  
- This status currently provides no automation for any plugins.  It can be used as part of a center's business process.  
- The allocation will display for staff on the 'Invoice' list  

#### Pending  
 - This status currently provides no automation for any plugins.  It can be used as part of a center's business process.  

#### Renewal Requested  
- This is the state an active allocation gets put in when the PI/manager requests to renew it  
- The allocation will appear on the "Allocation Requests" page for administrators to process  
- If the allocation renewal isn't processed prior to the original allocation expiration date, the allocation will expire and the allocation users will get a notification email  
- An email gets sent to 'EMAIL_TICKET_SYSTEM_ADDRESS' configured in coldfront.env  
- Emails are sent to all allocation users letting them know the renewal request has been submitted  

#### Revoked  
- The FreeIPA plugin syncs the allocation attribute freeipa_group for all allocation users, removing users from the group unless they're on another active allocation with the same group membership  
- The Slurm plugin (slurm_check) syncs Slurm attributes with the Slurm database for all allocations users, removing Slurm associations and accounts if necessary
- It's important to point out that unless these plugins are run to properly remove access, or the center is using some other mechanism for granting access to a resource, the allocation users' access will still be active on the systems, despite this allocation status being 'revoked'  
- Emails are sent to all allocation users letting them know the allocation has been revoked and their access to the resource has been removed    

#### Unpaid  
- This status currently provides no automation for any plugins.  It can be used as part of a center's business process.
