"""Todas as verificações são somente leitura."""

from . import (fflags, filesystem, logs, prefetch, processes, recent, recyclebin, registry, roblox_install,
               storedflags, usn)

ALL = [fflags, storedflags, roblox_install, filesystem, processes, prefetch, registry, recent, recyclebin, usn, logs]
