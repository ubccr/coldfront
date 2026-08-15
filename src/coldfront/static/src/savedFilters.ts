// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

/**
 * Handle saved filter change event.
 *
 * When a saved filter is selected from the dropdown, navigate to the current
 * page URL with the filter_id parameter applied, so the FilterSet can load
 * the saved filter's parameters.
 *
 * @param event "change" event for the saved filter select
 */
function handleSavedFilterChange(event: Event): void {
  const savedFilter = event.currentTarget as HTMLSelectElement;
  let baseUrl = savedFilter.baseURI.split('?')[0];
  const preFilter = '?';

  const selectedOptions = Array.from(savedFilter.options)
    .filter((option) => option.selected)
    .map((option) => `filter_id=${option.value}`)
    .join('&');

  baseUrl += `${preFilter}${selectedOptions}`;
  document.location.href = baseUrl;
}

export function initSavedFilterSelect(): void {
  const divResults = document.getElementById('results');
  if (divResults) {
    const savedFilterSelect = document.getElementById('id_filter_id');
    if (savedFilterSelect) {
      savedFilterSelect.addEventListener('change', handleSavedFilterChange);
    }
  }
}
