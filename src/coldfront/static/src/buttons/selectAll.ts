// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { getElementsByQueryGenerator } from '../util';

/**
 * If any PK checkbox is checked, uncheck the select all table checkbox and the select all
 * confirmation checkbox.
 *
 * @param event Change Event
 */
function handlePkCheck(event: Event): void {
  const target = event.currentTarget as HTMLInputElement;
  if (!target.checked) {
    for (const element of getElementsByQueryGenerator(
      'input[type="checkbox"].toggle'
    )) {
      const input = element as HTMLInputElement;
      input.checked = false;
    }
  }
}

function handleSelectAllToggle(event: Event): void {
  const tableSelectAll = event.currentTarget as HTMLInputElement;
  for (const element of getElementsByQueryGenerator(
    'tr:not(.d-none) input[type="checkbox"][name="pk"]'
  )) {
    const input = element as HTMLInputElement;
    if (tableSelectAll.checked) {
      // Check all PK checkboxes if the select all checkbox is checked.
      input.checked = true;
    } else {
      // Uncheck all PK checkboxes if the select all checkbox is unchecked.
      input.checked = false;
    }
  }
}

export function initSelectAll(): void {
  for (const element of getElementsByQueryGenerator(
    'table tr th > input[type="checkbox"].toggle'
  )) {
    element.addEventListener('change', handleSelectAllToggle);
  }
  for (const element of getElementsByQueryGenerator(
    'input[type="checkbox"][name="pk"]'
  )) {
    element.addEventListener('change', handlePkCheck);
  }
}
