import { Collapse, Tooltip, Popover } from 'bootstrap';
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

export function initFilterAccordionIcon() {
  // The list pages (project, archived-project, allocation, resource)
  // render the filter accordion's plus/minus icon server-side, once.
  // Toggle it from the panel's collapse events so it stays in sync with
  // the panel's state however the panel is toggled.
  const collapse = document.getElementById('collapseOne');
  const icon = document.getElementById('plus_minus');
  if (collapse === null || icon === null) {
    return;
  }
  collapse.addEventListener('show.bs.collapse', () => {
    icon.classList.replace('fa-plus', 'fa-minus');
  });
  collapse.addEventListener('hide.bs.collapse', () => {
    icon.classList.replace('fa-minus', 'fa-plus');
  });
}

export function initBootstrap(): void {
  for (const func of [initTooltips, initPopovers, initFilterAccordionIcon]) {
    func();
  }
}
