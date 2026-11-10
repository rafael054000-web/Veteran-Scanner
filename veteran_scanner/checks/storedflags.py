"""Listas de Fast Flags guardadas em arquivos (.json/.txt) em Downloads, Área de Trabalho e Documentos.

Muitos jogadores guardam listas de flags para colar no Bloxstrap. Só arquivos pequenos são abertos, e o
relatório mostra apenas as flags encontradas, nunca o resto do conteúdo.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from ..util import file_times, iso, newest, walk_limited
from .base import CheckResult, Context

ID, LABEL = "storedflags", "Listas de Fast Flags guardadas"
EXTS = {".json", ".txt"}
MAX_BYTES = 1_000_000
MIN_FLAGS = 3
FLAG_KEY = re.compile(r"""["']?\b([DS]?F(?:Flag|Int|String|Log)[A-Za-z0-9_]{3,})\b["']?\s*[:=]""")


def run(ctx: Context) -> CheckResult:
    res = CheckResult(ID, LABEL)
    fr = ctx.rules.get("fflags", {})
    opened = 0
    for root in ctx.env.user_folders():
        for entry, _ in walk_limited(root, max_depth=3):
            if os.path.splitext(entry.name)[1].lower() not in EXTS:
                continue
            try:
                if not entry.is_file() or entry.stat().st_size > MAX_BYTES:
                    continue
                with open(entry.path, "rb") as fh:
                    text = fh.read(MAX_BYTES).decode("utf-8", errors="replace")
            except OSError:
                continue
            opened += 1
            flags = sorted(set(FLAG_KEY.findall(text)))
            if not flags:
                continue
            abuse = [f for f in flags if f.lower() in ctx.flag_rules.known]
            suspicious = [f for f in flags if f not in abuse and any(p.search(f) for p in ctx.flag_rules.patterns)]
            if len(flags) < MIN_FLAGS and not abuse and not suspicious:
                continue
            path = Path(entry.path)
            created, modified = file_times(path)
            ts = newest(created, modified)
            if abuse:
                sev = fr.get("stored_abuse_severity", "medium")
                title = f"Lista de Fast Flags guardada com flag(s) de vantagem: {', '.join(abuse[:5])}"
            elif suspicious:
                sev = fr.get("stored_suspicious_severity", "low")
                title = f"Lista de Fast Flags guardada com nome(s) suspeito(s): {', '.join(suspicious[:5])}"
            else:
                sev = "info"
                title = f"Lista com {len(flags)} Fast Flags guardada"
            res.findings.append(ctx.finding(
                ID, sev, title,
                "Ter a lista guardada não prova que ela foi usada, mas mostra que o jogador teve acesso a essas flags. "
                "Compare com o arquivo ativo do Roblox/bootstrapper e com as datas.",
                {"arquivo": ctx.sanitize.path(path), "total_flags": len(flags), "flags_de_vantagem": abuse,
                 "flags_suspeitas": suspicious, "criado": iso(created), "modificado": iso(modified)}, ts))
    res.stats = {"arquivos_abertos": opened}
    return res
