// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

// Table-configuration modal and edit-page column picker behavior. Consolidates
// the legacy `initTableConfig`, `initMoveButtons`, and `form.ts` select-all
// helpers. Uses document-level event delegation so it keeps working across HTMX
// table swaps and applies to both the API modal (`form.userconfigform`) and the
// plain Django POST edit page (`form#form_fields`).
//
//   - "Add"     moves the highlighted options from Available → Selected.
//   - "Remove"  moves the highlighted options from Selected → Available.
//   - "Move Up"/"Move Down" reorder the highlighted Selected options.
//   - Submit    PATCHes the full ordered Selected list to the user-config API
//               (or clears it, for the "Reset" button) and reloads.
//
// The edit page is a plain Django POST (`form#form_fields`). On submit, every
// option in any `select[data-select-all]` is force-selected so the full set is
// POSTed even if only one option was highlighted for reordering.

import { showToast } from "./toast";
import { apiPatch, hasError } from "./util";

const CONFIG_FORM = "form.userconfigform";
const AVAILABLE = "select[name=available_columns]";
const COLUMNS = "select[name=columns]";
const PICKER_BUTTONS =
  "#add_columns, #remove_columns, .move-option-up, .move-option-down";

function selectIn(
  form: HTMLElement,
  selector: string,
): HTMLSelectElement | null {
  return form.querySelector<HTMLSelectElement>(selector);
}

/** Move the highlighted options from one select to the other (moves DOM nodes). */
function moveSelected(
  from: HTMLSelectElement,
  to: HTMLSelectElement,
  keepSelected: boolean,
): void {
  for (const option of Array.from(from.selectedOptions)) {
    to.appendChild(option);
    option.selected = keepSelected;
  }
}

/** Move highlighted options up one position, respecting optgroup boundaries. */
function moveOptionUp(select: HTMLSelectElement): void {
  const options = Array.from(select.options);
  for (let i = 1; i < options.length; i++) {
    const option = options[i];
    if (!option.selected) continue;
    const parent = option.parentElement;
    const previous = select.options[i - 1];
    if (parent && parent === previous.parentElement) {
      parent.insertBefore(option, previous);
    }
  }
}

/** Move highlighted options down one position, respecting optgroup boundaries. */
function moveOptionDown(select: HTMLSelectElement): void {
  const options = Array.from(select.options);
  for (let i = options.length - 2; i >= 0; i--) {
    const option = options[i];
    if (!option.selected) continue;
    const parent = option.parentElement;
    const next = select.options[i + 1];
    if (parent && parent === next.parentElement) {
      parent.insertBefore(next, option);
    }
  }
}

function onClick(event: MouseEvent): void {
  const target = event.target;
  if (!(target instanceof Element)) return;

  const button = target.closest<HTMLElement>(PICKER_BUTTONS);
  if (!button) return;

  const form = button.closest<HTMLFormElement>("form");
  if (!form) return;
  const available = selectIn(form, AVAILABLE);
  const columns = selectIn(form, COLUMNS);
  if (!available || !columns) return;

  event.preventDefault();
  if (button.id === "add_columns") {
    moveSelected(available, columns, true);
  } else if (button.id === "remove_columns") {
    moveSelected(columns, available, false);
  } else if (button.classList.contains("move-option-up")) {
    moveOptionUp(columns);
  } else if (button.classList.contains("move-option-down")) {
    moveOptionDown(columns);
  }
}

/** Wrap a value in a nested object following a dot-separated config path. */
function nest(path: string[], leaf: Dict<unknown>): Dict<unknown> {
  return path.reduceRight<Dict<unknown>>(
    (value, key) => ({ [key]: value }),
    leaf,
  );
}

function reload(): void {
  // Strip any query parameters and reload so the new config takes effect.
  window.location.href = window.location.origin + window.location.pathname;
}

async function onSubmit(event: SubmitEvent): Promise<void> {
  const form = event.target;
  if (!(form instanceof HTMLElement) || !form.matches(CONFIG_FORM)) return;
  event.preventDefault();

  const url = form.getAttribute("data-url");
  if (!url) {
    showToast(
      "error",
      "Error Updating Table Configuration",
      "No API path defined for the table configuration form.",
    );
    return;
  }

  const path = form.getAttribute("data-config-root")?.split(".") ?? [];
  const reset = event.submitter?.getAttribute("value") === "Reset";

  const columns = form.querySelector<HTMLSelectElement>(COLUMNS);
  const leaf: Dict<unknown> = reset
    ? {}
    : {
        columns: columns ? Array.from(columns.options).map((o) => o.value) : [],
      };

  const res = await apiPatch<APIUserConfig>(url, nest(path, leaf));
  if (hasError(res)) {
    showToast(
      "error",
      "Error Updating Table Configuration",
      res.error.slice(0, 15).concat("..."),
    );
    return;
  }
  reload();
}

/**
 * Force-select every option in any `select[data-select-all]` in the submitted form
 * so the full set is POSTed regardless of which options are highlighted.
 *
 * A native multi-select only submits its *selected* options. The column picker's
 * "Selected columns" box means "everything in this box", but clicking an option to
 * reorder it (Move Up/Down highlights a single option) deselects the rest — so
 * without this a save would drop every column except the highlighted one. The API
 * modal reads all options directly (see onSubmit) and doesn't need this; the plain
 * Django POST edit page does.
 */
function selectAllOnSubmit(event: SubmitEvent): void {
  const form = event.target;
  if (!(form instanceof HTMLElement)) return;
  for (const select of form.querySelectorAll<HTMLSelectElement>(
    "select[data-select-all]",
  )) {
    for (const option of Array.from(select.options)) option.selected = true;
  }
}

// Document-level delegation survives htmx swaps, so this only ever runs once;
// re-initializing would stack duplicate click/submit listeners (and duplicate
// PATCH requests on submit).
let delegationBound = false;

export function initTableConfig(): void {
  if (delegationBound) return;
  delegationBound = true;

  document.addEventListener("click", onClick);
  // Capture phase so the full-set selection is applied before onSubmit (which only
  // matters for the API modal, where it's harmless) and before native serialization.
  document.addEventListener("submit", selectAllOnSubmit, true);
  document.addEventListener("submit", (e) => void onSubmit(e as SubmitEvent));
}
