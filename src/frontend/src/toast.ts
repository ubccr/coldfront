// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

// daisyUI toast notifications. Consolidates the legacy toast helpers
// (`createToast` and `initMessages`) into a single daisyUI-based module.
//
//   - showToast() appends a programmatic daisyUI alert into the `#django-messages`
//     container (a `c-lb.toast`) and auto-dismisses it after a delay.
//   - initToast() wires the same timed dismiss + close button onto the
//     server-rendered django message toasts so they behave identically.

const CONTAINER = "#django-messages";
const DEFAULT_DELAY = 5000;

export type ToastLevel = "error" | "warning" | "success" | "info";

const LEVEL_CLASS: Record<ToastLevel, string> = {
  error: "alert-error",
  warning: "alert-warning",
  success: "alert-success",
  info: "alert-info",
};

function escapeHtml(value: string): string {
  const map: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };
  return value.replace(/[&<>"']/g, (c) => map[c] ?? c);
}

/** Remove a toast element and clear its pending dismiss timeout. */
function dismiss(el: HTMLElement, timer: number | null): void {
  if (timer !== null) window.clearTimeout(timer);
  el.remove();
}

/** Attach an auto-dismiss timeout and a close button to a toast element. */
function wireToast(el: HTMLElement, delay: number): void {
  const timer = window.setTimeout(() => dismiss(el, timer), delay);
  const close = el.querySelector<HTMLButtonElement>("button.cf-toast-close");
  close?.addEventListener("click", () => dismiss(el, timer));
}

/**
 * Show a programmatic daisyUI toast and auto-dismiss it after a delay.
 */
export function showToast(
  level: ToastLevel,
  title: string,
  message: string,
): void {
  const host = document.querySelector<HTMLElement>(CONTAINER);
  if (!host) return;

  const el = document.createElement("div");
  el.className = `alert ${LEVEL_CLASS[level]} shadow-sm`;
  el.setAttribute("role", "alert");
  el.innerHTML = `
    <div class="grid gap-1">
      <div class="font-semibold">${escapeHtml(title)}</div>
      <div class="text-sm">${escapeHtml(message)}</div>
    </div>
    <button class="cf-toast-close btn btn-sm btn-ghost" aria-label="Close">✕</button>
  `;
  host.appendChild(el);
  wireToast(el, DEFAULT_DELAY);
}

/**
 * Initialize the server-rendered django message toasts: auto-dismiss after a
 * delay (defaulting to the template's `data-dismiss`, or 5s) with a close button.
 *
 * @param root Optional root to bind within. Defaults to the document (which scopes to
 *   the `#django-messages` container). The htmx hook passes the swapped OOB toast
 *   fragment so newly inserted toasts get wired — re-running over the whole document
 *   would wrongly wire non-toast `.alert` elements elsewhere on the page.
 */
export function initToast(root: Document | HTMLElement = document): void {
  const host =
    root instanceof Document
      ? root.querySelector<HTMLElement>(CONTAINER)
      : root;
  if (!host) return;
  const alerts =
    host instanceof Element && host.matches(".alert")
      ? [host]
      : Array.from(host.querySelectorAll<HTMLElement>(".alert"));
  for (const el of alerts) {
    const delay = Number(el.dataset.dismiss ?? DEFAULT_DELAY);
    wireToast(el, delay);
  }
}
