"""Arquivos e pastas: procura nomes de programas conhecidos e a estrutura típica de executores.

Só olha NOMES de arquivos/pastas (não abre o conteúdo) e com profundidade limitada.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

from ..util import file_times, iso as _iso, newest, walk_limited
from .base import CheckResult, Context

ID, LABEL = "filesystem", "Arquivos e pastas"
FILE_EXT = {".exe", ".zip", ".rar", ".7z", ".msi", ".dll", ".bat", ".lnk", ".crdownload", ".part"}
LAYOUT_SIBLINGS = {"workspace", "scripts", "bin"}


def roots(ctx: Context) -> List[Tuple[Path, int]]:
    env = ctx.env
    out: List[Tuple[Path, int]] = [(p, 3) for p in env.user_folders()]
    for p, depth in ((env.local_appdata, 2), (env.appdata, 2), (env.temp, 2)):
        if p:
            out.append((p, depth))
    for pf in env.program_files:
        out.append((pf, 1))
    return [(p, d) for p, d in out if p.is_dir()]


def run(ctx: Context) -> CheckResult:
    res = CheckResult(ID, LABEL)
    seen = set()
    scanned = 0
    for root, depth in roots(ctx):
        for entry, _ in walk_limited(root, max_depth=depth):
            scanned += 1
            name = entry.name
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue
            ext = os.path.splitext(name)[1].lower()
            path = Path(entry.path)

            if is_dir and name.lower() == "autoexec":
                _check_layout(ctx, res, path, seen)

            if not is_dir and ext not in FILE_EXT:
                continue
            sig = ctx.signatures.match(name)
            if not sig:
                continue
            key = (sig.id, str(path).lower())
            if key in seen:
                continue
            seen.add(key)
            created, modified = file_times(path)
            kind = "pasta" if is_dir else "arquivo"
            res.findings.append(ctx.signature_finding(
                ID, sig, ("pasta encontrada" if is_dir else "arquivo encontrado"),
                {"caminho": ctx.sanitize.path(path), "tipo": kind,
                 "criado": _iso(created), "modificado": _iso(modified)},
                newest(created, modified)))
    res.stats = {"entradas_verificadas": scanned, "raizes": [ctx.sanitize.path(r) for r, _ in roots(ctx)]}
    return res


def _check_layout(ctx: Context, res: CheckResult, autoexec: Path, seen: set) -> None:
    parent = autoexec.parent
    try:
        siblings = {n.lower() for n in os.listdir(parent)}
    except OSError:
        return
    hits = sorted(siblings & LAYOUT_SIBLINGS)
    if not hits:
        return
    key = ("layout", str(parent).lower())
    if key in seen:
        return
    seen.add(key)
    created, modified = file_times(autoexec)
    res.findings.append(ctx.finding(
        ID, ctx.rules.get("executor_folder_layout_severity", "high"),
        "Estrutura de pastas típica de executor (autoexec + " + "/".join(hits) + ")",
        "Executores de script costumam criar as pastas 'autoexec' e 'workspace'/'scripts' ao lado do programa.",
        {"pasta": ctx.sanitize.path(parent), "subpastas": ["autoexec"] + hits,
         "criado": _iso(created), "modificado": _iso(modified)},
        newest(created, modified)))

