// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { createToast } from './bs';
import { getElementsByQueryGenerator, apiPatch, hasError } from './util';

/**
 * Add columns to the table config select element.
 */
function addColumns(event: Event): void {
  for (const optionElement of getElementsByQueryGenerator(
    '#id_available_columns > option'
  )) {
    const selectedOption = optionElement as HTMLOptionElement;
    if (selectedOption.selected) {
      const clone = selectedOption.cloneNode(true) as HTMLOptionElement;
      clone.selected = true;
      for (const selectedElement of getElementsByQueryGenerator(
        '#id_columns'
      )) {
        const selected = selectedElement as HTMLSelectElement;
        selected.appendChild(clone);
      }
      selectedOption.remove();
    }
  }
  event.preventDefault();
}

/**
 * Remove columns from the table config select element.
 */
function removeColumns(event: Event): void {
  for (const optionElement of getElementsByQueryGenerator(
    '#id_columns > option'
  )) {
    const selectedOption = optionElement as HTMLOptionElement;
    if (selectedOption.selected) {
      const clone = selectedOption.cloneNode(true) as HTMLOptionElement;
      clone.selected = false;
      for (const availableElement of getElementsByQueryGenerator(
        '#id_available_columns'
      )) {
        const available = availableElement as HTMLSelectElement;
        available.appendChild(clone);
      }
      selectedOption.remove();
    }
  }
  event.preventDefault();
}

/**
 * Submit form configuration to the ColdFront API.
 */
async function submitFormConfig(
  url: string,
  formConfig: Dict<unknown>
): Promise<APIResponse<APIUserConfig>> {
  return await apiPatch<APIUserConfig>(url, formConfig);
}

/**
 * Handle table config form submission. Sends the selected columns to the ColdFront API to update
 * the user's table configuration preferences.
 */
function handleSubmit(event: Event): void {
  event.preventDefault();

  const element = event.currentTarget as HTMLFormElement;

  // Get the API URL for submitting the form
  const url = element.getAttribute('data-url');
  if (url == null) {
    const toast = createToast(
      'danger',
      'Error Updating Table Configuration',
      'No API path defined for configuration form.'
    );
    toast.show();
    return;
  }

  // Determine if the form action is to reset the table config.
  const reset = document.activeElement?.getAttribute('value') === 'Reset';

  // Create an array from the dot-separated config path. E.g. tables.DevicePowerOutletTable becomes
  // ['tables', 'DevicePowerOutletTable']
  const path = element.getAttribute('data-config-root')?.split('.') ?? [];

  if (reset) {
    // If we're resetting the table config, create an empty object for this table. E.g.
    // tables.PlatformTable becomes {tables: PlatformTable: {}}
    const data = path.reduceRight<Dict<Dict>>(
      (value, key) => ({ [key]: value }),
      {}
    );

    // Submit the reset for configuration to the API.
    submitFormConfig(url, data).then((res) => {
      if (hasError(res)) {
        const toast = createToast(
          'danger',
          'Error Resetting Table Configuration',
          res.error.slice(0, 15).concat('...')
        );
        toast.show();
      } else {
        // Strip any URL query parameters & reload the page
        window.location.href =
          window.location.origin + window.location.pathname;
      }
    });
    return;
  }

  // Get all options from the columns select (all columns in the list, regardless of selection state).
  const columnsSelect = element.querySelector(
    'select[name=columns]'
  ) as HTMLSelectElement;
  const columnValues = Array.from(columnsSelect.options).map(
    (opt) => opt.value
  );

  // Create the form data mapping the select element's name to all its option values.
  const formData: Dict<string[]> = { columns: columnValues };

  // Create an object mapping the configuration path to the select element names, which contain the
  // selection options. E.g. {tables: {DevicePowerOutletTable: {columns: ['label', 'type']}}}
  const data = path.reduceRight<Dict<unknown>>(
    (value, key) => ({ [key]: value }),
    formData
  );

  // Submit the resulting object to the API to update the user's preferences for this table.
  submitFormConfig(url, data).then((res) => {
    if (hasError(res)) {
      const toast = createToast(
        'danger',
        'Error Updating Table Configuration',
        res.error.slice(0, 15).concat('...')
      );
      toast.show();
    } else {
      // Strip any URL query parameters & reload the page
      window.location.href = window.location.origin + window.location.pathname;
    }
  });
}

/**
 * Initialize table configuration elements.
 */
export function initTableConfig(): void {
  for (const element of getElementsByQueryGenerator('#add_columns')) {
    element.addEventListener('click', addColumns);
  }
  for (const element of getElementsByQueryGenerator('#remove_columns')) {
    element.addEventListener('click', removeColumns);
  }
  const forms = [...getElementsByQueryGenerator('form.userconfigform')];
  for (const element of forms) {
    element.addEventListener('submit', handleSubmit);
  }
}
