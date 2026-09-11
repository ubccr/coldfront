# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Slurm Docker stack wrapper for the Slurm e2e suite.

:class:`SlurmStack` drives the ``slurm-docker-cluster`` compose stack
through the generic :class:`BaseComposeStack` wrapper. It adds the Slurm-specific
setup: version validation, the per-version REST API mapping, the slurm.conf
variant bind-mount, a distinct host port per stack, and helpers to fetch the
REST endpoint and the admin JWT.

Design notes
------------
* The stack uses **pre-built images** from Docker Hub
  (``ubccr/slurm-docker-cluster:<version>``); nothing is built locally.
* The compose file is fully parameterized via a per-stack ``.env`` file —
  compose variables like ``SLURM_VERSION``, ``COMPOSE_PROJECT_NAME`` and
  ``SLURM_CONF`` keep the file reusable across versions and config variants without editing it.
* ``COMPOSE_PROJECT_NAME`` is unique per stack, so multiple stacks (e.g. two
  Slurm versions in one pytest session) can run side by side without volume /
  container-name collisions.
* ``slurm.conf`` is **not** baked into the image in a way we can tweak (e.g.
  ``TRESBillingWeights``), so a host config file is bind-mounted read-only over
  ``/etc/slurm/slurm.conf`` in the containers that read it (``slurmctld`` and
  ``slurmrestd``). ``slurmdbd.conf`` stays baked-in.
"""

from pathlib import Path

from coldfront.slurm.client.versions import (
    SUPPORTED_SLURM_VERSIONS,
    api_version_for,
    is_supported,
)
from tests.e2e.containers import BaseComposeStack

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_COMPOSE_DIR = Path(__file__).resolve().parent / "compose"
_COMPOSE_FILE = "docker-compose.slurm.yml"
_CONFIG_DIR = Path(__file__).resolve().parent / "config"

# ---------------------------------------------------------------------------
# Supported Slurm versions -> REST API version
# ---------------------------------------------------------------------------
# The canonical release -> API mapping lives in
# ``coldfront.slurm.client.versions``; this stack wrapper derives from it so
# there is a single place to change supported versions.

# Host port each version's stock stack publishes for slurmrestd (container
# port is always 6820). A second stack for the same version (e.g. the billing
# role) shifts +2 so the two stacks can run concurrently without a host-port
# clash. Both stacks share the same base slurm.conf; the variant/role label
# keeps their projects and ports distinct.
_RESTD_PORT_BASE: dict[str, int] = {
    "26.05.4": 6820,
    "25.11.8": 6821,
}

# Every supported version needs a host port, and no port should linger for a
# version we no longer support — guard against drift between the two maps.
assert set(_RESTD_PORT_BASE) == set(SUPPORTED_SLURM_VERSIONS), (
    "_RESTD_PORT_BASE keys must exactly match the supported Slurm versions; "
    f"ports={sorted(_RESTD_PORT_BASE)} supported={sorted(SUPPORTED_SLURM_VERSIONS)}"
)


class SlurmStack(BaseComposeStack):
    """A real Slurm cluster (slurmdbd/slurmctld/slurmrestd + mysql) in Docker.

    Inherits the generic compose lifecycle from :class:`BaseComposeStack` and adds the
    Slurm-specific setup: version validation, slurm.conf variant, host port,
    REST endpoint, and the admin JWT.
    """

    _COMPOSE_DIR = _COMPOSE_DIR
    _COMPOSE_FILE = _COMPOSE_FILE

    def __init__(
        self,
        version: str = "26.05.4",
        slurm_conf: str = "slurm.conf",
        variant: str = "stock",
        cpu_worker_count: int = 1,
        project_name: str | None = None,
    ) -> None:
        if not is_supported(version):
            raise ValueError(f"Unsupported Slurm version {version!r}; supported: {sorted(SUPPORTED_SLURM_VERSIONS)}")
        self.version = version
        self.api_version = api_version_for(version)
        self.slurm_conf_path = _CONFIG_DIR / slurm_conf
        if not self.slurm_conf_path.exists():
            raise FileNotFoundError(f"slurm.conf variant not found: {self.slurm_conf_path}")
        self.cpu_worker_count = cpu_worker_count
        # Unique per-stack compose project name -> isolated volumes/containers.
        # Multiple stacks for the same version share the same slurm.conf, so the
        # variant/role label (e.g. "stock" vs "billing") is what keeps their
        # projects and host ports distinct.
        conf_stem = Path(slurm_conf).stem
        self.project_name = project_name or f"coldfront-slurm-{version.replace('.', '')}-{conf_stem}-{variant}"
        # Distinct host port per stack so concurrent stacks of the same version
        # (e.g. stock + billing) don't publish the same port twice.
        self.restd_port = _RESTD_PORT_BASE[version] + (2 if variant != "stock" else 0)
        super().__init__(project_name=self.project_name)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def cluster_name(self) -> str:
        """Cluster name defined in the slurm.conf (``ClusterName=...``)."""
        for line in self.slurm_conf_path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("ClusterName="):
                return stripped.split("=", 1)[1].strip()
        raise RuntimeError(f"no ClusterName= in {self.slurm_conf_path}")

    def restd_url(self) -> str:
        """Host-visible base URL of slurmrestd (e.g. ``http://127.0.0.1:6820``)."""
        host = self.compose.get_service_host("slurmrestd", 6820)
        # The container port is always 6820; the host-side published port is
        # self.restd_port (per-stack, so concurrent stacks don't clash).
        # testcontainers leaves 0.0.0.0/:: as-is on Linux, but those are not
        # connectable from the host; the compose port is published on all
        # interfaces, so 127.0.0.1 is the correct loopback target.
        if host in ("0.0.0.0", "::", "localhost", ""):
            host = "127.0.0.1"
        return f"http://{host}:{self.restd_port}"

    def jwt(self) -> str:
        """Fetch an admin JWT from slurmctld (``scontrol token``).

        Requests a long lifespan (7 days) so long test sessions don't outlive
        the token. Root (uid 0) counts as a SlurmUser, so it is exempt from the
        ``max_token_lifespan`` cap in slurm.conf; we still set that cap and
        request the lifespan explicitly for robustness.
        """
        out, err, rc = self.exec("slurmctld", ["bash", "-c", "scontrol token lifespan=604800"])
        if rc != 0:
            raise RuntimeError(f"failed to obtain slurm JWT: {err.strip()}")
        for line in out.splitlines():
            if "SLURM_JWT=" in line:
                token = line.split("SLURM_JWT=", 1)[1].strip()
                if token:
                    return token
        raise RuntimeError(f"could not parse JWT from scontrol token output: {out!r}")

    def ensure_system_user(self, name: str) -> None:
        """Create a system user (uid in ``/etc/passwd``) in the Slurm containers.

        slurmdbd resolves REST-created users to a uid via ``getpwnam()``; a
        user that does not exist on the system is silently rejected (the REST
        create returns 200 but stores nothing). The reference
        ``slurm-docker-cluster`` bakes its users at image build time; since we
        use pre-built images we add the user at runtime in each container that
        needs it (slurmdbd for accounting, slurmctld for job submission).
        """
        super().ensure_system_user(name, ("slurmdbd", "slurmctld"))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _env_content(self) -> str:
        """Compose interpolation variables for this stack (one ``.env`` file)."""
        lines = [
            super()._env_content().rstrip("\n"),
            f"SLURM_VERSION={self.version}",
            # Host path of the slurm.conf variant bind-mounted into the stack.
            f"SLURM_CONF={self.slurm_conf_path}",
            f"SLURMRESTD_PORT={self.restd_port}",
            f"CPU_WORKER_COUNT={self.cpu_worker_count}",
            "MYSQL_USER=slurm",
            "MYSQL_PASSWORD=password",
            "MYSQL_DATABASE=slurm_acct_db",
            "SSH_ENABLE=false",
            # Image entrypoint backgrounds slurmdbd/slurmctld and runs `sleep
            # infinity` when ALLOW_RESTARTS=true, so per-test cleanup can kill
            # and re-exec the slurmdbd process without restarting its container.
            "ALLOW_RESTARTS=true",
        ]
        return "\n".join(lines) + "\n"
