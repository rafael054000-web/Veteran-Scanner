# FairScan

Scanner **open source, com consentimento e somente leitura** para campeonatos comunitários de Roblox.
Ele procura indícios de **Fast Flags proibidas**, **executores de script**, **injetores** e outros programas
vetados pelo regulamento. O resultado é um relatório que a organização analisa antes de decidir qualquer coisa.

> ⚖️ O FairScan **não acusa ninguém sozinho**. Ele junta indícios para uma **análise humana**, e o jogador
> sempre tem direito de ver as evidências e de se defender.

---

## Princípios

| | |
|---|---|
| ✅ **Consentimento** | Nada é lido antes de o jogador digitar `ACEITO`. Menores de 18 anos precisam confirmar a autorização de um responsável. |
| ✅ **Somente leitura** | Não modifica, move nem apaga nada. |
| ✅ **Não toca no Roblox** | Não lê memória, não injeta e não interage com o processo do jogo, então não interfere no anti-cheat. |
| ✅ **Privacidade** | Lê só **nomes** de arquivos/pastas (não abre seus documentos). O relatório traz apenas os achados, com o nome de usuário removido dos caminhos. |
| ✅ **Sem envio automático** | O relatório fica no PC do jogador, e ele decide se envia. A única conexão é o download da allowlist **pública** de Fast Flags do Roblox (`--offline` desativa). |
| ✅ **Auditável** | Python puro, sem dependências. Qualquer pessoa pode ler o código. |

## O que é verificado

| Verificação | O que olha | Observação |
|---|---|---|
| **Fast Flags** | `ClientAppSettings.json` do Roblox e de bootstrappers (Bloxstrap, Fishstrap, Voidstrap…) | Compara com a **allowlist oficial**: desde 29/09/2025 o Roblox ignora flags fora dela. Também destaca flags associadas a desync/hitbox. |
| **Instalação do Roblox** | Nomes de arquivos nas pastas de versão | Procura DLLs "proxy" (`dxgi.dll`, `version.dll`…), técnica comum de injeção. |
| **Arquivos e pastas** | Nomes em Downloads, Área de Trabalho, Documentos, AppData, Temp, Arquivos de Programas | Também procura a estrutura típica de executor (`autoexec` + `workspace`/`scripts`). |
| **Processos** | Programas abertos agora (`tasklist`) | Um achado aqui pesa mais. |
| **Prefetch** | `C:\Windows\Prefetch` | Programas executados recentemente. Requer administrador. |
| **Registro** | MuiCache, UserAssist, Compatibility Assistant, BAM, `HKCU\Software` | Rastros de execução que continuam mesmo depois de apagar o programa. O BAM requer administrador. |
| **Itens recentes** | Atalhos em `Recent` | |
| **Logs do Roblox** | `%LOCALAPPDATA%\Roblox\logs` | Linha do tempo das sessões e menções a executores. O conteúdo não vai para o relatório. |

Cada achado tem uma severidade (`INFO`, `BAIXA`, `MÉDIA`, `ALTA`, `CRÍTICA`) e o relatório termina com um destes resultados:

- **NENHUM INDÍCIO RELEVANTE ENCONTRADO**
- **ATENÇÃO — REVISÃO HUMANA RECOMENDADA**
- **INDÍCIOS FORTES — REVISÃO HUMANA OBRIGATÓRIA**

---

## Para jogadores

### Opção 1 — Executável (mais fácil)
1. Baixe o `FairScan.exe` **somente** da página [Releases](../../releases) deste repositório.
2. Confira se o SHA256 do arquivo bate com o publicado na release (veja o [guia do organizador](docs/GUIA_DO_ORGANIZADOR.md#3-conferir-se-a-cópia-é-oficial)).
3. Dê dois cliques. Para uma verificação completa, use **botão direito → Executar como administrador**.
4. Leia o termo, digite `ACEITO` e siga as instruções.
5. Envie o arquivo `fairscan_<nick>_<data>.json` para a organização.

> O Windows pode mostrar o aviso do SmartScreen porque o executável não é assinado digitalmente.
> É por isso que o código e o build são públicos: dá para conferir tudo.

### Opção 2 — Pelo terminal (Python 3.9+)
```bat
git clone https://github.com/SEU_USUARIO/fairscan.git
cd fairscan
python -m fairscan --event "Nome do Campeonato" --since 2026-11-01
```
Ou dê dois cliques em `executar.bat`.

### Opções úteis
```
python -m fairscan [opções]
  --player NICK            seu nick (senão será perguntado)
  --event NOME             nome do campeonato
  --since AAAA-MM-DD       início do campeonato: achados mais antigos pesam menos
  --output PASTA           onde salvar o relatório
  --offline                não baixa a allowlist oficial de Fast Flags
  --allowlist-file ARQ     usa uma allowlist fornecida pela organização
  --rules ARQ              regras específicas do campeonato (JSON)
  --signatures ARQ         assinaturas extras (JSON)

python -m fairscan verify relatorio.json --code AB12-CD34   # organizadores
python -m fairscan signatures                              # lista o que é detectado
python -m fairscan fingerprint                             # impressão digital desta cópia
```

Códigos de saída: `0` limpo · `1` atenção · `2` indícios fortes · `3` erro · `4` consentimento recusado.

---

## Para organizadores

Leia o **[Guia do Organizador](docs/GUIA_DO_ORGANIZADOR.md)**. Ele cobre o procedimento recomendado (verificação ao vivo
em chamada), como interpretar os achados, falsos positivos, direito de defesa e LGPD. Também há modelos prontos:

- [Termo de consentimento](docs/TERMO_DE_CONSENTIMENTO.md) para o formulário de inscrição
- [Trecho de regulamento](docs/REGULAMENTO_MODELO.md)
- [Exemplo de regras personalizadas](docs/exemplo_regras_campeonato.json)

## Limitações (leia!)

- **Nenhum scanner é infalível.** Quem apaga rastros com cuidado, usa outro PC ou renomeia programas pode passar.
  Por isso o FairScan é uma ferramenta de apoio, não a única prova.
- **Falsos positivos existem.** Nomes genéricos ("Wave", "Celery", "Velocity") podem ser outros softwares. Esses têm
  severidade reduzida e o relatório avisa "confirme manualmente".
- **Um relatório pode ser forjado** por quem modificar o código. Por isso existe o **código de verificação**, mostrado
  na tela durante a chamada, e a **impressão digital** do scanner, comparada com a release oficial.
- A lista de executores muda o tempo todo. Contribuições são bem-vindas (veja [CONTRIBUTING.md](CONTRIBUTING.md)).

## Testes
```bash
python -m unittest discover -s tests -v
```
Os testes usam uma árvore de Windows simulada e rodam em qualquer sistema.

## Aviso legal
Projeto comunitário, sem afiliação com a Roblox Corporation. "Roblox" é marca da Roblox Corporation.
O uso deve ser sempre **com consentimento** do jogador e de acordo com a LGPD e as leis locais. Veja
[PRIVACIDADE.md](PRIVACIDADE.md). Isto não é aconselhamento jurídico.

Licença: [MIT](LICENSE).
