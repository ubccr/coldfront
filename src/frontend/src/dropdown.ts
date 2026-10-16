// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

/**
 * Auto-flip daisyUI dropdowns marked `data-cf-flip` to open upward when they
 * would overflow their clipping boundary (e.g. the table's `overflow-x-auto`
 * wrapper on the last row). Mirrors Bootstrap/Popper's flip behavior that the
 * actions-column dropdown otherwise lacks — daisyUI dropdowns are pure CSS and
 * open in the configured direction unconditionally.
 *
 * Document-level delegation survives htmx swaps, so this runs once at startup.
 */

// Extra headroom so the menu isn't clipped mid-open (daisyUI opens at scale .95).
const FLIP_BUFFER = 8;

let delegationBound = false;

/**
 * The nearest overflow ancestor clips absolutely-positioned menus. Fall back to
 * the viewport when no ancestor clips.
 */
function getClipBoundary(el: HTMLElement): DOMRect {
  let cur = el.parentElement;
  while (cur) {
    const style = getComputedStyle(cur);
    if (style.overflowX !== "visible" || style.overflowY !== "visible") {
      return cur.getBoundingClientRect();
    }
    cur = cur.parentElement;
  }
  return document.documentElement.getBoundingClientRect();
}

/**
 * Measure the down-positioned menu and flip to `dropdown-top` if it would
 * overflow the bottom of its clipping boundary. Reads and writes in the same
 * task before paint, so the menu never renders in the wrong direction.
 */
function flip(dropdown: HTMLElement): void {
  const menu = dropdown.querySelector<HTMLElement>(".dropdown-content");
  const trigger = dropdown.querySelector<HTMLElement>(
    '[tabindex][role="button"]',
  );
  if (!menu || !trigger) return;

  // Reset to the down placement, then measure — no paint between these.
  dropdown.classList.remove("dropdown-top");
  const menuRect = menu.getBoundingClientRect();
  const triggerRect = trigger.getBoundingClientRect();

  const boundary = getClipBoundary(dropdown);
  const bottomLimit =
    Math.min(boundary.bottom, window.innerHeight) - FLIP_BUFFER;
  const topLimit = Math.max(boundary.top, 0) + FLIP_BUFFER;

  let useTop = false;
  if (menuRect.bottom > bottomLimit) {
    useTop = true;
    // If opening up would overflow the top too, keep it down.
    if (triggerRect.top - menuRect.height < topLimit) {
      useTop = false;
    }
  }
  dropdown.classList.toggle("dropdown-top", useTop);
}

/**
 * Initialize the delegated flip handler for `data-cf-flip` dropdowns (the table
 * actions menu). Idempotent — document-level delegation survives htmx swaps.
 */
export function initDropdown(): void {
  if (delegationBound) return;
  delegationBound = true;

  document.addEventListener("focusin", (e: FocusEvent) => {
    const trigger = (e.target as Element).closest<HTMLElement>(
      ".dropdown[data-cf-flip] > [tabindex]",
    );
    if (!trigger) return;
    const dropdown = trigger.closest<HTMLElement>(".dropdown");
    if (dropdown) flip(dropdown);
  });
}
