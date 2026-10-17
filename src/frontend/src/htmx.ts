// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import Alpine from "alpinejs";

import { initReslug } from "./buttons/reslug";
import { initDateSelector } from "./dateSelector";
import { initForm } from "./form";
import { initToast } from "./toast";
import { initCharts } from "./charts";

/**
 * Hook into HTMX's event system to reinitialize per-node inits when HTMX swaps
 * elements.
 *
 * Delegation-based inits (table config, object selector, quick add, clipboard)
 * bind a single document-level listener at startup and survive swaps untouched.
 * Only per-node inits — slug "reslug" buttons, django-message toasts, `.vc` date
 * pickers, and `data-reset` buttons inside swapped fragments — are re-run here,
 * scoped to the swapped subtree so listeners are never duplicated.
 */
export function initHtmx(): void {
  document.addEventListener("htmx:afterSettle", (evt) => {
    const el = (evt as CustomEvent).detail?.elt;
    if (!el) return;

    // Re-bind per-node listeners only to the newly swapped fragment.
    initReslug(el);
    initToast(el);
    initDateSelector(el);
    initForm(el);
    initCharts(el);

    // Alpine does not auto-initialize DOM inserted by htmx. Re-initialize any
    // x-data components (e.g. `c-cf.select`) inside the swapped fragment.
    Alpine.initTree(el);
  });
}
