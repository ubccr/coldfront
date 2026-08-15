// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import './scss/coldfront.scss';
import 'bootstrap';
import 'htmx.org';
import { initDateSelector } from './dateSelector';
import { initForm } from './form';
import { initSelects } from './select';
import { initQuickSearch } from './search';
import { initHtmx } from './htmx';
import { initTableConfig } from './tableConfig';
import { initButtons } from './buttons';
import { initBootstrap } from './bs';
import { initNavLinks } from './sidenav';
import { initMessages } from './messages';
import { initTheme } from './theme';
import { initClipboard } from './clipboard';
import { initObjectSelector } from './objectSelector';
import { initQuickAdd } from './quickAdd';
import { initSavedFilterSelect } from './savedFilters';

function initDocument(): void {
  for (const init of [
    initBootstrap,
    initTheme,
    initMessages,
    initDateSelector,
    initForm,
    initSelects,
    initQuickSearch,
    initHtmx,
    initNavLinks,
    initButtons,
    initTableConfig,
    initClipboard,
    initObjectSelector,
    initQuickAdd,
    initSavedFilterSelect,
  ]) {
    init();
  }
}
if (document.readyState !== 'loading') {
  initDocument();
} else {
  document.addEventListener('DOMContentLoaded', initDocument);
}
