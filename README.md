# VETERAN SCANNER

Scanner **open source, com consentimento e somente leitura** para ligas comunitárias de Roblox.
Ele procura indícios de **Fast Flags proibidas**, **executores de script**, **injetores** e outros programas
vetados pelo regulamento. O resultado é um relatório que a organização analisa antes de decidir qualquer coisa.

> ⚖️ O Veteran Scanner **não acusa ninguém sozinho**. Ele junta indícios para uma **análise humana**, e o jogador
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
| **Fast Flags** | `ClientAppSettings.json` do Roblox e de bootstrappers (Bloxstrap, Fishstrap, Voidstrap…), além de `IxpSettings.json`, perfis e backups | Compara com a **allowlist oficial**: desde 29/09/2025 o Roblox ignora flags fora dela. Também destaca flags associadas a desync/hitbox. |
| **Instalação do Roblox** | Nomes de arquivos nas pastas de versão | Procura DLLs "proxy" (`dxgi.dll`, `version.dll`…), técnica comum de injeção. |
| **Arquivos e pastas** | Nomes em Downloads, Área de Trabalho, Documentos, AppData, Temp, Arquivos de Programas | Também procura a estrutura típica de executor (`autoexec` + `workspace`/`scripts`). |
| **Processos** | Programas abertos agora (`tasklist`) | Um achado aqui pesa mais. |
| **Prefetch** | `C:\Windows\Prefetch` | Programas executados recentemente. Requer administrador. |
| **Registro** | MuiCache, UserAssist, Compatibility Assistant, BAM, `HKCU\Software` | Rastros de execução que continuam mesmo depois de apagar o programa. O BAM requer administrador. |
| **Itens recentes** | Atalhos em `Recent` | |
| **Lixeira** | Nome original e data dos itens apagados | Lê só o índice (`$I`), nunca o conteúdo. |
| **Arquivos apagados/renomeados (USN Journal)** | Diário do NTFS da unidade do sistema | Mostra executores, arquivos de Fast Flags e pastas `autoexec` apagados ou renomeados nos últimos dias, mesmo com a Lixeira esvaziada. Também detecta limpeza em massa do Prefetch. Requer administrador. Ideal para verificações no mesmo dia da partida. |
| **Listas de Fast Flags guardadas** | `.json`/`.txt` de até 1 MB em Downloads, Área de Trabalho e Documentos | Encontra listas de flags (ex.: para colar no Bloxstrap). O relatório mostra só as flags. |
| **Logs do Roblox** | `%LOCALAPPDATA%\Roblox\logs` | Linha do tempo das sessões e menções a executores. O conteúdo não vai para o relatório. |

Cada achado tem uma severidade (`INFO`, `BAIXA`, `MÉDIA`, `ALTA`, `CRÍTICA`) e o relatório termina com um destes resultados:

- **NENHUM INDÍCIO RELEVANTE ENCONTRADO**
- **ATENÇÃO — REVISÃO HUMANA RECOMENDADA**
- **INDÍCIOS FORTES — REVISÃO HUMANA OBRIGATÓRIA**

---

## Para jogadores

**Não precisa instalar Python nem nada.**

### Opção 1 — Um comando, sem baixar nada (recomendada)
1. Abra o menu Iniciar, digite **PowerShell**, clique com o botão direito e escolha **Executar como administrador**.
2. Cole este comando e aperte Enter:
   ```powershell
   irm https://raw.githubusercontent.com/rafael054000-web/Veteran-Scanner/main/iniciar.ps1 | iex
   ```
3. O scanner é baixado para uma pasta temporária, tem o SHA256 conferido e abre. No final, ele é apagado sozinho, e o
   relatório fica na **Área de Trabalho**.

> ⚠️ Só cole comandos vindos do canal oficial da liga. Você pode ler o [`iniciar.ps1`](iniciar.ps1) antes de rodar.

### Opção 2 — Baixar só o executável
1. Baixe o **[VeteranScanner.exe](https://github.com/rafael054000-web/Veteran-Scanner/releases/latest/download/VeteranScanner.exe)**
   (sempre a versão mais recente, gerada automaticamente pelo GitHub a partir deste código).
2. Clique com o **botão direito → Executar como administrador** (com dois cliques também funciona, mas a verificação fica menos completa).
3. Leia o termo, digite `ACEITO` e siga as instruções.
4. Envie o arquivo `veteran_<nick>_<data>.json`, que aparece na mesma pasta, para a organização.

### Opção 3 — Baixar o projeto
1. Na página do repositório, clique em **Code → Download ZIP** e extraia.
2. Dê dois cliques em **`executar.bat`**. Ele baixa o `VeteranScanner.exe` oficial (ou atualiza, se já tiver),
   confere o SHA256 e abre o scanner.

> O Windows pode mostrar o aviso do SmartScreen ("O Windows protegeu o computador") porque o executável não é
> assinado digitalmente. Clique em **Mais informações → Executar assim mesmo**. O código e o processo de build são
> públicos justamente para qualquer um poder conferir.

### Opção 4 — Pelo Python (desenvolvedores)
```bat
git clone https://github.com/rafael054000-web/Veteran-Scanner.git
cd Veteran-Scanner
python -m veteran_scanner --event "Nome da Liga" --since 2026-11-01
```

### Opções úteis
```
VeteranScanner.exe [opções]        (ou: python -m veteran_scanner [opções])
  --player NICK            seu nick (senão será perguntado)
  --event NOME             nome da liga
  --since AAAA-MM-DD       início da liga: achados mais antigos pesam menos
  --output PASTA           onde salvar o relatório
  --offline                não baixa a allowlist oficial de Fast Flags
  --allowlist-file ARQ     usa uma allowlist fornecida pela organização
  --rules ARQ              regras específicas da liga (JSON)
  --signatures ARQ         assinaturas extras (JSON)

VeteranScanner.exe verify relatorio.json --code AB12-CD34   # organizadores
VeteranScanner.exe signatures                              # lista o que é detectado
VeteranScanner.exe fingerprint                             # impressão digital desta cópia
```

Códigos de saída: `0` limpo · `1` atenção · `2` indícios fortes · `3` erro · `4` consentimento recusado.

---

## Para organizadores

Leia o **[Guia do Organizador](docs/GUIA_DO_ORGANIZADOR.md)**. Ele cobre o procedimento recomendado (verificação ao vivo
em chamada), como interpretar os achados, falsos positivos, direito de defesa e LGPD. Também há modelos prontos:

- [Termo de consentimento](docs/TERMO_DE_CONSENTIMENTO.md) para o formulário de inscrição
- [Trecho de regulamento](docs/REGULAMENTO_MODELO.md)
- [Exemplo de regras personalizadas](docs/exemplo_regras_liga.json)

## Limitações (leia!)

- **Nenhum scanner é infalível.** Quem apaga rastros com cuidado, usa outro PC ou renomeia programas pode passar.
  Por isso o Veteran Scanner é uma ferramenta de apoio, não a única prova.
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
