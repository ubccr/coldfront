// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { getElementsByQueryGenerator } from "../util";

/**
 * Create a slug from any input string.
 *
 * @param slug Original string.
 * @param chars Maximum number of characters.
 * @returns Slugified string.
 */
function slugify(slug: string, chars: number): string {
  return slug
    .replace(/[^\-.\w\s]/g, "") // Remove unneeded chars
    .replace(/^[\s.]+|[\s.]+$/g, "") // Trim leading/trailing spaces
    .replace(/[-.\s]+/g, "-") // Convert spaces and decimals to hyphens
    .toLowerCase() // Convert to lowercase
    .substring(0, chars); // Trim to first chars chars
}

/**
 * For any slug fields, add event listeners to handle automatically generating slug values.
 *
 * @param root Optional root to bind within (defaults to the document). Called with the
 *   swapped subtree by the htmx hook so only newly inserted buttons are bound — re-running
 *   over the whole document would stack duplicate listeners on already-bound fields.
 */
export function initReslug(root: Document | HTMLElement = document): void {
  for (const element of getElementsByQueryGenerator("button.reslug", root)) {
    const slugButton = element as HTMLButtonElement;
    const form = slugButton.form;
    if (form == null) continue;

    const slugField = form.querySelector(
      "input[name='slug']",
    ) as HTMLInputElement;
    if (slugField == null) continue;

    const sourceId = slugField.getAttribute("slug_source");
    const sourceField = form.querySelector(
      `#id_${sourceId}`,
    ) as HTMLInputElement;

    const slugLengthAttr = slugField.getAttribute("maxlength");
    let slugLength = 50;

    if (slugLengthAttr) {
      slugLength = Number(slugLengthAttr);
    }
    sourceField.addEventListener("blur", () => {
      if (!slugField.value) {
        slugField.value = slugify(sourceField.value, slugLength);
      }
    });
    slugButton.addEventListener("click", () => {
      slugField.value = slugify(sourceField.value, slugLength);
    });
  }
}
