# Billing & Invoicing

ColdFront includes a billing app for allocation-based invoicing. It lets an
HPC center charge research groups for the resources they use — storage
quotas billed per terabyte and compute time billed per service unit (SU) on
Slurm accounts — and issue invoices for each billing period.

## Core Models

- **Invoice** — A bill sent to a responsible owner for a billing period,
  optionally restricted to a subset of the owner's projects.
- **Invoice Line Item** — A single row on an invoice: a charge, free
  allowance, discount, or credit.
- **Rate** — A per-unit price scoped to a resource (one rate per scope).
- **Free Allowance** — A quantity of a unit granted free, per owner or
  per project.
- **Discount** — A percentage or flat reduction applied to an invoice.
- **Unit Format** — The billing dimension: `bytes`, `service_units`,
  `core_hours`, or `per_item`.

## Invoice Lifecycle

An invoice moves through a status workflow:

```
Draft ──generate──→ Draft
Draft ──invoice──→ Invoiced ──pay──→ Paid
Draft ──void──→ Void      (also from Invoiced)
```

Each transition requires a permission: `generate_invoice`, `finalize_invoice`,
`pay_invoice`, or `void_invoice`.

## What Gets Billed

Invoices are generated from registered **billing sources**, for example:

- **Storage** — `StorageQuota` allocations are billed per terabyte against
  the storage resource's rate.
- **Slurm** — `SlurmAccount` compute usage is billed per service unit against
  the cluster's rate.

Free allowances are stacked (owner-level first, then project-level) before
discounts are applied to the net total.

## Extensibility

Billing sources are registered through the plugin registry with
`register_billing_source`. Plugins can add their own billable models (e.g. a
custom metering system) without modifying core ColdFront. See
[Billing Plugins](../plugins/billing.md).

## PDF Export

Any invoice can be exported as a simple PDF with its line items and totals
from the invoice detail page.
