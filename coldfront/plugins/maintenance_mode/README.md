# Maintenance Mode for ColdFront

Maintenance mode redirects all pages to a maintenance page during an active maintenance event.

It will optionally attempt to stop running django-q tasks and extend allocations expiring during the maintenance.

## Model

| Field | Type | What it does |
| -------- | -------- | -------- |
| start_time | datetime | Specifies a start time for the maintenance window |
| end_time  | datetime | Specifies an end time for the maintenance window  |
| stop_tasks | boolean | Specifies whether or not to try to stop tasks during the maintenance. |
| is_stopped | boolean | Specifies whether or not tasks have been stopped. |
| extension | int | specifies a number of days to extend an allocation by if it will expire during the maintenance |
| message | text | Information to display on the site during the maintenance |

## Options / Configuration

| Environment Variable | What it does |
| -------- | -------- |
| MAINTENANCE_EXCLUDED_TASK_IDS | A list of task IDs that won't be stopped (if stop_tasks is set to True for the maintenance event) |
| MAINTENANCE_EXCLUDED_USERS  | A list of users who will not be redirected during the maintenance. Note: user must be logged in before the maintenance begins. The login page will not be accessible |
| MAINTENANCE_TASK_LOG_DIR | Directory to save information about tasks. This must be writeable by the account running ColdFront and is used to restore task repeat accounts to their previous values if stop_tasks is set to True for the maintenance event. |
| MAINTENANCE_ALLOCATION_IMPACT_PADDING | A padding factor (in days) for determining if an allocations expiration date will be impacted by the maintenance. If the maintenance event has an extension value greater than 0, then allocations expiring between `start_time` and `end_time + MAINTENANCE_ALLOCATION_IMPACT_PADDING` will have their end date extended. |
