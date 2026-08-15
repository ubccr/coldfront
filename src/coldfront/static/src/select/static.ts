// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import TomSelect from 'tom-select';
import type { TomOption } from 'tom-select/dist/esm/types/core.js';
import { escape_html } from 'tom-select/dist/esm/utils.js';
import { getPlugins } from './pluginConfig';
import { getElementsByQueryGenerator } from '../util';

// Initialize selection fields
export function initStaticSelects(): void {
  for (const element of getElementsByQueryGenerator(
    'select:not(.tomselected):not(.no-ts):not([size]):not(.api-select):not(.color-select):not(.flatpickr-monthDropdown-months)'
  )) {
    const select = element as HTMLSelectElement;
    new TomSelect(select, {
      ...getPlugins(select),
      maxOptions: undefined,
    });
  }
}

// Initialize color selection fields
export function initColorSelects(): void {
  function renderColor(item: TomOption, escape: typeof escape_html) {
    return `<div><span class="dropdown-item-indicator color-label" style="background-color: #${escape(
      item.value
    )}"></span>&nbsp;&nbsp; ${escape(item.text)}</div>`;
  }

  for (const element of getElementsByQueryGenerator(
    'select.color-select:not(.tomselected)'
  )) {
    const select = element as HTMLSelectElement;
    new TomSelect(select, {
      maxOptions: undefined,
      render: {
        option: renderColor,
        item: renderColor,
      },
    });
  }
}
