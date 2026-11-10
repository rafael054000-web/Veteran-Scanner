"""Montagem, integridade e exportação do relatório."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from . import __version__
from .checks.base import CheckResult
from .util import SEVERITIES, SEVERITY_LABEL, SEVERITY_SCORE, iso, now_iso

SCHEMA = "veteran-scanner-report/1"

VERDICTS = {
    "clean": "NENHUM INDÍCIO RELEVANTE ENCONTRADO",
    "attention": "ATENÇÃO — REVISÃO HUMANA RECOMENDADA",
    "suspicious": "INDÍCIOS FORTES — REVISÃO HUMANA OBRIGATÓRIA",
}


def compute_verdict(results: List[CheckResult]) -> dict:
    counts = {s: 0 for s in SEVERITIES}
    score = 0
    for r in results:
        for f in r.findings:
            counts[f.severity] += 1
            score += SEVERITY_SCORE[f.severity]
    if counts["critical"] or counts["high"] or score >= 10:
        level = "suspicious"
    elif counts["medium"] or score >= 3:
        level = "attention"
    else:
        level = "clean"
    return {"level": level, "label": VERDICTS[level], "score": score, "counts": counts}


def scanner_fingerprint() -> Tuple[str, str]:
    """Hash do executável (versão .exe) ou dos arquivos-fonte (versão Python).

    Permite à organização conferir se a cópia usada é a oficial do GitHub.
    """
    h = hashlib.sha256()
    if getattr(sys, "frozen", False):
        try:
            with open(sys.executable, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            return "exe", h.hexdigest()
        except OSError:
            return "exe", "indisponível"
    pkg = Path(__file__).parent
    for p in sorted(pkg.rglob("*")):
        if p.is_file() and p.suffix in (".py", ".json"):
            h.update(p.relative_to(pkg).as_posix().encode())
            h.update(b"\0")
            h.update(p.read_bytes().replace(b"\r\n", b"\n"))
            h.update(b"\0")
    return "source", h.hexdigest()


def _canonical(report: dict) -> bytes:
    body = {k: v for k, v in report.items() if k != "integrity"}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def integrity_of(report: dict) -> dict:
    digest = hashlib.sha256(_canonical(report)).hexdigest()
    code = digest[:8].upper()
    return {"algorithm": "sha256", "digest": digest, "code": f"{code[:4]}-{code[4:]}"}


def build_report(
    results: List[CheckResult],
    *,
    player: str,
    event: str,
    consent: dict,
    since: Optional[float],
    admin: bool,
    allowlist_source: str,
    allowlist_count: int,
    versions: dict,
) -> dict:
    kind, fp = scanner_fingerprint()
    report = {
        "schema": SCHEMA,
        "scanner": {
            "name": "Veteran Scanner",
            "version": __version__,
            "fingerprint_kind": kind,
            "fingerprint": fp,
            **versions,
        },
        "event": event,
        "player": player,
        "created_at": now_iso(),
        "consent": consent,
        "system": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "admin": admin,
        },
        "window_since": iso(since),
        "allowlist": {"source": allowlist_source, "count": allowlist_count},
        "verdict": compute_verdict(results),
        "checks": [r.to_dict() for r in results],
    }
    report["integrity"] = integrity_of(report)
    return report


def verify_report(report: dict) -> Tuple[bool, dict]:
    expected = integrity_of(report)
    stored = report.get("integrity", {})
    return stored.get("digest") == expected["digest"], expected


def safe_filename(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._")
    return s[:40] or "jogador"


def to_text(report: dict) -> str:
    v = report["verdict"]
    lines = [
        "RELATÓRIO — VETERAN SCANNER",
        "=" * 64,
        f"Jogador:        {report['player']}",
        f"Liga:           {report['event'] or '-'}",
        f"Data:           {report['created_at']}",
        f"Período desde:  {report['window_since'] or 'não informado'}",
        f"Scanner:        v{report['scanner']['version']} ({report['scanner']['fingerprint_kind']}) "
        f"{report['scanner']['fingerprint'][:16]}…",
        f"Assinaturas:    {report['scanner'].get('signatures_version')}",
        f"Allowlist:      {report['allowlist']['source']} ({report['allowlist']['count']} flags)",
        f"Administrador:  {'sim' if report['system']['admin'] else 'não'}",
        f"Consentimento:  aceito em {report['consent']['accepted_at']} (termo v{report['consent']['terms_version']})",
        "",
        f"RESULTADO: {v['label']}",
        "Contagem: " + ", ".join(f"{SEVERITY_LABEL[s]}={v['counts'][s]}" for s in reversed(SEVERITIES)),
        f"Código de verificação: {report['integrity']['code']}",
        "",
        "Este relatório é um indício para análise humana, não uma prova automática.",
        "=" * 64,
    ]
    for chk in report["checks"]:
        lines.append("")
        status = {"ok": "OK", "partial": "PARCIAL", "skipped": "NÃO EXECUTADA", "error": "ERRO"}.get(chk["status"], chk["status"])
        lines.append(f"## {chk['label']} — {status}")
        if chk["note"]:
            lines.append(f"   Obs.: {chk['note']}")
        if not chk["findings"] and chk["status"] != "skipped":
            lines.append("   Nenhum achado.")
        order = {s: i for i, s in enumerate(reversed(SEVERITIES))}
        for f in sorted(chk["findings"], key=lambda x: order[x["severity"]]):
            tag = f"[{SEVERITY_LABEL[f['severity']]}]"
            when = f" ({f['timestamp']})" if f["timestamp"] else ""
            old = " [anterior ao período]" if f["before_window"] else ""
            lines.append(f" {tag:<10}{f['title']}{when}{old}")
            if f["detail"]:
                lines.append(f"            {f['detail']}")
            for k, val in f["evidence"].items():
                if isinstance(val, list):
                    shown = ", ".join(map(str, val[:40])) + (" …" if len(val) > 40 else "")
                    lines.append(f"            - {k}: {shown}")
                elif val not in (None, ""):
                    lines.append(f"            - {k}: {val}")
    lines.append("")
    return "\n".join(lines)
