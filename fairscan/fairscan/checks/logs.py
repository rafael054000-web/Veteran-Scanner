"""Logs do Roblox (%LOCALAPPDATA%\\Roblox\\logs): linha do tempo das sessões e menções a programas.

O conteúdo dos logs NÃO vai para o relatório; só as menções encontradas e a contagem de sessões.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from ..util import iso
from .base import CheckResult, Context

ID, LABEL = "logs", "Logs do Roblox"
MAX_FILES = 300
MAX_BYTES = 5_000_000


def _keyword_regex(ctx: Context):
    words = set()
    for sig in ctx.signatures.signatures:
        if sig.confidence != "high" or sig.category not in ("executor", "injector"):
            continue
        for n in sig.names:
            n = n.strip().lower()
            if len(n) >= 5:
                words.add(re.escape(n))
    if not words:
        return None
    return re.compile(r"(?<![a-z0-9])(" + "|".join(sorted(words, key=len, reverse=True)) + r")(?![a-z0-9])", re.IGNORECASE)


def run(ctx: Context) -> CheckResult:
    res = CheckResult(ID, LABEL)
    if not ctx.env.local_appdata:
        res.status, res.note = "skipped", "Pasta LOCALAPPDATA desconhecida."
        return res
    roblox = ctx.env.local_appdata / "Roblox"
    folder = roblox / "logs"
    installed = (roblox / "Versions").is_dir()
    try:
        entries = [Path(e.path) for e in os.scandir(folder) if e.is_file() and e.name.lower().endswith(".log")]
    except OSError:
        entries = []

    if not entries:
        res.stats = {"arquivos_log": 0}
        if installed:
            res.findings.append(ctx.finding(
                ID, ctx.rules.get("missing_logs_severity", "low"),
                "Nenhum log do Roblox encontrado",
                "O Roblox está instalado, mas não há logs. Eles podem ter sido apagados, ou o jogo não é aberto há "
                "algum tempo (o Roblox remove logs antigos sozinho). Pergunte ao jogador.",
                {"pasta": ctx.sanitize.path(folder)}))
        else:
            res.status, res.note = "skipped", "Pasta de logs não encontrada."
        return res

    mtimes = []
    for p in entries:
        try:
            mtimes.append((p, p.stat().st_mtime))
        except OSError:
            pass
    mtimes.sort(key=lambda x: x[1], reverse=True)
    in_window = [m for _, m in mtimes if ctx.since is None or m >= ctx.since]
    res.stats = {
        "arquivos_log": len(mtimes),
        "log_mais_recente": iso(mtimes[0][1]) if mtimes else None,
        "log_mais_antigo": iso(mtimes[-1][1]) if mtimes else None,
        "logs_no_periodo": len(in_window),
    }
    if ctx.since is not None and not in_window:
        res.findings.append(ctx.finding(ID, "info", "Nenhuma sessão do Roblox no período informado",
                                        "Não há logs posteriores à data de início (--since)."))

    rx = _keyword_regex(ctx)
    if rx is None:
        return res
    hits = {}
    for p, m in mtimes[:MAX_FILES]:
        try:
            with open(p, "rb") as fh:
                text = fh.read(MAX_BYTES).decode("utf-8", errors="replace")
        except OSError:
            continue
        for match in rx.finditer(text):
            word = match.group(1).lower()
            if word not in hits or m > hits[word][1]:
                hits[word] = (p.name, m)
    for word, (fname, m) in hits.items():
        sig = ctx.signatures.match(word)
        title = f"Menção a '{word}' em log do Roblox"
        res.findings.append(ctx.finding(
            ID, ctx.rules.get("log_mention_severity", "low"), title,
            "O nome de um programa conhecido aparece no log. Pode ser coincidência (nome de jogo, chat etc.); "
            "use como indício complementar.",
            {"termo": word, "assinatura": sig.id if sig else None, "arquivo_log": fname}, m))
    return res
