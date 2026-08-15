// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { getElementsByQueryGenerator } from '../util';

/**
 * Move selected options of a select element up in order, respecting optgroup boundaries.
 *
 * Adapted from:
 * @see https://github.com/netbox-community/netbox/blob/main/netbox/project-static/src/buttons/moveOptions.ts
 * @see https://www.tomred.net/css-html-js/reorder-option-elements-of-an-html-select.html
 * @param element Select Element
 */
function moveOptionUp(element: HTMLSelectElement): void {
  const options = Array.from(element.options);
  for (let i = 1; i < options.length; i++) {
    const option = options[i];
    if (option.selected) {
      const parent = option.parentElement as HTMLElement;
      const previousOption = element.options[i - 1];
      const previousParent = previousOption.parentElement as HTMLElement;

      // Only move if previous option is in the same parent (optgroup or select)
      if (parent === previousParent) {
        parent.removeChild(option);
        parent.insertBefore(option, previousOption);
      }
    }
  }
}

/**
 * Move selected options of a select element down in order, respecting optgroup boundaries.
 *
 * Adapted from:
 * @see https://github.com/netbox-community/netbox/blob/main/netbox/project-static/src/buttons/moveOptions.ts
 * @see https://www.tomred.net/css-html-js/reorder-option-elements-of-an-html-select.html
 * @param element Select Element
 */
function moveOptionDown(element: HTMLSelectElement): void {
  const options = Array.from(element.options);
  for (let i = options.length - 2; i >= 0; i--) {
    const option = options[i];
    if (option.selected) {
      const parent = option.parentElement as HTMLElement;
      const nextOption = element.options[i + 1];
      const nextParent = nextOption.parentElement as HTMLElement;

      // Only move if next option is in the same parent (optgroup or select)
      if (parent === nextParent) {
        const optionClone = parent.removeChild(option);
        const nextClone = parent.replaceChild(optionClone, nextOption);
        parent.insertBefore(nextClone, optionClone);
      }
    }
  }
}

/**
 * Initialize select/move buttons.
 */
export function initMoveButtons(): void {
  // Move selected option(s) up in current list
  for (const element of getElementsByQueryGenerator('.move-option-up')) {
    const button = element as HTMLButtonElement;
    const target = button.getAttribute('data-target');
    const target_select = document.getElementById(
      `id_${target}`
    ) as HTMLSelectElement;
    if (target_select !== null) {
      button.addEventListener('click', () => moveOptionUp(target_select));
    }
  }

  // Move selected option(s) down in current list
  for (const element of getElementsByQueryGenerator('.move-option-down')) {
    const button = element as HTMLButtonElement;
    const target = button.getAttribute('data-target');
    const target_select = document.getElementById(
      `id_${target}`
    ) as HTMLSelectElement;
    if (target_select !== null) {
      button.addEventListener('click', () => moveOptionDown(target_select));
    }
  }
}
