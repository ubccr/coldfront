// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import flatpickr from 'flatpickr';

export function initDateSelector(): void {
  flatpickr('.datepicker', { allowInput: true });
  flatpickr('.date-picker', { allowInput: true });
  flatpickr('.datetime-picker', {
    allowInput: true,
    enableSeconds: true,
    enableTime: true,
    time_24hr: true,
  });
  flatpickr('.time-picker', {
    allowInput: true,
    enableSeconds: true,
    enableTime: true,
    noCalendar: true,
    time_24hr: true,
  });
}
