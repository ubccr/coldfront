// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { getElementsByQueryGenerator } from './util';

function handleFormSubmit(): void {
  // Automatically select all options in any <select> with the "select-all" class. This is useful for
  // multi-select fields that are used to add/remove choices (e.g. table config column picker).
  for (const element of getElementsByQueryGenerator(
    'select.select-all option'
  )) {
    (element as HTMLOptionElement).selected = true;
  }
}

export function initForm(): void {
  // Initialize any reset buttons so that when clicked, the page is reloaded without query parameters.
  const resetButton =
    document.querySelector<HTMLButtonElement>('button[data-reset]');
  if (resetButton !== null) {
    resetButton.addEventListener('click', () => {
      // Drop the filter query params, but keep any listed in data-reset-preserve
      // (e.g. return_url) so a reset still returns the user where they came from.
      const url = new URL(window.location.href);
      const preserve = (resetButton.dataset.resetPreserve ?? '').split(',');
      const params = new URLSearchParams();
      for (const rawName of preserve) {
        const name = rawName.trim();
        const value = url.searchParams.get(name);
        if (value) params.set(name, value);
      }
      const qs = params.toString();
      window.location.assign(
        window.location.origin + window.location.pathname + (qs ? `?${qs}` : '')
      );
    });
  }

  // Attach event listeners to each form's submit buttons to select all options in any <select>
  // with the "select-all" CSS class. This ensures all values are submitted regardless of selection state.
  for (const form of getElementsByQueryGenerator('form')) {
    const submitters = form.querySelectorAll<HTMLButtonElement>(
      'button[type=submit]'
    );
    for (const submitter of submitters) {
      submitter.addEventListener('click', () => handleFormSubmit());
    }
  }
}
