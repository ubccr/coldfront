// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

/**
 * @param root Optional root to bind within (defaults to the document). The htmx hook
 *   passes the swapped subtree so reset buttons inserted by a swap get wired.
 */
export function initForm(root: Document | HTMLElement = document): void {
  // Initialize any reset buttons so that when clicked, the page is reloaded without query parameters.
  const resetButton =
    root.querySelector<HTMLButtonElement>("button[data-reset]");
  if (resetButton !== null) {
    resetButton.addEventListener("click", () => {
      // Drop the filter query params, but keep any listed in data-reset-preserve
      // (e.g. return_url) so a reset still returns the user where they came from.
      const url = new URL(window.location.href);
      const preserve = (resetButton.dataset.resetPreserve ?? "").split(",");
      const params = new URLSearchParams();
      for (const rawName of preserve) {
        const name = rawName.trim();
        const value = url.searchParams.get(name);
        if (value) params.set(name, value);
      }
      const qs = params.toString();
      window.location.assign(
        window.location.origin +
          window.location.pathname +
          (qs ? `?${qs}` : ""),
      );
    });
  }
}
