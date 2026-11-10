"""Estruturas compartilhadas pelas verificações."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from ..signatures import FlagRules, Signature, SignatureDB, category_severity
from ..util import Env, Sanitizer, iso, lower_severity, valid_severity


@dataclass
class Finding:
    check: str
    severity: str
    title: str
    detail: str = ""
    evidence: Dict = field(default_factory=dict)
    timestamp: Optional[float] = None
    before_window: bool = False

    def to_dict(self) -> dict:
        return {
            "check": self.check,
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "evidence": self.evidence,
            "timestamp": iso(self.timestamp),
            "before_window": self.before_window,
        }


@dataclass
class CheckResult:
    id: str
    label: str
    status: str = "ok"  # ok | partial | skipped | error
    note: str = ""
    findings: List[Finding] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "status": self.status,
            "note": self.note,
            "stats": self.stats,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class Context:
    env: Env
    sanitize: Sanitizer
    signatures: SignatureDB
    flag_rules: FlagRules
    rules: dict
    allowlist: Optional[Set[str]] = None
    allowlist_source: str = "indisponível"
    since: Optional[float] = None
    admin: bool = False

    def finding(
        self,
        check: str,
        severity: str,
        title: str,
        detail: str = "",
        evidence: Optional[dict] = None,
        timestamp: Optional[float] = None,
    ) -> Finding:
        sev = valid_severity(severity)
        before = False
        if self.since is not None and timestamp is not None and timestamp < self.since:
            before = True
            if self.rules.get("since_downgrade", True):
                sev = lower_severity(sev)
        return Finding(check, sev, title, detail, evidence or {}, timestamp, before)

    def signature_finding(
        self,
        check: str,
        sig: Signature,
        where: str,
        evidence: dict,
        timestamp: Optional[float] = None,
        severity_override: Optional[str] = None,
    ) -> Finding:
        sev = severity_override or category_severity(self.rules, sig.category, sig.confidence)
        detail = f"Categoria: {CATEGORY_LABEL.get(sig.category, sig.category)}."
        if sig.confidence != "high":
            detail += " Nome genérico: confirme manualmente."
        if sig.note:
            detail += " " + sig.note
        ev = {"assinatura": sig.id, "categoria": sig.category, **evidence}
        return self.finding(check, sev, f"{sig.name} — {where}", detail, ev, timestamp)


CATEGORY_LABEL = {
    "executor": "executor de scripts",
    "injector": "injetor de DLL",
    "memory_editor": "editor de memória",
    "dual_use": "ferramenta de sistema (uso duplo)",
    "macro": "macro / auto clicker",
    "bootstrapper": "bootstrapper (permite editar Fast Flags)",
    "fps_unlocker": "desbloqueador de FPS",
    "cleaner": "limpador de rastros",
}
