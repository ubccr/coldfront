// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { initBootstrap } from './bs';
import { initButtons } from './buttons';
import { initClipboard } from './clipboard';
import { initQuickAdd } from './quickAdd';
import { initSelects } from './select';
import { initObjectSelector } from './objectSelector';
import { initTableConfig } from './tableConfig';

function initDepedencies(): void {
  initBootstrap();
  initSelects();
  initButtons();
  initObjectSelector();
  initClipboard();
  initQuickAdd();
  initTableConfig();
}

/**
 * Hook into HTMX's event system to reinitialize specific native event listeners when HTMX swaps
 * elements.
 */
export function initHtmx(): void {
  document.addEventListener('htmx:afterSettle', initDepedencies);
}
