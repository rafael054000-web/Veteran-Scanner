# Guia do Organizador

Este guia explica como usar o Veteran Scanner de forma **justa, segura e de acordo com a LGPD** numa liga comunitária.

## 1. Antes da liga

1. **Coloque as regras no regulamento.** Use o [modelo](REGULAMENTO_MODELO.md). Diga claramente:
   - o que é proibido (quais Fast Flags, executores, macros…);
   - que a verificação pode ser pedida e como ela funciona;
   - que recusar a verificação pode impedir a participação;
   - quais são as punições e como recorrer.
2. **Colete o consentimento na inscrição** com o [termo](TERMO_DE_CONSENTIMENTO.md). O scanner pede o consentimento
   de novo antes de rodar.
3. **Fixe a versão do scanner.** A release `latest` muda a cada atualização do código. Para a liga, crie uma tag
   (`git tag v1.0.0 && git push --tags`): o GitHub gera uma release fixa. Divulgue o link dela e o SHA256 do `.exe`.
4. *(Opcional)* **Ajuste as regras** com um arquivo JSON próprio (veja [exemplo](exemplo_regras_liga.json)) e
   distribua junto: `--rules regras_liga.json`.
5. *(Opcional)* **Fixe a allowlist.** Salve a allowlist oficial do dia e distribua com `--allowlist-file`, para todos
   serem avaliados com a mesma lista.

## 2. Procedimento recomendado: verificação ao vivo

A forma mais confiável é em **chamada com compartilhamento de tela** (Discord, por exemplo):

1. O jogador compartilha a tela inteira.
2. Baixa o `VeteranScanner.exe` da release fixada pela liga **durante a chamada**, ou mostra o SHA256 da cópia que já tem
   (`certutil -hashfile VeteranScanner.exe SHA256`).
3. Executa como administrador. O jeito mais fácil é o comando de uma linha do README (`irm ... | iex`) num
   PowerShell aberto como administrador. Sem administrador, o USN Journal, o Prefetch e o BAM ficam de fora, e eles
   são os mais importantes para verificações no mesmo dia da partida.
4. **Anote o código de verificação** (ex.: `3558-15DA`) mostrado no final.
5. O jogador envia o `.json`. Você confere:
   ```
   VeteranScanner.exe verify veteran_Nick_20261110-180231.json --code 3558-15DA
   ```
   Se o código não conferir, o arquivo foi alterado depois da chamada.
6. Compare a **impressão digital** mostrada pelo `verify` com o SHA256 da release fixada. Se for diferente, o jogador
   usou uma cópia modificada.

Sem a chamada ao vivo, o relatório ainda serve como indício, mas é mais fácil de manipular.

## 3. Conferir se a cópia é oficial

- O workflow `release.yml` gera o `.exe` no GitHub Actions a partir do código público, testa o executável num Windows
  e publica `SHA256SUMS.txt` junto. Isso acontece a cada atualização (release `latest`) e a cada tag `v*` (release fixa).
- No relatório, `scanner.fingerprint` deve ser igual a esse SHA256 (quando `fingerprint_kind` = `exe`).
- Se o jogador rodou pelo Python (`fingerprint_kind` = `source`), a impressão é o hash dos arquivos-fonte. Compare
  com o resultado de `python -m veteran_scanner fingerprint` numa cópia limpa da mesma tag, baixada por você.

## 4. Como interpretar os achados

| Achado | Peso | Como avaliar |
|---|---|---|
| Executor **em execução agora** | Muito forte | Praticamente conclusivo, mas confira o nome do processo. |
| Prefetch / BAM / UserAssist de executor | Forte | Mostra que o programa **foi executado**. Veja a data em relação à liga. |
| Estrutura `autoexec` + `workspace` | Forte | Típica de executor, mesmo com o programa renomeado. |
| Arquivo/pasta com nome de executor | Médio a forte | Pode ser só um download. Veja datas e caminho. |
| Executor ou `autoexec` **apagado/renomeado** (USN Journal ou Lixeira) | Forte | Principalmente se a data for entre a partida e a verificação. |
| `ClientAppSettings.json` apagado (USN Journal ou Lixeira) | Médio | Pode ser tentativa de esconder flags, mas também acontece quando o Roblox atualiza. Compare com a data da partida e com as pastas de versão. |
| Prefetch apagado em massa | Médio | Forma comum de esconder rastros. |
| Flag de vantagem em `IxpSettings.json`/perfil de bootstrapper | Forte | Editar arquivos de cache do Roblox é modificação do cliente. |
| Lista de flags guardada com flag de vantagem | Médio | Mostra acesso às flags, não prova uso. |
| Fast Flag associada a abuso **na allowlist** | Forte | Tem efeito real no jogo. |
| Fast Flag associada a abuso **fora da allowlist** | Médio | O Roblox ignora; só teria efeito com programa externo. Mostra intenção. |
| Flags fora da allowlist (comuns) | Fraco | Geralmente sobra de configurações antigas do Bloxstrap. Decida pelo regulamento. |
| DLL proxy na pasta do Roblox | Médio | Pode ser ReShade/overlay. Pergunte. |
| Menção em log | Fraco | Só complementa outros indícios. |
| Logs ausentes / Prefetch vazio | Fraco | Pode ser limpeza de rastros ou só configuração do sistema. |
| Bootstrapper, limpador, FPS unlocker | Informativo | Não são proibidos por padrão. |

**Datas importam.** Use `--since`. Achados anteriores à liga aparecem marcados como "anterior ao período", com
severidade reduzida. Ter usado um executor meses atrás, em outro jogo, é diferente de usar durante a liga. O
regulamento deve dizer como tratar cada caso.

## 5. Falsos positivos

- Nomes genéricos (Wave, Celery, Velocity, Zenith…) têm confiança "média" e vêm com o aviso **"confirme manualmente"**.
- Confira **o caminho**. `...\site-packages\celery` é uma biblioteca Python, não um executor.
- Na dúvida, peça explicação ao jogador e, se necessário, uma nova verificação ao vivo.
- Encontrou um falso positivo? Abra uma issue usando o modelo "Falso positivo".

## 6. Decisão justa e direito de defesa

1. **Nunca puna só pelo resultado automático.** Um organizador (de preferência dois) revisa as evidências.
2. **Mostre ao jogador** os achados que embasam a decisão e dê um prazo para ele se explicar.
3. **Registre a decisão** com o motivo e a regra violada.
4. **Ofereça recurso** com outra pessoa revisando.
5. **Comunique com discrição.** Prefira "suspenso por violação do item X do regulamento". **Evite chamar alguém
   publicamente de "hacker" ou "cheater"**: acusações públicas sem prova sólida podem gerar problemas legais
   (difamação/calúnia) e são injustas se houver erro.

## 7. Dados pessoais (LGPD)

- **Finalidade:** só verificar a integridade na liga. Não use para outra coisa.
- **Minimização:** o relatório já vem com só os achados e com o nome de usuário removido. Não peça arquivos extras.
- **Acesso restrito:** só a equipe de arbitragem vê os relatórios. Não publique o `.json`.
- **Retenção:** apague os relatórios depois da liga e do prazo de recurso (sugestão: até 30 dias depois).
- **Pedidos do titular:** se o jogador pedir para ver ou apagar o relatório, atenda.
- **Menores:** muitos jogadores de Roblox são menores de idade. Para menores de 12 anos, a LGPD exige consentimento
  específico de um dos pais ou responsável. O scanner pede essa confirmação, mas o ideal é coletar também na inscrição.

> Este guia não é aconselhamento jurídico. Em caso de dúvida ou de ligas com premiação em dinheiro,
> consulte um advogado.
