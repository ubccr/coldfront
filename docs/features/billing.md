# Billing & Invoicing

ColdFront includes a billing app for allocation-based invoicing. It lets an
HPC center charge research groups for the resources they use — storage
quotas billed per terabyte and compute time billed per service unit (SU) on
Slurm accounts — and issue invoices for each billing period.

## Core Models

- **Invoice** — A bill sent to a responsible owner for a billing period,
  optionally restricted to specific billing source types.
- **Invoice Line Item** — A single row on an invoice: a charge, free
  allowance, discount, or credit.
- **Rate** — A per-unit price scoped to a resource (one rate per scope).
- **Free Allowance** — A quantity of a unit granted free to an owner, scoped
  to a single resource.
- **Discount** — A percentage or flat reduction applied to an invoice, scoped
  by owner and/or resource (or global).
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

Free allowances are stacked (per owner, resource, and unit format) before a
single discount is applied to each resource's net total. Discounts are never
stacked; the most specific match (owner+resource > resource > owner > global)
wins. A global No Cost discount reduces the grand total to zero while still
showing the underlying charges.

## Extensibility

Billing sources are registered through the plugin registry with
`register_billing_source`. Each source must provide `get_billable`,
`get_rate_scope`, and `get_quantity` callbacks — a registration missing one
fails fast with `ImproperlyConfigured`. Plugins can add their own billable
models (e.g. a custom metering system) without modifying core ColdFront. See
[Billing Plugins](../plugins/billing.md).

## PDF Export

Any invoice can be exported as a simple PDF with its line items and totals
from the invoice detail page.
