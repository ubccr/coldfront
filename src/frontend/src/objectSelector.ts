// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

function handleSelection(link: HTMLElement): void {
  const selector_results = document.getElementById("selector_results");
  if (selector_results == null) {
    return;
  }
  const target_id = selector_results.getAttribute("data-selector-target");
  if (target_id == null) {
    return;
  }
  const target = document.getElementById(target_id);
  if (target == null) {
    return;
  }

  const label = link.getAttribute("data-label");
  const value = link.getAttribute("data-value");

  // Push the selected object into the `c-cf.select` (the hidden native sink is
  // `target`); the Alpine component adds + selects it.
  target.dispatchEvent(
    new CustomEvent("cf-select:add-option", {
      detail: { value, label },
      bubbles: true,
    }),
  );

  // Close the daisy `<dialog>` modal (htmxModal) natively.
  const modal_element = document.getElementById(
    "htmxModal",
  ) as HTMLDialogElement | null;
  if (modal_element) {
    modal_element.close();
  }
}

let delegationBound = false;

export function initObjectSelector(): void {
  // Event delegation: bind a single click listener on a stable ancestor
  // (`document`), which survives htmx swaps of `#selector_results`. Per-button
  // listeners attached in `htmx:afterSettle` miss clicks that land during
  // htmx's settle window after a search (first-click-dead / second-click-works
  // bug), so delegation removes the race entirely.
  if (delegationBound) {
    return;
  }
  delegationBound = true;

  document.addEventListener("click", (e: MouseEvent) => {
    // Results are `<button data-label data-value>` (element-agnostic query).
    const item = (e.target as Element).closest<HTMLElement>(
      "#selector_results [data-label][data-value]",
    );
    if (item) {
      handleSelection(item);
    }
  });
}
