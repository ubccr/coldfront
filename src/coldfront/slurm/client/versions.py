# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Supported Slurm REST API versions.

The **single source of truth** for which Slurm versions ColdFront's client
supports. Maps Slurm releases to the REST API version they expose; every
consumer — the client's version discovery, the e2e stack matrix, the mock
suite — derives from this one module. To change supported versions, edit
``SUPPORTED_SLURM_VERSIONS`` here and nothing else.

Current support: 26.05.x -> v0.0.45, 25.11.x -> v0.0.44. Older API versions
(24.05/24.11/25.05 -> v0.0.41-43) are deliberately NOT supported: discovery
is strict and will refuse a slurmrestd exposing only those.
"""

# Supported Slurm release -> REST API version, in release order.
SUPPORTED_SLURM_VERSIONS: dict[str, str] = {
    "26.05.4": "v0.0.45",
    "25.11.8": "v0.0.44",
}


def supported_slurm_versions() -> tuple[str, ...]:
    """The supported Slurm release versions (map keys), in release order."""
    return tuple(SUPPORTED_SLURM_VERSIONS)


def supported_api_versions() -> tuple[str, ...]:
    """The supported REST API versions, in descending preference order.

    Discovery probes the newest API version first, so this is the map values
    sorted newest-first rather than relying on dict insertion order.
    """
    return tuple(sorted(SUPPORTED_SLURM_VERSIONS.values(), reverse=True))


def api_version_for(slurm_version: str) -> str:
    """Return the REST API version a Slurm release exposes.

    Raises:
        ValueError: If ``slurm_version`` is not supported.
    """
    try:
        return SUPPORTED_SLURM_VERSIONS[slurm_version]
    except KeyError:
        raise ValueError(
            f"Unsupported Slurm version {slurm_version!r}; supported: {sorted(SUPPORTED_SLURM_VERSIONS)}"
        ) from None


def is_supported(slurm_version: str) -> bool:
    """Return True if ``slurm_version`` is a supported Slurm release."""
    return slurm_version in SUPPORTED_SLURM_VERSIONS


def slurm_version_for(api_version: str) -> str:
    """Return the Slurm release that exposes a given REST API version.

    Inverse of :func:`api_version_for`; used by discovery to report the
    negotiated Slurm release to consumers.

    Raises:
        ValueError: If ``api_version`` is not supported.
    """
    try:
        return next(slurm for slurm, api in SUPPORTED_SLURM_VERSIONS.items() if api == api_version)
    except StopIteration:
        raise ValueError(
            f"Unknown REST API version {api_version!r}; supported: {sorted(SUPPORTED_SLURM_VERSIONS.values())}"
        ) from None


__all__ = [
    "SUPPORTED_SLURM_VERSIONS",
    "supported_slurm_versions",
    "supported_api_versions",
    "api_version_for",
    "slurm_version_for",
    "is_supported",
]
