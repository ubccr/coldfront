// SPDX-FileCopyrightText: (C) DigitalOcean, LLC
// SPDX-FileCopyrightText: (C) University at Buffalo
//
// SPDX-License-Identifier: Apache-2.0

import { registerCfSelect } from "./cfSelect";

// Register the Alpine `cfSelect` component at module load (before Alpine.start()
// runs in coldfront.ts), so the initial DOM is picked up. HTMX-swapped fragments
// are re-initialized via Alpine.initTree() in the htmx afterSettle hook.
registerCfSelect();
