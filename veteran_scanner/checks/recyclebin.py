"""Lixeira do Windows: itens apagados que ainda não foram esvaziados.

Lê só os arquivos de índice `$I...` (nome original + data da exclusão), nunca o conteúdo apagado.
"""

from __future__ import annotations

import ntpath
import os
import struct
from pathlib import Path
from typing import Optional, Tuple

from ..util import filetime_to_epoch, iso
from .base import CheckResult, Context
from .deleted import evaluate

ID, LABEL = "recyclebin", "Lixeira (itens apagados)"


def parse_index(data: bytes) -> Optional[Tuple[str, Optional[float]]]:
    """Formato $I: versão 1 (Vista–8.1) ou 2 (Windows 10/11). Retorna (caminho original, data da exclusão)."""
    if len(data) < 24:
        return None
    version, _size, ft = struct.unpack_from("<qqQ", data, 0)
    if version == 1:
        raw = data[24:24 + 520]
    elif version == 2 and len(data) >= 28:
        (nchars,) = struct.unpack_from("<I", data, 24)
        raw = data[28:28 + nchars * 2]
    else:
        return None
    path = raw.decode("utf-16-le", errors="replace").split("\x00", 1)[0]
    return (path, filetime_to_epoch(ft)) if path else None


def run(ctx: Context) -> CheckResult:
    res = CheckResult(ID, LABEL)
    bins = [d / "$Recycle.Bin" for d in ctx.env.drives if (d / "$Recycle.Bin").is_dir()]
    if not bins:
        res.status, res.note = "skipped", "Lixeira não encontrada."
        return res
    total, unreadable = 0, 0
    for b in bins:
        try:
            sids = [Path(e.path) for e in os.scandir(b) if e.is_dir()]
        except OSError:
            unreadable += 1
            continue
        for sid in sids:
            try:
                names = [n for n in os.listdir(sid) if n.startswith("$I")]
            except OSError:
                continue  # Lixeira de outro usuário: sem permissão (esperado)
            for n in names:
                try:
                    with open(sid / n, "rb") as fh:
                        parsed = parse_index(fh.read(4096))
                except OSError:
                    continue
                if not parsed:
                    continue
                total += 1
                original, ts = parsed
                base = ntpath.basename(original.rstrip("\\"))
                f = evaluate(ctx, ID, base, "na Lixeira",
                             {"caminho_original": ctx.sanitize.path(original), "apagado_em": iso(ts)}, ts)
                if f:
                    res.findings.append(f)
    res.stats = {"itens_na_lixeira": total}
    if unreadable and not total:
        res.status, res.note = "partial", "Não foi possível ler a Lixeira."
    return res
