# Background Jobs

ColdFront runs background jobs. Background jobs keep data current and do
maintenance tasks. Examples: the Slurm accounting syncs and the notification
digest.

This page tells you how the job framework works and which processes a center
must run in production.

## Terms

- **Job runner** — a Python class with the job logic. Each runner has a
  `run()` method.
- **System job** — a job runner that ColdFront registers itself. The
  `@system_job` decorator adds the runner to the job registry. Exactly one
  schedule type is set on the decorator.
- **Job row** — one record in the `Job` database table. The record stores the
  schedule, the status, the log output, and the result.
- **Worker** — a management command that creates schedules and executes job
  rows.

## How scheduling works

The `@system_job` decorator accepts one schedule type:

- `interval=N` — run again `N` minutes after each start. A missed occurrence
  is caught up: the next run fires even if its time passed.
- `cron_schedule="0 4 * * *"` — run at the times in a cron expression.
  ColdFront evaluates cron expressions in the default timezone (`TIME_ZONE`).
  A missed occurrence is not replayed. The next run is the first occurrence
  after the current time.

Each job execution is one `Job` row. When a job finishes, the runner enqueues
a new row for the next occurrence. This chain of rows is durable. It keeps a
periodic job alive across worker restarts.

## The worker processes

Two management commands divide the work.

**`taskworker`** — the scheduler entry point. At startup it:

1. Creates the first schedule for each registered system job. Interval jobs
   are ready immediately. Cron jobs are scheduled at the next cron
   occurrence.
2. If a schedule exists with the same parameters, it does not create a
   duplicate. If a cron schedule is stale after downtime, it replaces it with
   the next occurrence.
3. Starts the executor for the configured backend and keeps it running. The
   executor is `db_worker` (DB backend, default) or `rqworker` (Redis
   backend).

`taskworker` does not execute jobs itself. It only creates schedules and
delegates.

**`db_worker`** — the executor for the DB backend. Its loop:

1. Selects job rows that are ready. A row is ready when its status is
   `pending` or `scheduled` and its scheduled time has passed.
2. Claims one row. A row lock prevents two workers from taking the same job.
3. Sets the row to `running`, runs the job, records the log output, and sets
   a terminal status (`completed`, `failed`, or `errored`).
4. For system jobs, enqueues the next occurrence. A shared lock prevents
   duplicate schedules.
5. Sleeps and repeats.

**Do not use a bare `db_worker` as the primary process.** A bare `db_worker`
executes job rows that exist in the `Job` table. It cannot create the first
schedule. With no schedule in the table, it polls an empty table and does
nothing.

## Production setup

Run **one `taskworker` process** under a service manager. This is sufficient.
The embedded executor runs for the lifetime of the service.

Example systemd unit. Adjust the paths and user for your installation.

```ini
[Unit]
Description=ColdFront background jobs
After=network.target

[Service]
Type=simple
User=coldfront
WorkingDirectory=/opt/coldfront
Environment="COLDFRONT_ENV=/etc/coldfront/.env"
ExecStart=/opt/coldfront/.venv/bin/coldfront taskworker
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Notes:

- The `COLDFRONT_TASKS_BACKEND` setting selects the executor. The value `db`
  selects `db_worker`. The value `rq` selects `rqworker` and a Redis queue.
  Default: `db`. See the configuration page for all job settings.
- On each restart, `taskworker` re-seeds the schedules. This repair step is
  necessary after downtime: a cron schedule for an occurrence that passed is
  replaced with the next occurrence.
- Do not run more than one `taskworker` process. The seeding is safe with
  duplicates, but duplicates serve no purpose.

## Optional: additional executors

For more execution capacity, run additional bare `db_worker` processes next
to the one `taskworker` process. The row locks make this safe. Only the
`taskworker` process creates schedules.

## Monitor and troubleshoot

The job list in the admin UI shows each `Job` row with its status, schedule,
log output, and error text.

Symptoms:

| Symptom | Cause | Action |
|---|---|---|
| No jobs run. The `Job` table is empty. | No worker created the first schedule. | Start `taskworker`. |
| A cron job did not run after downtime. | Its scheduled time passed while the worker was down. | Start `taskworker`. The startup repair replaces the stale schedule. |
| A job row stays in `running`. | The worker process died mid-execution. | Restart `taskworker`. Then check the row error text. |
