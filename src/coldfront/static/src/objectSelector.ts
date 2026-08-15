// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { getElementsByQueryGenerator } from './util';

function handleSelection(link: HTMLAnchorElement): void {
  const selector_results = document.getElementById('selector_results');
  if (selector_results == null) {
    return;
  }
  const target_id = selector_results.getAttribute('data-selector-target');
  if (target_id == null) {
    return;
  }
  const target = document.getElementById(target_id);
  if (target == null) {
    return;
  }

  const label = link.getAttribute('data-label');
  const value = link.getAttribute('data-value');

  //@ts-expect-error tomselect added on init
  target.tomselect.addOption({
    id: value,
    display: label,
  });
  //@ts-expect-error tomselect added on init
  target.tomselect.addItem(value);
}

export function initObjectSelector(): void {
  for (const element of getElementsByQueryGenerator('#selector_results a')) {
    const anchor = element as HTMLAnchorElement;
    anchor.addEventListener('click', () => handleSelection(anchor));
  }
}
