// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { initMoveButtons } from './moveOptions';
import { initReslug } from './reslug';
import { initSelectAll } from './selectAll';
import { initMarkdownPreviews } from './markdownPreview';

export function initButtons(): void {
  for (const func of [
    initMoveButtons,
    initReslug,
    initSelectAll,
    initMarkdownPreviews,
  ]) {
    func();
  }
}
