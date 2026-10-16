// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

declare global {
  interface Window {
    CSRF_TOKEN: string;
  }
}

type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
type ReqData = URLSearchParams | Dict | undefined | unknown;

/**
 * Generator that yields HTML elements by CSS query selector
 * @param query - CSS query selector string
 * @param container - Optional container to search within (defaults to document)
 * @yields HTMLElement - HTML elements (never null)
 */
export function* getElementsByQueryGenerator(
  query: string,
  container: Document | HTMLElement = document,
): Generator<HTMLElement, void, undefined> {
  const elements = container.querySelectorAll(query);
  for (let i = 0; i < elements.length; i++) {
    yield elements[i] as HTMLElement;
  }
}

export function hasError<E extends ErrorBase = ErrorBase>(
  data: Record<string, unknown>,
): data is E {
  return "error" in data;
}

export async function apiRequest<R extends Dict, D extends ReqData = undefined>(
  url: string,
  method: Method,
  data?: D,
): Promise<APIResponse<R>> {
  const token = window.CSRF_TOKEN;
  const headers = new Headers({ "X-CSRFToken": token });

  const body = typeof data !== "undefined" ? JSON.stringify(data) : undefined;
  if (body) {
    headers.set("content-type", "application/json");
  }

  const res = await fetch(url, {
    method,
    body,
    headers,
    credentials: "same-origin",
  });
  const contentType = res.headers.get("Content-Type");
  if (typeof contentType === "string" && contentType.includes("text")) {
    const error = await res.text();
    return { error } as ErrorBase;
  }
  const json = (await res.json()) as R | APIError;
  if (!res.ok && Array.isArray(json)) {
    const error = json.join("\n");
    return { error } as ErrorBase;
  } else if (!res.ok && "detail" in json) {
    return { error: json.detail } as ErrorBase;
  }
  return json;
}

export async function apiPatch<R extends Dict, D extends ReqData = Dict>(
  url: string,
  data: D,
): Promise<APIResponse<R>> {
  return await apiRequest(url, "PATCH", data);
}
