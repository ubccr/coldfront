// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

/* eslint-disable @typescript-eslint/no-unnecessary-type-constraint */
type Dict<T extends unknown = unknown> = Record<string, T>;

type Nullable<T> = T | null;

interface ErrorBase extends Record<string, unknown> {
  error: string;
}

interface APIError extends Record<string, unknown> {
  error: string;
  exception: string;
}

type APIResponse<T extends Dict> = T | APIError | ErrorBase;

type APIUserConfig = Dict & {
  data: Dict;
};
