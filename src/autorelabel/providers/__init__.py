"""Hypervisor back ends with a common interface (see libvirt.py / virtualbox.py)."""

from __future__ import annotations

from types import ModuleType


def get(provider: str) -> ModuleType:
    if provider == "virtualbox":
        from . import virtualbox

        return virtualbox
    from . import libvirt

    return libvirt
