"""Termo de consentimento exibido antes de qualquer verificação."""

from __future__ import annotations

from typing import Optional

from . import TERMS_VERSION
from .ui import UI
from .util import now_iso

TERMS = f"""\
TERMO DE CONSENTIMENTO — FairScan (versão {TERMS_VERSION})

Este programa verifica o seu computador em busca de sinais de programas e configurações
proibidos pelo regulamento do campeonato (executores, injetores, Fast Flags etc.).

O QUE ELE LÊ (somente leitura):
  • Arquivos de Fast Flags do Roblox e de bootstrappers (ClientAppSettings.json)
  • NOMES de arquivos e pastas em Downloads, Área de Trabalho, Documentos, AppData e Temp
  • Arquivos dentro da pasta de instalação do Roblox (só os nomes)
  • Lista de processos abertos agora
  • Rastros de execução do Windows: Prefetch, Itens Recentes e registro
    (MuiCache, UserAssist, Compatibility Assistant, BAM)
  • Logs do Roblox (o conteúdo NÃO vai para o relatório, só termos encontrados)

O QUE ELE NÃO FAZ:
  • Não lê a memória nem interage com o processo do Roblox
  • Não abre seus documentos, fotos, senhas, cookies ou conversas
  • Não modifica, move nem apaga nada
  • Não envia nada pela internet. A única conexão é para baixar a lista PÚBLICA de
    Fast Flags permitidas do servidor do Roblox (use --offline para desativar)

RELATÓRIO:
  • Fica salvo só no seu computador. VOCÊ decide se envia para a organização.
  • Contém apenas os achados, com o seu nome de usuário do Windows removido dos caminhos.
  • O resultado é um INDÍCIO para análise humana, não uma acusação automática.
    Você tem direito de ver as evidências e de se explicar ou recorrer.
  • Você pode pedir à organização que apague o seu relatório depois do campeonato.

Se você não aceitar, nada será verificado. Recusar pode impedir a participação no
campeonato, conforme o regulamento.
"""


def ask_consent(ui: UI, input_fn=input) -> Optional[dict]:
    ui.title("Antes de começar")
    ui.print(TERMS)
    ui.rule()
    ans = ui.ask('Para aceitar e continuar, digite ACEITO (ou Enter para sair): ', input_fn)
    if ans.strip().upper() != "ACEITO":
        return None
    adult = ui.yes_no("Você tem 18 anos ou mais?", default=False, input_fn=input_fn)
    guardian = None
    if not adult:
        guardian = ui.yes_no("Seu pai, mãe ou responsável autorizou esta verificação?", default=False, input_fn=input_fn)
        if not guardian:
            ui.print(ui.c("\nPara menores de 18 anos é necessária a autorização de um responsável. "
                          "Peça a ele e rode o scanner de novo.", "yellow"))
            return None
    return {
        "accepted": True,
        "terms_version": TERMS_VERSION,
        "accepted_at": now_iso(),
        "adult_declared": adult,
        "guardian_authorized_declared": guardian,
    }
