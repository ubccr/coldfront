// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

declare global {
  interface Window {
    CSRF_TOKEN: string;
  }
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
type ReqData = URLSearchParams | Dict | undefined | unknown;
type SelectedOption = { name: string; options: string[] };

/**
 * Generator that yields HTML elements by CSS query selector
 * @param query - CSS query selector string
 * @param container - Optional container to search within (defaults to document)
 * @yields HTMLElement - HTML elements (never null)
 */
export function* getElementsByQueryGenerator(
  query: string,
  container: Document | HTMLElement = document
): Generator<HTMLElement, void, undefined> {
  const elements = container.querySelectorAll(query);
  for (let i = 0; i < elements.length; i++) {
    yield elements[i] as HTMLElement;
  }
}

/**
 * Type guard to determine if a value is not null, undefined, or empty.
 */
/* eslint-disable @typescript-eslint/no-unnecessary-type-constraint */
export function isTruthy<V extends unknown>(value: V): value is NonNullable<V> {
  const badStrings = ['', 'null', 'undefined'];
  if (Array.isArray(value)) {
    return value.length > 0;
  } else if (typeof value === 'string' && !badStrings.includes(value)) {
    return true;
  } else if (typeof value === 'number') {
    return true;
  } else if (typeof value === 'boolean') {
    return true;
  } else if (typeof value === 'object' && value !== null) {
    return true;
  }
  return false;
}

export function getElement<E extends HTMLElement>(id: string): Nullable<E> {
  return document.getElementById(id) as Nullable<E>;
}

/**
 * Replace all occurrences of a pattern with a replacement string.
 *
 * This is a browser-compatibility-focused drop-in replacement for `String.prototype.replaceAll()`,
 * introduced in ES2021.
 *
 * @param input string to be processed.
 * @param pattern regex pattern string or RegExp object to search for.
 * @param replacement replacement substring with which `pattern` matches will be replaced.
 * @returns processed version of `input`.
 */
export function hasError<E extends ErrorBase = ErrorBase>(
  data: Record<string, unknown>
): data is E {
  return 'error' in data;
}

export async function apiRequest<R extends Dict, D extends ReqData = undefined>(
  url: string,
  method: Method,
  data?: D
): Promise<APIResponse<R>> {
  const token = window.CSRF_TOKEN;
  const headers = new Headers({ 'X-CSRFToken': token });

  let body;
  if (typeof data !== 'undefined') {
    body = JSON.stringify(data);
    headers.set('content-type', 'application/json');
  }

  const res = await fetch(url, {
    method,
    body,
    headers,
    credentials: 'same-origin',
  });
  const contentType = res.headers.get('Content-Type');
  if (typeof contentType === 'string' && contentType.includes('text')) {
    const error = await res.text();
    return { error } as ErrorBase;
  }
  const json = (await res.json()) as R | APIError;
  if (!res.ok && Array.isArray(json)) {
    const error = json.join('\n');
    return { error } as ErrorBase;
  } else if (!res.ok && 'detail' in json) {
    return { error: json.detail } as ErrorBase;
  }
  return json;
}

export async function apiPatch<R extends Dict, D extends ReqData = Dict>(
  url: string,
  data: D
): Promise<APIResponse<R>> {
  return await apiRequest(url, 'PATCH', data);
}

/**
 * Iterate through a select element's options and return an array of options that are selected.
 *
 * @param base Select element.
 * @param selector Optionally specify a selector. 'select' by default.
 * @returns Array of selected options.
 */
export function getSelectedOptions<E extends HTMLElement>(
  base: E,
  selector: string = 'select'
): SelectedOption[] {
  let selected = [] as SelectedOption[];
  for (const element of base.querySelectorAll<HTMLSelectElement>(selector)) {
    if (element !== null) {
      const select = { name: element.name, options: [] } as SelectedOption;
      for (const option of element.options) {
        if (option.selected) {
          select.options.push(option.value);
        }
      }
      selected = [...selected, select];
    }
  }
  return selected;
}

export function replaceAll(
  input: string,
  pattern: string | RegExp,
  replacement: string
): string {
  // Ensure input is a string.
  if (typeof input !== 'string') {
    throw new TypeError("replaceAll 'input' argument must be a string");
  }
  // Ensure pattern is a string or RegExp.
  if (typeof pattern !== 'string' && !(pattern instanceof RegExp)) {
    throw new TypeError(
      "replaceAll 'pattern' argument must be a string or RegExp instance"
    );
  }
  // Ensure replacement is able to be stringified.
  switch (typeof replacement) {
    case 'boolean':
      replacement = String(replacement);
      break;
    case 'number':
      replacement = String(replacement);
      break;
    case 'string':
      break;
    default:
      throw new TypeError(
        "replaceAll 'replacement' argument must be stringifyable"
      );
  }

  if (pattern instanceof RegExp) {
    // Add global flag to existing RegExp object and deduplicate
    const flags = Array.from(new Set([...pattern.flags.split(''), 'g'])).join(
      ''
    );
    pattern = new RegExp(pattern.source, flags);
  } else {
    // Create a RegExp object with the global flag set.
    pattern = new RegExp(pattern, 'g');
  }

  return input.replace(pattern, replacement);
}
