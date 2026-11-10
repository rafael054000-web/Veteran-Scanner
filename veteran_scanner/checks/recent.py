"""Itens recentes do Windows (atalhos em %APPDATA%\\Microsoft\\Windows\\Recent). Só lê os nomes."""

from __future__ import annotations

import os

from ..util import file_times, iso
from .base import CheckResult, Context

ID, LABEL = "recent", "Itens recentes do Windows"


def run(ctx: Context) -> CheckResult:
    res = CheckResult(ID, LABEL)
    if not ctx.env.appdata:
        res.status, res.note = "skipped", "Pasta APPDATA desconhecida."
        return res
    folder = ctx.env.appdata / "Microsoft" / "Windows" / "Recent"
    try:
        names = [n for n in os.listdir(folder) if n.lower().endswith(".lnk")]
    except OSError:
        res.status, res.note = "skipped", "Pasta de itens recentes não encontrada."
        return res
    res.stats = {"atalhos": len(names)}
    for n in names:
        sig = ctx.signatures.match(n)
        if not sig:
            continue
        _, modified = file_times(folder / n)
        res.findings.append(ctx.signature_finding(
            ID, sig, "aberto recentemente (Itens recentes)",
            {"atalho": n, "data": iso(modified)}, modified))
    return res
