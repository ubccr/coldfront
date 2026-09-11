# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Generic container wrappers for ColdFront e2e tests.

This module holds setup code that can be reused across all e2e test apps. The
generic :class:`BaseComposeStack` wraps ``testcontainers.compose.DockerCompose`` to
drive a docker compose stack: it writes a per-stack env file (project name),
starts the stack and waits for healthchecks, exposes helpers to exec into
containers, and tears everything down (volumes included) on stop.

The Slurm-specific stack (:class:`SlurmStack`) lives in
``tests/e2e/slurm/containers.py`` and inherits from :class:`BaseComposeStack`.

Design notes
------------
* The stack uses **pre-built images** from Docker Hub; nothing is built
  locally.
* The compose file is fully parameterized via a per-stack ``.env`` file passed
  to ``DockerCompose(env_file=...)`` — compose variables keep the file reusable
  across versions and config variants without editing it.
* ``COMPOSE_PROJECT_NAME`` is unique per stack, so multiple stacks can run
  side by side without volume / container-name collisions.
"""

import os
import tempfile
from pathlib import Path
from typing import Self

from testcontainers.compose import DockerCompose


class BaseComposeStack:
    """Thin wrapper over ``testcontainers.compose.DockerCompose`` shared by e2e stacks.

    Subclasses set the docker compose file location (``_COMPOSE_DIR`` and
    ``_COMPOSE_FILE``) and extend ``_env_content`` with their compose
    variables. This base writes the env file, starts the stack and waits for
    healthchecks, exposes exec helpers, and tears everything down on stop.
    """

    # Docker compose file location — subclass sets these.
    _COMPOSE_DIR: Path
    _COMPOSE_FILE: str

    def __init__(self, *, project_name: str) -> None:
        self.project_name = project_name
        self._compose: DockerCompose | None = None
        self._env_file: tempfile._TemporaryFileWrapper | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Write the env file and start the compose stack (waits for healthy)."""
        env = tempfile.NamedTemporaryFile(
            "w",
            prefix=f"{self.project_name}-",
            suffix=".env",
            delete=False,
        )
        env.write(self._env_content())
        env.close()
        self._env_file = env

        self._compose = DockerCompose(
            context=str(self._COMPOSE_DIR),
            compose_file_name=self._COMPOSE_FILE,
            env_file=env.name,
            wait=True,
        )
        self._compose.start()

    def stop(self) -> None:
        """Tear down the stack (``docker compose down --volumes``) and clean up."""
        if self._compose is not None:
            self._compose.stop(down=True)
            self._compose = None
        if self._env_file is not None:
            os.unlink(self._env_file.name)
            self._env_file = None

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def compose(self) -> DockerCompose:
        if self._compose is None:
            raise RuntimeError("stack not started")
        return self._compose

    def exec(self, service: str, command: list[str]) -> tuple[str, str, int]:
        """Run a command inside a compose service; returns (stdout, stderr, rc)."""
        return self.compose.exec_in_container(command, service_name=service)

    def ensure_system_user(self, name: str, services: tuple[str, ...]) -> None:
        """Create a system user (uid in ``/etc/passwd``) in the given services.

        Some daemons (e.g. slurmdbd) resolve REST-created users to a uid via
        ``getpwnam()``; a user that does not exist on the system is silently
        rejected. Pre-built images bake their users at build time, so we add
        the user at runtime in each service that needs it.

        Idempotent: skips if the user already exists.
        """
        for service in services:
            out, err, rc = self.exec(
                service,
                ["bash", "-c", f"id {name} >/dev/null 2>&1 || useradd -m -s /bin/bash {name}"],
            )
            if rc != 0:
                raise RuntimeError(f"failed to create system user {name!r} in {service}: {err.strip() or out.strip()}")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _env_content(self) -> str:
        """Compose interpolation variables for this stack (one ``.env`` file)."""
        return f"COMPOSE_PROJECT_NAME={self.project_name}\n"


def ensure_docker_available() -> None:
    """Raise if the Docker CLI is not reachable (used by fixtures to skip)."""
    import shutil
    from subprocess import run

    if not shutil.which("docker"):
        raise RuntimeError("docker not found on PATH")
    try:
        run(["docker", "info"], capture_output=True, check=True, timeout=30)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"docker daemon not reachable: {exc}") from exc
