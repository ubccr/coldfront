// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { Collapse, Toast, Tooltip, Popover } from 'bootstrap';
import { getElementsByQueryGenerator } from './util';

export function initTooltips() {
  for (const tooltip of getElementsByQueryGenerator(
    '[data-bs-toggle="tooltip"]'
  )) {
    new Tooltip(tooltip, { container: 'body' });
  }
}

export function initPopovers() {
  for (const popover of getElementsByQueryGenerator(
    '[data-bs-toggle="popover"]'
  )) {
    new Popover(popover);
  }
}

export function initCollapse() {
  for (const collapse of getElementsByQueryGenerator(
    '[data-bs-toggle="collapse"]'
  )) {
    new Collapse(collapse);
  }
}

type ToastLevel = 'danger' | 'warning' | 'success' | 'info';

/**
 * Create a Bootstrap toast notification and append it to the DOM.
 */
export function createToast(
  level: ToastLevel,
  title: string,
  message: string
): Toast {
  let iconName = 'fa-solid fa-circle-exclamation';
  switch (level) {
    case 'warning':
      iconName = 'fa-solid fa-triangle-exclamation';
      break;
    case 'success':
      iconName = 'fa-solid fa-check-circle';
      break;
    case 'info':
      iconName = 'fa-solid fa-circle-info';
      break;
    case 'danger':
      iconName = 'fa-solid fa-circle-exclamation';
      break;
  }

  const container = document.createElement('div');
  container.setAttribute(
    'class',
    'toast-container position-fixed bottom-0 end-0 m-3'
  );

  const main = document.createElement('div');
  main.setAttribute('class', `toast bg-${level}`);
  main.setAttribute('role', 'alert');
  main.setAttribute('aria-live', 'assertive');
  main.setAttribute('aria-atomic', 'true');

  const header = document.createElement('div');
  header.setAttribute('class', `toast-header bg-${level} text-body`);

  const icon = document.createElement('i');
  icon.setAttribute('class', iconName);

  const titleElement = document.createElement('strong');
  titleElement.setAttribute('class', 'me-auto ms-1');
  titleElement.innerText = title;

  const button = document.createElement('button');
  button.setAttribute('type', 'button');
  button.setAttribute('class', 'btn-close');
  button.setAttribute('data-bs-dismiss', 'toast');
  button.setAttribute('aria-label', 'Close');

  const body = document.createElement('div');
  body.setAttribute('class', 'toast-body');

  header.appendChild(icon);
  header.appendChild(titleElement);
  header.appendChild(button);

  body.innerText = message.trim();

  main.appendChild(header);
  main.appendChild(body);
  container.appendChild(main);
  document.body.appendChild(container);

  return new Toast(main);
}

export function initBootstrap(): void {
  for (const func of [initTooltips, initPopovers]) {
    func();
  }
}
