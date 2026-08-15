// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

export function initTheme(): void {
  // Toggle dark mode
  const toggle = document.getElementById('theme-toggle');

  if (toggle !== null) {
    toggle.addEventListener('click', function () {
      const html = document.documentElement;
      const isDarkMode = html.getAttribute('data-bs-theme') === 'dark';

      if (isDarkMode) {
        html.setAttribute('data-bs-theme', 'light');
        localStorage.setItem('theme', 'light');
        toggle.title = 'Toggle dark mode';
      } else {
        html.setAttribute('data-bs-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        toggle.title = 'Toggle light mode';
      }
    });
  }
}
