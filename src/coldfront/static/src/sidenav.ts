// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { getElementsByQueryGenerator } from './util';

/**
 * Expand the top level side menu group for the current page
 */
export function initNavLinks(): void {
  // Mobile hamburger button to show/hide side nav
  const sidebar = document.querySelector('aside.sidebar');
  if (sidebar) {
    document.addEventListener('click', function (e) {
      const toggle = document.getElementById('sidebarToggle');
      const target = e.target as Node;
      if (toggle && (e.target === toggle || toggle.contains(target))) {
        e.stopPropagation();
        sidebar.classList.toggle('show');
      }
      // Close sidebar when clicking outside on mobile
      if (
        sidebar.classList.contains('show') &&
        toggle &&
        !sidebar.contains(target) &&
        e.target !== toggle &&
        !toggle.contains(target)
      ) {
        sidebar.classList.remove('show');
      }
    });
  }

  for (const element of getElementsByQueryGenerator('nav.nav .collapse')) {
    const divMenu = element as HTMLDivElement;
    for (const link of divMenu.querySelectorAll<HTMLAnchorElement>('a')) {
      const href = new RegExp(link.href, 'gi');
      if (window.location.href.match(href)) {
        divMenu.classList.add('show');
        return;
      }
    }
  }
}
