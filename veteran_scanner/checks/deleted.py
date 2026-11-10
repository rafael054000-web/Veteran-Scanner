"""Regras comuns para itens apagados ou renomeados (Lixeira e USN Journal)."""

from __future__ import annotations

from typing import Optional

from .base import Context, Finding

FFLAG_FILES = {"clientappsettings.json", "ixpsettings.json"}


def evaluate(ctx: Context, check: str, name: str, action: str, evidence: dict,
             timestamp: Optional[float]) -> Optional[Finding]:
    """Decide se um arquivo apagado/renomeado é relevante. `action` ex.: 'apagado', 'na Lixeira'."""
    low = name.lower()
    if low in FFLAG_FILES:
        return ctx.finding(
            check, ctx.rules.get("deleted_fflag_file_severity", "medium"),
            f"Arquivo de Fast Flags {action}: {name}",
            "Apagar o arquivo de Fast Flags pouco antes da verificação pode indicar tentativa de esconder flags. "
            "Também acontece quando o Roblox atualiza ou o jogador reinstala; compare a data com a da partida.",
            evidence, timestamp)
    if low == "autoexec":
        return ctx.finding(
            check, ctx.rules.get("executor_folder_layout_severity", "high"),
            f"Pasta 'autoexec' {action}",
            "Pasta típica de executores de script.", evidence, timestamp)
    sig = ctx.signatures.match(name)
    if sig and sig.category not in ("bootstrapper", "cleaner", "fps_unlocker", "dual_use"):
        return ctx.signature_finding(check, sig, action, evidence, timestamp)
    return None
