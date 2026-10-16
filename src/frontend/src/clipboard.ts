// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

/**
 * Copy-to-clipboard for `button.copy-content` elements (e.g. generated API
 * tokens). A single delegated document click handler replaces the clipboard.js
 * library, so it survives htmx swaps with no per-node re-initialization.
 *
 * The source is resolved from `data-clipboard-target` (a CSS selector) and its
 * value copied via the async Clipboard API when available (secure context),
 * falling back to select + `document.execCommand('copy')` otherwise.
 */

let delegationBound = false;

/** Resolve the element whose value should be copied, from `data-clipboard-target`. */
function resolveSource(button: HTMLElement): HTMLElement | null {
  const selector = button.dataset.clipboardTarget;
  if (!selector) return null;
  return document.querySelector<HTMLElement>(selector);
}

/** Read the copyable value off a resolved source element. */
function sourceValue(source: HTMLElement): string {
  if (
    source instanceof HTMLInputElement ||
    source instanceof HTMLTextAreaElement ||
    source instanceof HTMLSelectElement
  ) {
    return source.value;
  }
  return source.textContent ?? "";
}

/** Copy `value` using a temporary textarea + `execCommand('copy')`. */
function legacyCopy(value: string): void {
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

/** Copy the value of `source`, preferring the async Clipboard API. */
async function copyFrom(button: HTMLElement): Promise<void> {
  const source = resolveSource(button);
  const value = source ? sourceValue(source) : (button.dataset.copy ?? "");
  if (!value) return;

  // Preferred: async Clipboard API (requires a secure context).
  try {
    if (typeof navigator.clipboard?.writeText === "function") {
      await navigator.clipboard.writeText(value);
      return;
    }
  } catch {
    // Permission denied or transient failure — fall through to execCommand.
  }

  // Fallback: works in non-secure contexts. Select the visible input directly
  // (a readonly token field), otherwise copy via a hidden temporary textarea.
  if (
    source instanceof HTMLInputElement ||
    source instanceof HTMLTextAreaElement
  ) {
    source.select();
    document.execCommand("copy");
  } else {
    legacyCopy(value);
  }
}

/**
 * Initialize the delegated copy handler. Idempotent — document-level
 * delegation survives htmx swaps, so this only ever runs once.
 */
export function initClipboard(): void {
  if (delegationBound) return;
  delegationBound = true;

  document.addEventListener("click", (e: MouseEvent) => {
    const button = (e.target as Element).closest<HTMLElement>(
      "button.copy-content",
    );
    if (button) void copyFrom(button);
  });
}
