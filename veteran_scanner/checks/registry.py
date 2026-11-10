"""Registro do Windows: rastros de execução de programas (somente leitura).

- MuiCache: executáveis que já foram abertos.
- UserAssist: programas abertos pelo Explorer (nomes em ROT13, com data da última execução).
- Compatibility Assistant: executáveis já executados.
- BAM: executáveis com data de execução (geralmente exige administrador).
- HKCU\\Software: chaves criadas por programas.
"""

from __future__ import annotations

import codecs
import ntpath
import struct
from typing import Callable, Iterator, List, Optional, Tuple

from ..util import IS_WINDOWS, filetime_to_epoch, iso
from .base import CheckResult, Context

ID, LABEL = "registry", "Registro do Windows (rastros de execução)"

MUICACHE = r"Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache"
USERASSIST = r"Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"
COMPAT_STORE = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store"
BAM_PATHS = [r"SYSTEM\CurrentControlSet\Services\bam\State\UserSettings",
             r"SYSTEM\CurrentControlSet\Services\bam\UserSettings"]

# Cada item: (fonte, caminho/nome do executável, timestamp ou None)
Trace = Tuple[str, str, Optional[float]]


def _values(winreg, root, path) -> Iterator[Tuple[str, object]]:
    with winreg.OpenKey(root, path) as k:
        i = 0
        while True:
            try:
                name, data, _ = winreg.EnumValue(k, i)
            except OSError:
                return
            yield name, data
            i += 1


def _subkeys(winreg, root, path) -> List[str]:
    out = []
    with winreg.OpenKey(root, path) as k:
        i = 0
        while True:
            try:
                out.append(winreg.EnumKey(k, i))
            except OSError:
                return out
            i += 1


def collect_traces(notes: List[str]) -> List[Trace]:
    import winreg  # type: ignore

    HKCU, HKLM = winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE
    traces: List[Trace] = []

    try:
        for name, _ in _values(winreg, HKCU, MUICACHE):
            exe = name.rsplit(".", 1)[0] if name.lower().endswith((".friendlyappname", ".applicationcompany")) else name
            traces.append(("MuiCache", exe, None))
    except OSError:
        notes.append("MuiCache indisponível")

    try:
        for guid in _subkeys(winreg, HKCU, USERASSIST):
            try:
                for name, data in _values(winreg, HKCU, USERASSIST + "\\" + guid + "\\Count"):
                    decoded = codecs.decode(name, "rot_13")
                    ts = None
                    if isinstance(data, bytes) and len(data) >= 68:
                        ts = filetime_to_epoch(struct.unpack_from("<Q", data, 60)[0])
                    traces.append(("UserAssist", decoded, ts))
            except OSError:
                continue
    except OSError:
        notes.append("UserAssist indisponível")

    try:
        for name, _ in _values(winreg, HKCU, COMPAT_STORE):
            traces.append(("CompatibilityAssistant", name, None))
    except OSError:
        pass

    bam_ok = False
    for base in BAM_PATHS:
        try:
            for sid in _subkeys(winreg, HKLM, base):
                try:
                    for name, data in _values(winreg, HKLM, base + "\\" + sid):
                        ts = None
                        if isinstance(data, bytes) and len(data) >= 8:
                            ts = filetime_to_epoch(struct.unpack_from("<Q", data, 0)[0])
                        traces.append(("BAM", name, ts))
                    bam_ok = True
                except OSError:
                    continue
        except OSError:
            continue
    if not bam_ok:
        notes.append("BAM indisponível (requer administrador)")

    try:
        for sub in _subkeys(winreg, HKCU, "Software"):
            traces.append(("HKCU\\Software", sub, None))
    except OSError:
        pass
    return traces


def run(ctx: Context, collector: Optional[Callable[[List[str]], List[Trace]]] = None) -> CheckResult:
    res = CheckResult(ID, LABEL)
    if collector is None:
        if not IS_WINDOWS or ctx.env.simulated:
            res.status, res.note = "skipped", "Disponível apenas no Windows."
            return res
        collector = collect_traces
    notes: List[str] = []
    try:
        traces = collector(notes)
    except Exception as ex:
        res.status, res.note = "error", f"Falha ao ler o registro ({type(ex).__name__})."
        return res
    res.stats = {"rastros_lidos": len(traces)}
    if notes:
        res.status, res.note = "partial", "; ".join(notes) + "."
    best = {}  # (assinatura, fonte, caminho) -> trace com timestamp mais recente
    for source, raw, ts in traces:
        base = ntpath.basename(raw.rstrip("\\")) or raw
        sig = ctx.signatures.match(base)
        if not sig:
            continue
        key = (sig.id, source, raw.lower())
        prev = best.get(key)
        if prev is None or (ts or 0) > (prev[3] or 0):
            best[key] = (sig, source, raw, ts)
    for sig, source, raw, ts in best.values():
        res.findings.append(ctx.signature_finding(
            ID, sig, f"rastro no registro ({source})",
            {"fonte": source, "caminho": ctx.sanitize.path(raw), "data": iso(ts)}, ts))
    return res
