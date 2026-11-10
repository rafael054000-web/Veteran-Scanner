"""Fast Flags: procura ClientAppSettings.json do Roblox e de bootstrappers (Bloxstrap, Fishstrap...)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Tuple

from ..allowlist import FLAG_RE, strip_prefix
from ..util import file_times, newest, walk_limited
from .base import CheckResult, Context

ID, LABEL = "fflags", "Fast Flags (Roblox e bootstrappers)"
EXTRA_BOOTSTRAPPERS = {"roblox", "rbxfpsunlocker"}
SKIP = {"logs", "http", "rbx-storage", "localstorage", "downloads", "sounds", "textures", "content", "platformcontent", "extracontent", "shaders"}
MAX_LISTED = 300


MAX_OTHER_JSON = 2_000_000


def candidate_files(ctx: Context) -> List[Tuple[Path, bool]]:
    """Retorna (arquivo, ativo). Ativo = ClientAppSettings.json; os outros são JSONs de configuração
    do Roblox (ex.: IxpSettings.json) e dos bootstrappers (perfis, backups), onde só procuramos flags de abuso."""
    env = ctx.env
    roots: List[Tuple[Path, bool]] = []  # (raiz, é bootstrapper)
    if env.local_appdata and env.local_appdata.is_dir():
        try:
            for e in os.scandir(env.local_appdata):
                n = e.name.lower()
                if e.is_dir() and (n.endswith("strap") or n in EXTRA_BOOTSTRAPPERS):
                    roots.append((Path(e.path), n.endswith("strap")))
        except OSError:
            pass
    for pf in env.program_files:
        roots.append((pf / "Roblox", False))
    files = {}
    for r, is_strap in roots:
        if not r.is_dir():
            continue
        for e, _ in walk_limited(r, max_depth=5, max_entries=30000, skip_dirs=SKIP):
            name = e.name.lower()
            if not name.endswith(".json"):
                continue
            try:
                if not e.is_file():
                    continue
                size = e.stat().st_size
            except OSError:
                continue
            p = Path(e.path)
            if name == "clientappsettings.json":
                files[str(p).lower()] = (p, True)
            elif size <= MAX_OTHER_JSON and (is_strap or p.parent.name.lower() == "clientsettings"):
                files.setdefault(str(p).lower(), (p, False))
    return sorted(files.values(), key=lambda x: str(x[0]).lower())


def _load(path: Path):
    raw = path.read_bytes()[:3_000_000]
    return json.loads(raw.decode("utf-8-sig", errors="replace"))


def run(ctx: Context) -> CheckResult:
    res = CheckResult(ID, LABEL)
    fr = ctx.rules.get("fflags", {})
    files = candidate_files(ctx)
    res.stats = {"arquivos_ativos": sum(1 for _, a in files if a), "outros_json": sum(1 for _, a in files if not a), "allowlist": ctx.allowlist_source,
                 "allowlist_tamanho": len(ctx.allowlist) if ctx.allowlist else 0}
    if ctx.allowlist is None and any(a for _, a in files):
        res.note = "Allowlist oficial indisponível: não foi possível dizer quais flags têm efeito real."

    for path, active in files:
        created, modified = file_times(path)
        ts = newest(created, modified)
        where = ctx.sanitize.path(path)
        try:
            data = _load(path)
        except (OSError, ValueError) as ex:
            if not active:
                continue
            res.findings.append(ctx.finding(ID, "low", "Arquivo de Fast Flags ilegível ou malformado",
                                            f"Não foi possível ler o JSON ({type(ex).__name__}). Pode ser corrupção ou edição manual.",
                                            {"arquivo": where}, ts))
            continue
        if not active:
            _scan_other(ctx, res, data, where, ts)
            continue
        if not isinstance(data, dict) or not data:
            res.findings.append(ctx.finding(ID, "info", "Arquivo de Fast Flags vazio", "Nenhuma flag definida.",
                                            {"arquivo": where}, ts))
            continue

        allowed, unlisted, unknown, abuse, pattern_hits, not_flags = [], [], [], [], [], []
        for key, value in data.items():
            key = str(key)
            val = str(value)[:200]
            if not FLAG_RE.match(key):
                not_flags.append(key)
                continue
            low = key.lower()
            if low in ctx.flag_rules.known:
                abuse.append((key, val, ctx.flag_rules.known[low]))
            elif any(p.search(key) for p in ctx.flag_rules.patterns):
                pattern_hits.append((key, val))
            if ctx.allowlist is None:
                unknown.append(key)
            elif strip_prefix(key) in ctx.allowlist:
                allowed.append(key)
            else:
                unlisted.append(key)

        for key, val, reason in abuse:
            efeito = _effect_text(ctx, key)
            res.findings.append(ctx.finding(ID, fr.get("known_abuse_severity", "high"),
                                            f"Fast Flag associada a vantagem: {key}",
                                            f"{reason} {efeito}",
                                            {"arquivo": where, "flag": key, "valor": val}, ts))
        for key, val in pattern_hits:
            res.findings.append(ctx.finding(ID, fr.get("suspicious_pattern_severity", "medium"),
                                            f"Fast Flag com nome suspeito: {key}",
                                            f"O nome sugere relação com rede/física/hitbox. {_effect_text(ctx, key)}",
                                            {"arquivo": where, "flag": key, "valor": val}, ts))
        if unlisted:
            res.findings.append(ctx.finding(
                ID, fr.get("unlisted_severity", "low"),
                f"{len(unlisted)} Fast Flag(s) fora da allowlist oficial",
                "O cliente atual do Roblox ignora essas flags (sem efeito), mas o regulamento da liga pode proibir a presença delas.",
                {"arquivo": where, "flags": unlisted[:MAX_LISTED], "total": len(unlisted)}, ts))
        if unknown:
            res.findings.append(ctx.finding(
                ID, fr.get("unknown_allowlist_severity", "low"),
                f"{len(unknown)} Fast Flag(s) definida(s) — efeito não verificado",
                "Sem a allowlist oficial não dá para saber quais têm efeito. Revise a lista manualmente.",
                {"arquivo": where, "flags": unknown[:MAX_LISTED], "total": len(unknown)}, ts))
        if allowed:
            res.findings.append(ctx.finding(
                ID, fr.get("allowlisted_severity", "info"),
                f"{len(allowed)} Fast Flag(s) permitida(s) pela allowlist oficial",
                "Essas flags são aceitas pelo próprio Roblox.",
                {"arquivo": where, "flags": allowed[:MAX_LISTED], "total": len(allowed)}, ts))
        if not_flags:
            res.findings.append(ctx.finding(ID, "info", f"{len(not_flags)} chave(s) que não parecem Fast Flags",
                                            "Chaves fora do padrão FFlag/FInt/FString/FLog.",
                                            {"arquivo": where, "chaves": not_flags[:50]}, ts))
    return res


def _scan_other(ctx: Context, res: CheckResult, data, where: str, ts) -> None:
    """JSON que não é o arquivo ativo: só interessa se tiver flags associadas a abuso."""
    from ..allowlist import extract_flag_names

    fr = ctx.rules.get("fflags", {})
    for key in sorted(extract_flag_names(data)):
        low = key.lower()
        if low in ctx.flag_rules.known:
            sev, title, why = fr.get("known_abuse_severity", "high"), f"Fast Flag associada a vantagem em {_short(where)}: {key}", ctx.flag_rules.known[low]
        elif any(p.search(key) for p in ctx.flag_rules.patterns):
            sev, title, why = fr.get("suspicious_pattern_severity", "medium"), f"Fast Flag com nome suspeito em {_short(where)}: {key}", "O nome sugere relação com rede/física/hitbox."
        else:
            continue
        res.findings.append(ctx.finding(
            ID, sev, title,
            f"{why} Encontrada num arquivo de configuração do Roblox/bootstrapper (perfil, backup ou cache). "
            "Editar arquivos de cache do Roblox também é considerado modificação do cliente.",
            {"arquivo": where, "flag": key}, ts))


def _short(where: str) -> str:
    return where.replace("\\", "/").rsplit("/", 1)[-1]


def _effect_text(ctx: Context, key: str) -> str:
    if ctx.allowlist is None:
        return "Não foi possível verificar se ela tem efeito (allowlist indisponível)."
    if strip_prefix(key) in ctx.allowlist:
        return "Ela ESTÁ na allowlist oficial, então tem efeito no cliente."
    return ("Ela NÃO está na allowlist oficial, então o cliente a ignora; "
            "só teria efeito se aplicada por um programa externo.")
