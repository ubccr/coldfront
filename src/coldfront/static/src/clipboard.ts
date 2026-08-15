// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import Clipboard from 'clipboard';
import { getElementsByQueryGenerator } from './util';

export function initClipboard(): void {
  for (const element of getElementsByQueryGenerator('.copy-content')) {
    new Clipboard(element);
  }
}
