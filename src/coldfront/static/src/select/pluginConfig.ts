// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

interface PluginConfig {
  [plugin: string]: object;
}

export function getPlugins(element: HTMLSelectElement): object {
  const plugins: PluginConfig = {};

  // Enable "clear all" button for non-required fields
  if (!element.required) {
    plugins.clear_button = {
      html: (data: Record<string, string>) =>
        `<i class="fa-solid fa-circle-xmark ${data.className}" title="${data.title}"></i>`,
    };
  }

  // Enable individual "remove" buttons for items on multi-select fields
  if (element.hasAttribute('multiple')) {
    plugins.remove_button = {
      title: 'Remove',
    };
  }

  // Enable drag-and-drop reordering of items on multi-select fields
  if (element.hasAttribute('multiple')) {
    plugins.drag_drop = {};
  }

  if (element.hasAttribute('ts-checkbox-field')) {
    plugins.checkbox_options = {};
  }

  if (element.hasAttribute('ts-extra-columns-field')) {
    const title = (element.getAttribute('ts-title-field') as string) || '';
    const headers = title.split(',');
    plugins.dropdown_header = {
      title: headers.shift(),
      html: function (data: Record<string, string>) {
        let html = `<div class="${data.headerClass}">`;
        html = `${html}<div class="row ${data.titleRowClass}">`;
        html = `${html}<div class="col"><span class="${data.labelClass}">${data.title}</span></div>`;

        for (const col of headers) {
          html = `${html}<div class="col"><span class="${data.labelClass}">${col}</span></div>`;
        }
        html = `${html}</div>`;
        html = `${html}</div>`;
        return html;
      },
    };
  }

  return {
    plugins: plugins,
  };
}
