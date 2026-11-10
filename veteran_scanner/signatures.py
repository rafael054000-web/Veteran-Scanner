"""Carrega assinaturas de programas, regras da liga e a lista de Fast Flags associadas a abuso."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .util import valid_severity

DATA_DIR = Path(__file__).parent / "data"

# Sufixos comuns em nomes de arquivos baixados: "Solara_v3", "solara-setup", "Wave (1).zip"...
_SUFFIX = r"(?:v?\d+[a-z0-9]*|setup|installer|bootstrapper|launcher|x64|x86|portable|main|release|latest|win|windows)*"
_STRIP_EXT = (".lnk", ".exe", ".zip", ".rar", ".7z", ".msi", ".dll", ".bat", ".pf", ".tmp", ".crdownload", ".part")
_PREFETCH_RE = re.compile(r"^(.*?)\.exe-[0-9a-f]{8}\.pf$", re.IGNORECASE)
_COPY_RE = re.compile(r"\s*\(\d+\)\s*")
_SEP_RE = re.compile(r"[\s_\-\.]+")


def normalize(name: str) -> str:
    """'Synapse X.exe' -> 'synapsex' ; 'SOLARA.EXE-1A2B3C4D.pf' -> 'solara' ; 'wave (1).zip' -> 'wave'."""
    n = name.strip().lower()
    m = _PREFETCH_RE.match(n)
    if m:
        n = m.group(1)
    changed = True
    while changed:
        changed = False
        for ext in _STRIP_EXT:
            if n.endswith(ext) and len(n) > len(ext):
                n = n[: -len(ext)]
                changed = True
    n = _COPY_RE.sub("", n)
    return _SEP_RE.sub("", n)


@dataclass
class Signature:
    id: str
    name: str
    category: str
    confidence: str
    names: List[str]
    regex: List["re.Pattern[str]"] = field(default_factory=list)
    exclude: List["re.Pattern[str]"] = field(default_factory=list)
    note: str = ""
    _compiled: List["re.Pattern[str]"] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._compiled = [re.compile(re.escape(normalize(n)) + _SUFFIX) for n in self.names if normalize(n)]

    def matches(self, raw_name: str) -> bool:
        norm = normalize(raw_name)
        if not norm:
            return False
        if any(x.search(raw_name) for x in self.exclude):
            return False
        if any(c.fullmatch(norm) for c in self._compiled):
            return True
        return any(r.fullmatch(norm) for r in self.regex)


class SignatureDB:
    def __init__(self, data: dict):
        self.version: str = str(data.get("version", "?"))
        self.signatures: List[Signature] = []
        for s in data.get("programs", []):
            self.signatures.append(
                Signature(
                    id=s["id"],
                    name=s.get("name", s["id"]),
                    category=s.get("category", "executor"),
                    confidence=s.get("confidence", "high"),
                    names=s.get("names", [s["id"]]),
                    regex=[re.compile(r) for r in s.get("regex", [])],
                    exclude=[re.compile(r, re.IGNORECASE) for r in s.get("exclude", [])],
                    note=s.get("note", ""),
                )
            )

    def match(self, raw_name: str) -> Optional[Signature]:
        for sig in self.signatures:
            if sig.matches(raw_name):
                return sig
        return None

    def merge(self, other: "SignatureDB") -> None:
        ids = {s.id for s in self.signatures}
        for s in other.signatures:
            if s.id in ids:
                self.signatures = [x for x in self.signatures if x.id != s.id]
            self.signatures.append(s)
        self.version += f"+{other.version}"


def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def load_signatures(extra: Optional[Path] = None) -> SignatureDB:
    db = SignatureDB(_read_json(DATA_DIR / "signatures.json"))
    if extra:
        db.merge(SignatureDB(_read_json(extra)))
    return db


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_rules(custom: Optional[Path] = None) -> dict:
    rules = _read_json(DATA_DIR / "rules.json")
    if custom:
        rules = _deep_merge(rules, _read_json(custom))
    return rules


def category_severity(rules: dict, category: str, confidence: str = "high") -> str:
    from .util import lower_severity

    sev = valid_severity(rules.get("category_severity", {}).get(category, "low"))
    if confidence != "high":
        sev = lower_severity(sev)
    return sev


@dataclass
class FlagRules:
    version: str
    known: Dict[str, str]  # nome -> motivo
    patterns: List["re.Pattern[str]"]


def load_flag_rules() -> FlagRules:
    data = _read_json(DATA_DIR / "fflags_abuse.json")
    known = {f["name"].lower(): f.get("reason", "") for f in data.get("flags", [])}
    pats = [re.compile(p, re.IGNORECASE) for p in data.get("suspicious_patterns", [])]
    return FlagRules(version=str(data.get("version", "?")), known=known, patterns=pats)
