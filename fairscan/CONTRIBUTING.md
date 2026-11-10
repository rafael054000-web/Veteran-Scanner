# Contribuindo

Obrigado por ajudar! As contribuições mais úteis são **novas assinaturas** e **relatos de falsos positivos**.

## Adicionando uma assinatura

Edite `fairscan/data/signatures.json`:

```json
{"id": "nome-curto", "name": "Nome Exibido", "category": "executor", "confidence": "high",
 "names": ["nomeexato", "nome exato"], "exclude": ["algo parecido legítimo"], "note": "dica opcional"}
```

- `names` são comparados com o nome do arquivo/pasta/processo **normalizado**: minúsculas, sem extensão, sem espaços,
  `-`, `_` ou `.`. Sufixos de versão e instalador (`v3`, `setup`, `bootstrapper`, `x64`…) já são aceitos
  automaticamente.
- Use `"confidence": "medium"` quando o nome também for usado por outro software. A severidade cai um nível e o
  relatório pede confirmação manual.
- Use `exclude` (expressões regulares, sem diferenciar maiúsculas) para evitar falsos positivos conhecidos.
- Categorias: `executor`, `injector`, `memory_editor`, `dual_use`, `macro`, `bootstrapper`, `fps_unlocker`, `cleaner`.
- **Adicione testes** em `tests/test_fairscan.py`: um caso positivo e, se o nome for genérico, um negativo.

### Regras
- ❌ Não adicione links de download, instruções de uso ou código de cheats.
- ❌ Não adicione detecções que exijam ler a memória do Roblox ou interagir com o processo do jogo.
- ❌ Não adicione coleta de dados além do necessário (veja [PRIVACIDADE.md](PRIVACIDADE.md)).
- ✅ Explique na PR de onde vem a informação (ex.: nome padrão da pasta criada pelo programa).

## Fast Flags associadas a abuso
Edite `fairscan/data/fflags_abuse.json` com o nome e um motivo curto. Atualize o campo `version`.

## Rodando os testes
```bash
python -m unittest discover -s tests -v
```
