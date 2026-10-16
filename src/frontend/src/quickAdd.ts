// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

function handleQuickAddObject(): void {
  const quick_add = document.getElementById("quick-add-object");
  if (quick_add == null) return;

  const object_id = quick_add.getAttribute("data-object-id");
  if (object_id == null) return;
  const object_repr = quick_add.getAttribute("data-object-repr");
  if (object_repr == null) return;

  const target_id = quick_add.getAttribute("data-target-id");
  if (target_id == null) return;
  const target = document.getElementById(target_id);
  if (target == null) return;

  // Push the created object into the `c-cf.select` (the hidden native sink is
  // `target`); the Alpine component adds + selects it.
  target.dispatchEvent(
    new CustomEvent("cf-select:add-option", {
      detail: { value: object_id, label: object_repr },
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

// #htmxModal-content is itself swapped by htmx, so a listener bound on it would be
// lost/re-bound repeatedly. Delegate a single document-level htmx:afterSwap listener
// that matches the modal — it survives swaps untouched and never accumulates.
let delegationBound = false;

export function initQuickAdd(): void {
  if (delegationBound) return;
  delegationBound = true;

  document.addEventListener("htmx:afterSwap", (evt: Event) => {
    const el = (evt as CustomEvent).detail?.elt;
    if (el?.closest("#htmxModal-content")) {
      handleQuickAddObject();
    }
  });
}
