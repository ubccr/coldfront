// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import "htmx.org";
import collapse from "@alpinejs/collapse";
import focus from "@alpinejs/focus";
import Alpine from "alpinejs";
import { initDateSelector } from "./dateSelector";
import { initForm } from "./form";
import { initTableConfig } from "./tableConfig";
import { initToast } from "./toast";
import "./select";
import { initButtons } from "./buttons";
import { initClipboard } from "./clipboard";
import { initDropdown } from "./dropdown";
import { initHtmx } from "./htmx";
import { initObjectSelector } from "./objectSelector";
import { initQuickAdd } from "./quickAdd";
import { initSavedFilterSelect } from "./savedFilters";
import { initQuickSearch } from "./search";
import { initRowSelect } from "./table/rowSelect";

declare global {
  interface Window {
    Alpine: typeof Alpine;
  }
}

window.Alpine = Alpine;
Alpine.plugin(collapse);
Alpine.plugin(focus);
Alpine.start();

function initDocument(): void {
  for (const init of [
    initToast,
    initDateSelector,
    initForm,
    initQuickSearch,
    initHtmx,
    initButtons,
    initTableConfig,
    initClipboard,
    initObjectSelector,
    initQuickAdd,
    initSavedFilterSelect,
    initRowSelect,
    initDropdown,
  ]) {
    init();
  }
}
if (document.readyState !== "loading") {
  initDocument();
} else {
  document.addEventListener("DOMContentLoaded", initDocument);
}
