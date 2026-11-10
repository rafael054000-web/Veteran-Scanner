"""Diário do NTFS (USN Journal): arquivos apagados ou renomeados recentemente.

O Windows anota cada alteração de arquivo nesse diário, que costuma cobrir os últimos dias. Mesmo que o jogador
apague um executor ou o arquivo de Fast Flags antes da verificação, a exclusão fica registrada (nome e data).
Usa o comando oficial `fsutil usn readjournal` e exige administrador. Só os NOMES dos arquivos são lidos.
"""

from __future__ import annotations

import csv
import datetime as _dt
import locale
import re
import subprocess
import time
from typing import Callable, Iterable, Iterator, List, Optional, Tuple

from ..util import IS_WINDOWS, iso
from .base import CheckResult, Context
from .deleted import evaluate

ID, LABEL = "usn", "Arquivos apagados/renomeados recentemente (USN Journal)"
HINT = "pode levar até 2 minutos"

REASON_DELETE = 0x00000200
REASON_RENAME_OLD = 0x00001000
TIMEOUT_S = 150
MAX_FINDINGS = 60
PREFETCH_WIPE_THRESHOLD = 10

_HEX = re.compile(r"0x([0-9a-fA-F]{1,8})")
_TS_FORMATS = ("%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S",
               "%d/%m/%Y %H:%M", "%m/%d/%Y %I:%M:%S %p")

# (nome do arquivo, motivo bruto, data bruta)
Record = Tuple[str, str, str]


def _day_first() -> bool:
    loc = (locale.getlocale()[0] or "").lower()
    return not (loc.startswith("en_us") or loc.startswith("english_united states"))


def parse_timestamp(raw: str, day_first: bool = True) -> Optional[float]:
    raw = raw.strip()
    fmts = list(_TS_FORMATS)
    if not day_first:
        fmts[0], fmts[1] = fmts[1], fmts[0]
    for fmt in fmts:
        try:
            return _dt.datetime.strptime(raw, fmt).timestamp()
        except ValueError:
            continue
    return None


def reason_flags(raw: str) -> int:
    m = _HEX.search(raw)
    if m:
        return int(m.group(1), 16)
    low = raw.lower()
    flags = 0
    if "delete" in low or "exclus" in low or "exclu" in low:
        flags |= REASON_DELETE
    if "rename old" in low or "nome antigo" in low:
        flags |= REASON_RENAME_OLD
    return flags


def parse_csv(lines: Iterable[str]) -> Iterator[Record]:
    """Saída de `fsutil usn readjournal C: csv`. Colunas: Usn, Nome, Tamanho do nome, Motivo, Data, ...

    O cabeçalho pode vir traduzido, então usamos as posições das colunas.
    """
    header_seen = False
    for row in csv.reader(lines):
        if len(row) < 5:
            continue
        if not header_seen:
            if not row[0].strip().lower().startswith("0x") and not row[0].strip().isdigit():
                header_seen = True
                continue
            header_seen = True
        yield row[1].strip(), row[3], row[4]


def run_fsutil(drive: str) -> Iterator[str]:
    enc = locale.getpreferredencoding(False)
    proc = subprocess.Popen(["fsutil", "usn", "readjournal", drive, "csv"], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    start = time.time()
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            if time.time() - start > TIMEOUT_S:
                raise TimeoutError
            yield raw.decode(enc, errors="replace").rstrip("\r\n")
    finally:
        proc.kill()
        proc.wait()


def run(ctx: Context, reader: Optional[Callable[[str], Iterable[str]]] = None) -> CheckResult:
    res = CheckResult(ID, LABEL)
    if reader is None:
        if not IS_WINDOWS or ctx.env.simulated:
            res.status, res.note = "skipped", "Disponível apenas no Windows."
            return res
        if not ctx.admin:
            res.status, res.note = "skipped", "Requer administrador (abra como administrador para incluir)."
            return res
        reader = run_fsutil
    # Só a unidade do sistema (onde ficam Usuários, Downloads e o Roblox): ler todas demoraria demais.
    system = str(ctx.env.windir)[:2] if ctx.env.windir and str(ctx.env.windir)[1:2] == ":" else "C:"
    drives = [system]
    day_first = _day_first()
    records = 0
    oldest: Optional[float] = None
    prefetch_deleted: List[float] = []
    seen = set()
    notes = []
    for drive in drives:
        try:
            for name, reason_raw, ts_raw in parse_csv(reader(drive)):
                records += 1
                flags = reason_flags(reason_raw)
                ts = parse_timestamp(ts_raw, day_first)
                if ts is not None and (oldest is None or ts < oldest):
                    oldest = ts
                if not flags & (REASON_DELETE | REASON_RENAME_OLD):
                    continue
                if name.lower().endswith(".pf") and flags & REASON_DELETE:
                    prefetch_deleted.append(ts or 0)
                    continue
                action = "apagado (USN Journal)" if flags & REASON_DELETE else "renomeado (USN Journal)"
                key = (name.lower(), action)
                if key in seen or len(res.findings) >= MAX_FINDINGS:
                    continue
                f = evaluate(ctx, ID, name, action,
                             {"arquivo": name, "unidade": drive, "data": iso(ts), "motivo": reason_raw.strip()[:80]}, ts)
                if f:
                    seen.add(key)
                    res.findings.append(f)
        except TimeoutError:
            notes.append(f"{drive}: leitura interrompida após {TIMEOUT_S}s")
        except (OSError, ValueError) as ex:
            notes.append(f"{drive}: não foi possível ler ({type(ex).__name__})")
    if len(prefetch_deleted) >= PREFETCH_WIPE_THRESHOLD:
        ts = max(prefetch_deleted) or None
        res.findings.append(ctx.finding(
            ID, ctx.rules.get("prefetch_wipe_severity", "medium"),
            f"{len(prefetch_deleted)} arquivos do Prefetch apagados recentemente",
            "Apagar o Prefetch em massa é uma forma comum de esconder rastros de programas executados. "
            "O Windows também remove alguns sozinho, mas não muitos de uma vez.",
            {"quantidade": len(prefetch_deleted), "ultimo": iso(ts)}, ts))
    res.stats = {"registros_lidos": records, "cobertura_desde": iso(oldest)}
    if records == 0:
        res.status = "partial" if not notes else "error"
        res.note = "; ".join(notes) or "Nenhum registro lido (o diário pode estar desativado)."
    elif notes:
        res.status, res.note = "partial", "; ".join(notes)
    elif oldest:
        res.note = f"O diário cobre desde {iso(oldest)}."
    return res
