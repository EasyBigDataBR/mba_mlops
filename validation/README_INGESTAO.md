# Evidência local da ingestão

O arquivo [ingestion_sequence.json](ingestion_sequence.json) registra a execução
real de `plan_snapshot()` sobre os dez CSVs sintéticos de `data_demo/`. Ele
contém hashes dos fontes conferidos, resultados dos seis ciclos, eventos de
rejeição/substituição e a repetição de cada ciclo com os mesmos bytes.

**Escopo:** validação local em Python/pandas, testes unitários e compilação da
sintaxe dos notebooks. Não foram executados Spark, Delta, o workspace MLflow,
Jobs, acesso a Drive/Volume ou células dos notebooks nesta conferência. Os
ensaios locais do modelo estão documentados separadamente em
[README_MODELO.md](README_MODELO.md).

## Resultado dos seis ciclos

| Ciclo | Arquivos presentes | Status do plano | Linhas candidatas | Corte contíguo | Rejeitados ativos | Substituídos |
| --- | --- | --- | ---: | --- | ---: | ---: |
| 1 | 01–05 | READY | 98 | 2026-11-03 | 0 | 0 |
| 2 | 01–06 | READY | 105 | 2026-11-10 | 0 | 0 |
| 3 | 01–07 | BLOCKED | 105 | 2026-11-10 | 1 | 0 |
| 4 | 01–08 | READY | 112 | 2026-11-17 | 0 | 1 |
| 5 | 01–09 | READY | 119 | 2026-11-24 | 0 | 1 |
| 6 | 01–10 | READY | 119 | 2026-11-24 | 0 | 1 |

O arquivo 07 é rejeitado inteiro. Suas linhas válidas não entram parcialmente
no snapshot. O arquivo 08 corrige o mesmo período e deixa o evento anterior
como `SUPERSEDED`, preservando `validation_status=REJECTED`, o erro original e
a identificação da correção. A rejeição histórica continua disponível.

O arquivo 10 substitui somente a linha de **2026-10-26**. A contagem `treated`
desse dia aumenta em 12; os controles e todo o pré permanecem iguais. O
snapshot muda, mas continuam existindo 119 datas únicas e o corte permanece
em 2026-11-24. Nenhuma soma entre versões da mesma data é realizada.

Um plano `BLOCKED` ou `INCOMPLETE` pode devolver um DataFrame candidato para
diagnóstico. Ele não está liberado para publicação. O chamador precisa exigir
`status == "READY"`; `summary.publishable` expressa a mesma condição.

## Identidade e repetição

O SHA-256 de cada CSV protege seus bytes exatos. O `snapshot_id` identifica os
dados atuais após resolver as revisões: CSV UTF-8, LF, cabeçalho fixo
`date,treated,control_a,control_b`, datas ordenadas, inteiros e quebra de linha
final. Colunas de proveniência não entram nesse hash.

Nos seis ciclos, o hash coincidiu com o resultado esperado no
[manifesto](../data_demo/manifest.json) e com a função Python de hash do
adaptador Databricks. Isso verifica a compatibilidade de serialização; não
comprova uma gravação ou leitura Delta.

Cada plano foi repetido com os mesmos bytes e com a ordem do dicionário de
entrada invertida. Dados, status, corte, hash, eventos e resumo permaneceram
iguais. A decisão de reutilizar uma análise persistida pertence ao runtime;
esta conferência prova a repetibilidade do plano local.

**`as_of` não identifica sozinho uma revisão histórica.** Ele recorta o
snapshot atualmente aceito, que já pode conter uma correção tardia. Para
recuperar exatamente os dados anteriores à correção, use o `snapshot_id`
registrado e seus dados preservados.

## Testes e sintaxe

Nesta rodada, **51 testes unitários passaram**, sem falhas, erros ou testes
ignorados. O comando equivalente, na raiz do repositório, é:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_*.py' -v
```

Os seis arquivos de `notebooks/` passaram em `compile(source, path, "exec")`.
Essa conferência não executa as células `%pip`, não resolve `spark`/`dbutils`
e não testa a aceitação do Job no serviço. Os hashes individuais dos notebooks
estão no JSON de evidência, permitindo identificar a versão de cada arquivo
que foi conferida.
