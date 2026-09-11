# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Task framework internals for ColdFront.

This package deliberately keeps its ``__init__`` free of imports: submodules
here (``system``, ``backends``, ``rq``, ``utils``) import ``coldfront.core.models``,
which in turn imports this package — eager imports here would create a
circular import. The system jobs are registered by ``CoreConfig.ready()``
importing ``coldfront.core.tasks.system`` explicitly.
"""
