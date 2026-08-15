// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { initColorSelects, initStaticSelects } from './static';
import { initDynamicSelects } from './dynamic';

export function initSelects(): void {
  for (const func of [
    initColorSelects,
    initStaticSelects,
    initDynamicSelects,
  ]) {
    func();
  }
}
