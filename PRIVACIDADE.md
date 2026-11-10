# Privacidade

O Veteran Scanner foi feito para coletar **o mínimo necessário**.

## O que é lido
- Arquivos `ClientAppSettings.json` (Fast Flags) do Roblox e de bootstrappers. Os nomes e valores das flags vão para
  o relatório.
- **Nomes** de arquivos e pastas em locais específicos, com profundidade limitada. O conteúdo de documentos, fotos e
  outros arquivos pessoais **nunca** é aberto.
- Nomes de processos em execução.
- Rastros de execução do Windows (Prefetch, Itens Recentes, registro). Só os itens que batem com assinaturas
  conhecidas vão para o relatório.
- Arquivos `.json`/`.txt` de até 1 MB em Downloads, Área de Trabalho e Documentos, só para encontrar listas de Fast
  Flags. Apenas os nomes das flags encontradas vão para o relatório.
- Índice da Lixeira (`$I`): nome original e data da exclusão. O conteúdo apagado não é lido nem recuperado.
- Diário do NTFS (USN Journal) da unidade do sistema, via `fsutil`: nomes de arquivos apagados ou renomeados. Só os
  itens que batem com assinaturas, arquivos de Fast Flags ou limpeza do Prefetch vão para o relatório.
- Logs do Roblox, procurando nomes de programas conhecidos. Só o termo encontrado e o nome do arquivo de log vão para o
  relatório, nunca o conteúdo.

## O que vai para o relatório
- Nick e liga informados pelo jogador.
- Data do consentimento, versão do termo e declaração de idade/autorização.
- Sistema operacional e se rodou como administrador.
- **Apenas os achados**, com caminhos em que o nome de usuário do Windows é trocado por `%USERPROFILE%` / `<usuario>`.

## O que NÃO vai
- Lista completa de arquivos, programas ou processos.
- Nome do computador, endereço IP, identificadores de hardware, contas, senhas ou cookies.

## Rede
A única conexão é um `GET` para `clientsettingscdn.roblox.com`, que baixa a allowlist **pública** de Fast Flags.
Nenhum dado do jogador é enviado. Use `--offline` para desativar.

## Armazenamento
O relatório é salvo **apenas** na pasta escolhida, no computador do jogador. Enviar ou não é decisão dele.
Organizadores devem seguir a seção de LGPD do [Guia do Organizador](docs/GUIA_DO_ORGANIZADOR.md#7-dados-pessoais-lgpd).
