# Billing & Invoicing

ColdFront's billing app produces invoices for the resources a research group
uses. This guide walks an HPC administrator through setting up billing and
running the invoice workflow.

---

## How Billing Works (Background)

Billing is **allocation-based**. For each billing period, ColdFront looks at
every billable allocation a project holds, prices it against a **rate**, and
collects the result into an **invoice**:

- **Storage** — A `StorageQuota` is billed per terabyte (TB) of capacity at
  the storage resource's rate.
- **Compute** — A `SlurmAccount` is billed per service unit (SU) of compute
  time at the cluster's rate.

Two levers reduce the final amount:

- **Free allowances** — A pool of free units granted to an owner, scoped to a
  resource. Allowances are stacked before any discount is applied.
- **Discounts** — A percentage or flat reduction on the net total, scoped by
  owner and/or resource.

Every invoice is owned by a **responsible user** (the `owner`). Generation
considers all of the owner's billable sources, optionally restricted to
specific billing source types (e.g. storage or compute); if no source types
are selected, every billable source is billed.

---

## Setting Up Billing

Billing needs three things before an invoice can be generated: rates, free
allowances, and discounts.

### Rates

A **Rate** is a per-unit price scoped to a single resource. Create one for
each resource you want to bill:

| Field | Meaning |
|---|---|
| **Name** | Required, globally unique label for the rate |
| **Scope** | The resource the rate applies to (a `StorageResource`, `SlurmCluster`, or `SlurmQOS`) |
| **Unit** | Native units per billed unit — e.g. `1000000000000` (1.0 TB) for per-TB pricing |
| **Unit format** | The billing dimension: `bytes`, `service_units`, `core_hours`, or `per_item` |
| **Amount** | Price per billing unit (required) |
| **Charge basis** | `one_time`, `monthly`, or `yearly` cadence |
| **Effective dates** | Optional window during which the rate is active |

There is exactly **one rate per scope** — creating a second rate for the same
resource is rejected. To change a price, edit the existing rate. The unit
must be greater than zero and the amount is required.

Rates are created under **Billing → Rates**.

### Free Allowances

A **FreeAllowance** grants a pool of free units to an owner, scoped to a
single resource (scope is required — there are no global allowances):

- **Name** — Required, globally unique label for the allowance.
- **Owner** — The user granted the free units (required).
- **Scope** — The resource the allowance applies to (required).
- **Unit format** and **quantity total** — The dimension and total free units.

Allowances are stacked with other allowances for the same owner, resource, and
unit format, and are consumed once when an invoice is finalized; the `used`
field tracks how much of the pool has been drawn down over time.

### Discounts

A **Discount** reduces the net total after allowances. It can be scoped by
owner, by resource, both, or neither:

- **Name** — Required, globally unique label for the discount.
- **Owner** — The user receiving the discount. Leave empty for a
  resource-only or global discount.
- **Scope** — The resource the discount applies to. Leave empty for an
  owner-only or global discount.
- **Type** — `percentage` (0-100), `flat` (an amount), or `no_cost` (zeroes
  the invoice while still showing the underlying charges).
- **Value** — The percentage or flat amount.

For a given charge the **most specific** matching discount wins — owner +
resource, then resource-only, then owner-only, then global — and discounts are
never stacked. A global **No Cost** discount (`owner` and scope empty) reduces
the grand total to zero while keeping the line items visible.

---

## Creating an Invoice

Invoices are created from **Billing → Invoices → Add**. The create form asks
for only what generation needs:

- **Slug**, **owner**, and an optional **description**
- **Source types** — restrict to specific billing source types (empty = all
  of the owner's billable sources)
- **Period** — start date, end date, and due date

On creation, ColdFront **automatically generates** the invoice: it prices
every billable source in the period, applies free allowances and discounts,
and builds the line items and totals (subtotal, allowance total, discount
total, grand total) in the same step. There is no separate "save then
generate" step for a new invoice.

---

## Running the Invoice Workflow

An invoice moves through a status workflow controlled by object permissions:

```
Draft ──generate──→ Draft        (regenerate line items)
Draft ──invoice──→ Invoiced ──pay──→ Paid
Draft ──void──→ Void              (also from Invoiced)
```

| Action | Permission | What it does |
|---|---|---|
| **Generate** | `generate_invoice` | (Re)builds line items and totals for a draft invoice |
| **Invoice** | `finalize_invoice` | Finalizes a draft: drops invalid lines, consumes allowance pools, moves to `invoiced` |
| **Pay** | `pay_invoice` | Records payment (date, amount, method) and moves to `paid` |
| **Void** | `void_invoice` | Voids a draft or invoiced invoice (no refund) |

Each action opens a small form with an optional **comments** field. Any
comment is recorded on the invoice's comment thread. The **Generate** and
**Invoice** transitions are available on draft invoices; **Pay** is available
once invoiced; **Void** is available on drafts and invoiced invoices.

### Generating

Click **Generate** to rebuild the invoice's line items and totals. Charges are
priced at the scoped rate, free allowances are stacked (per owner, resource,
and unit format), and a single discount is applied to each resource's net
total (owner+resource > resource > owner > global precedence). Sources that
were already billed in an overlapping, non-voided invoice period are skipped.

### Invoicing (Finalize)

Click **Invoice** to finalize the draft. Invalid lines are dropped, allowance
pools are consumed once, and the invoice moves to `invoiced`. The owner
receives a notification.

### Paying

Click **Pay** on an invoiced invoice and record the payment date, amount, and
method. The invoice moves to `paid`.

### Voiding

Click **Void** to cancel a draft or invoiced invoice. A voided invoice is not
billed and does not consume allowance pools.

---

## Exporting a PDF

Every invoice has an **Export PDF** button on its detail page. It downloads a
PDF with the invoice's line items (description, type, quantity, unit, unit
price, amount), totals, and (when paid) payment details. The PDF is rendered 
from the Django template `src/coldfront/templates/billing/pdf_invoice.html`.

### Customizing the invoice PDF

Sites override `billing/pdf_invoice.html` with their own template dir (see
`SITE_TEMPLATES` / `TEMPLATES["DIRS"]`) exactly like any other page. The
context is curated and includes:

- `invoice` — the `Invoice` instance (use `{{ invoice.slug }}`, `{{ invoice.owner }}`,
  `{{ invoice.get_status_display }}`, dates, and the Money totals).
- `line_items` — the invoice's line items, pre-sorted by line type then id.
- `status_paid` — the paid status value, for `{% if invoice.status == status_paid %}`.

ColdFront currently uses [fpdf2](https://py-pdf.github.io/fpdf2/index.html) for
PDF rendering which handles a limited HTML subset, keep overrides to plain
headings, paragraphs, and `<table>`/`<tr>`/`<td>`/`<th>` markup — no CSS. For
more information see [the fpdf2 HTML rendering docs](https://py-pdf.github.io/fpdf2/HTML.html).

---

## Troubleshooting

### Invalid lines ("Needs fixing")

If a billing source could not be priced at generation time, its line item is
flagged `is_valid=False` with a description such as *"Needs fixing: quantity
not set"*. These lines are shown on the invoice and are **dropped** when the
invoice is finalized. Fix the underlying data (e.g. set the source's quantity)
and generate again. An invoice with no valid charge lines cannot be finalized.

### Sources skipped

A source is skipped when:

- **No rate** exists for its scope — the admin has chosen not to bill it.
- **Quantity is zero** — there is nothing to bill.
- **Currency mismatch** — the rate is not in the invoice's default currency
  (v1 is single-currency).
- **Period overlap** — the source was already billed in an overlapping,
  non-voided invoice period.

### Configuration errors

A misconfigured billing source (e.g. a registered source whose rate scope
does not match its declared scope) raises a configuration error rather than
producing a silent wrong bill. Correct the registration and generate again.

---

## Extending Billing

The built-in sources bill `StorageQuota` per TB and `SlurmAccount` per SU.
HPC centers with different metering can register their own billing sources
through plugins. See [Billing Plugins](../plugins/billing.md).
