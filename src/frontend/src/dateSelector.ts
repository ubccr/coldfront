// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { Calendar, time } from "vanilla-calendar-pro";

// vanilla-calendar-pro's 24h time format is `HH:MM`; strip any seconds suffix.
function toTime(value: string): string {
  if (!value) return "";
  const parts = value.split(":");
  return parts.length >= 2 ? `${parts[0]}:${parts[1]}` : "";
}

function initDatePicker(input: HTMLInputElement): void {
  new Calendar(input, {
    inputMode: true,
    selectionDatesMode: "single",
    enableJumpToSelectedDate: true,
    selectedDates: input.value ? [input.value] : [],
    onChangeToInput(self) {
      if (self.context.inputElement && self.context.selectedDates.length > 0) {
        self.context.inputElement.value = self.context.selectedDates[0];
        self.hide();
      }
    },
  }).init();
}

function initDateTimePicker(input: HTMLInputElement): void {
  const [dateStr, timeStr = ""] = input.value.split(" ");
  new Calendar(input, {
    extensions: [time],
    inputMode: true,
    selectionDatesMode: "single",
    selectionTimeMode: 24,
    enableJumpToSelectedDate: true,
    selectedDates: dateStr ? [dateStr] : [],
    selectedTime: toTime(timeStr),
    onChangeToInput(self) {
      if (self.context.inputElement && self.context.selectedDates.length > 0) {
        self.context.inputElement.value = `${self.context.selectedDates[0]} ${self.context.selectedTime || "00:00"}`;
      }
    },
    onChangeTime(self) {
      if (self.context.inputElement && self.context.selectedDates.length > 0) {
        self.context.inputElement.value = `${self.context.selectedDates[0]} ${self.context.selectedTime || "00:00"}`;
      }
    },
  }).init();
}

function initTimePicker(input: HTMLInputElement): void {
  new Calendar(input, {
    extensions: [time],
    inputMode: true,
    selectionDatesMode: false,
    selectionTimeMode: 24,
    layouts: {
      default: "<#ControlTime />",
    },
    selectedTime: toTime(input.value),
    onChangeTime(self) {
      if (self.context.inputElement) {
        self.context.inputElement.value = self.context.selectedTime || "00:00";
      }
    },
  }).init();
}

/**
 * @param root Optional root to bind within (defaults to the document). The htmx hook
 *   passes the swapped subtree so pickers inserted by a swap get initialized.
 */
export function initDateSelector(
  root: Document | HTMLElement = document,
): void {
  root.querySelectorAll<HTMLElement>(".vc").forEach((wrapper) => {
    const input = wrapper.querySelector("input");
    if (!input) return;
    const className = input.className || "";
    if (className.includes("datetime-picker")) {
      initDateTimePicker(input);
    } else if (className.includes("time-picker")) {
      initTimePicker(input);
    } else if (className.includes("date-picker")) {
      initDatePicker(input);
    }
  });
}
