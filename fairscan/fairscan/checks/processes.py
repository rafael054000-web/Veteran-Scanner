"""Processos em execução agora (via `tasklist`). Não interage com nenhum processo."""

from __future__ import annotations

import csv
import io
import locale
import subprocess
import time
from typing import Callable, List, Optional

from ..signatures import category_severity
from ..util import IS_WINDOWS, SEVERITIES
from .base import CheckResult, Context

ID, LABEL = "processes", "Processos em execução"


def list_processes() -> List[str]:
    out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, timeout=30)
    text = out.stdout.decode(locale.getpreferredencoding(False), errors="replace")
    names = []
    for row in csv.reader(io.StringIO(text)):
        if row:
            names.append(row[0])
    return names


def run(ctx: Context, lister: Optional[Callable[[], List[str]]] = None) -> CheckResult:
    res = CheckResult(ID, LABEL)
    if lister is None:
        if not IS_WINDOWS or ctx.env.simulated:
            res.status, res.note = "skipped", "Disponível apenas no Windows."
            return res
        lister = list_processes
    try:
        names = lister()
    except Exception as ex:
        res.status, res.note = "error", f"Não foi possível listar processos ({type(ex).__name__})."
        return res
    res.stats = {"processos": len(names), "roblox_aberto": any(n.lower() == "robloxplayerbeta.exe" for n in names)}
    now = time.time()
    seen = set()
    for n in names:
        sig = ctx.signatures.match(n)
        if not sig or sig.id in seen:
            continue
        seen.add(sig.id)
        sev = category_severity(ctx.rules, sig.category, sig.confidence)
        if ctx.rules.get("running_now_bonus", True) and sev not in ("info", "critical"):
            sev = SEVERITIES[SEVERITIES.index(sev) + 1]
        res.findings.append(ctx.signature_finding(ID, sig, "em execução AGORA", {"processo": n}, now, sev))
    return res
