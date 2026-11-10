"""Prefetch do Windows: registra programas executados recentemente (C:\\Windows\\Prefetch).

Normalmente exige executar o scanner como administrador.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..util import file_times, iso
from .base import CheckResult, Context

ID, LABEL = "prefetch", "Prefetch do Windows (programas executados)"


def run(ctx: Context) -> CheckResult:
    res = CheckResult(ID, LABEL)
    if not ctx.env.windir:
        res.status, res.note = "skipped", "Pasta do Windows desconhecida."
        return res
    folder = ctx.env.windir / "Prefetch"
    try:
        names = os.listdir(folder)
    except PermissionError:
        res.status, res.note = "skipped", "Sem permissão. Execute como administrador para incluir esta verificação."
        return res
    except OSError:
        res.status, res.note = "skipped", "Pasta Prefetch não encontrada."
        return res
    pf = [n for n in names if n.lower().endswith(".pf")]
    res.stats = {"arquivos_pf": len(pf)}
    if not pf:
        res.status = "partial"
        res.note = "Prefetch vazio: pode estar desativado no sistema ou ter sido limpo."
        return res
    for n in pf:
        sig = ctx.signatures.match(n)
        if not sig:
            continue
        p = folder / n
        _, modified = file_times(p)
        res.findings.append(ctx.signature_finding(
            ID, sig, "foi executado (Prefetch)",
            {"arquivo_prefetch": n, "ultima_execucao_aprox": iso(modified)},
            modified))
    return res
