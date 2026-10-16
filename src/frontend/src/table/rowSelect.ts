// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

// Row selection for object tables (bulk edit/delete). Consolidates the legacy
// `initSelectAll` helper. Uses document-level event delegation so it keeps
// working across HTMX table swaps without re-initialization.
//
//   - The header "toggle all" checkbox (`input.cf-toggle-all`) checks/unchecks
//     every row checkbox (`input[name="pk"]`) in its table.
//   - Unchecking a row clears the header toggle; checking the last remaining
//     row re-checks it.
//   - Shift-clicking a row checkbox selects the contiguous range between it and
//     the previously clicked checkbox, applying the clicked box's new state.

const ROW = 'input[type="checkbox"][name="pk"]';
const TOGGLE = "input.cf-toggle-all";

// Remember the last row checkbox clicked per table body, to anchor shift-ranges.
const lastClicked = new WeakMap<HTMLElement, HTMLInputElement>();

function rowBoxes(scope: Element): HTMLInputElement[] {
  return Array.from(scope.querySelectorAll<HTMLInputElement>(ROW));
}

function isRowBox(el: EventTarget | null): el is HTMLInputElement {
  return (
    el instanceof HTMLInputElement && el.type === "checkbox" && el.name === "pk"
  );
}

function syncHeader(table: HTMLElement): void {
  const toggle = table.querySelector<HTMLInputElement>(TOGGLE);
  if (!toggle) return;
  const boxes = rowBoxes(table);
  toggle.checked = boxes.length > 0 && boxes.every((b) => b.checked);
}

function onMouseDown(event: MouseEvent): void {
  // Prevent the browser from starting a text selection on shift+click so a
  // shift-select range doesn't flash a highlighted region across the row text.
  // The checkbox still toggles on the subsequent click.
  if (event.shiftKey && isRowBox(event.target)) {
    event.preventDefault();
  }
}

function onClick(event: MouseEvent): void {
  const target = event.target;
  if (!isRowBox(target)) return;

  const body = target.closest("tbody");
  if (!body) return;

  if (event.shiftKey) {
    const anchor = lastClicked.get(body);
    if (anchor && anchor !== target) {
      const boxes = rowBoxes(body);
      const start = boxes.indexOf(anchor);
      const end = boxes.indexOf(target);
      if (start !== -1 && end !== -1) {
        const [lo, hi] = start < end ? [start, end] : [end, start];
        // The click has already toggled `target`; apply its state to the range.
        for (let i = lo; i <= hi; i++) {
          if (boxes[i].disabled) continue;
          boxes[i].checked = target.checked;
        }
      }
    }
  }

  lastClicked.set(body, target);

  const table = target.closest("table");
  if (table) syncHeader(table);
}

function onChange(event: Event): void {
  const target = event.target;
  if (target instanceof HTMLInputElement && target.matches(TOGGLE)) {
    const table = target.closest("table");
    if (!table) return;
    for (const box of rowBoxes(table)) {
      if (!box.disabled) box.checked = target.checked;
    }
    return;
  }

  // A row toggled via keyboard (space) won't fire a click; keep the header in
  // sync on any row-checkbox change.
  if (isRowBox(target)) {
    const table = target.closest("table");
    if (table) syncHeader(table);
  }
}

export function initRowSelect(): void {
  document.addEventListener("mousedown", onMouseDown);
  document.addEventListener("click", onClick);
  document.addEventListener("change", onChange);
}
