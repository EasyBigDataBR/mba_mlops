# Arquivos das campanhas no Drive

## Um ponto de entrada para os cinco encontros

Pasta preparada: **Dados_Campanhas_CausalImpact**, dentro da pasta do curso. O endereço foi entregue ao usuário na conversa e será configurado no workspace. URLs e IDs privados do Drive não são publicados neste repositório.

O Drive recebe os arquivos de resultados observados. O Databricks Free prepara os dados, executa o CausalImpact e mostra os resultados. O GitHub guarda o código e a documentação.

**Estado:** a pasta foi criada. Ainda não foram recebidos arquivos de campanha nesta preparação, configurada a transferência ou executada a ingestão. O contrato abaixo será mapeado às colunas reais após a leitura do código existente.

## Fluxo inicial do curso

1. Depositar no Drive um arquivo CSV identificado por campanha, período e revisão.
2. Baixar esse arquivo e enviá-lo ao volume `mba.mlops_causalimpact.landing`.
3. Conferir nome, tamanho, hash, cabeçalho, período e completude antes de processar.
4. Usar o fluxo existente para validar e incorporar o lote, com controle contra duplicação.
5. Atualizar a análise até o novo corte completo e preservar sua identificação.
6. Consultar o resultado e o contexto da execução no painel.

Caminho previsto no Databricks: `/Volumes/mba/mlops_causalimpact/landing/`.

O upload para um volume é documentado na interface do Databricks: **New → Add or upload data → Upload files to a volume**. O destino pode ser selecionado pelo catálogo ou pelo caminho acima. Isso exige as permissões correspondentes no volume, schema e catálogo. [Documentação oficial](https://docs.databricks.com/aws/en/volumes/volume-files).

A transferência inicial é manual. O processamento será ajustado no notebook do projeto depois de sua inspeção. Esta preparação não afirma que o upload ou o Job já tenham sido executados.

## Conteúdo do arquivo

O contrato final aproveitará o formato já usado no projeto. Estes são os significados que ele precisa representar, sem pressupor nomes de colunas existentes:

| Informação | Regra de interpretação |
|---|---|
| Campanha ou estudo | Identificação estável ao longo dos encontros |
| Data da observação | Dia da métrica no fuso definido pelo estudo |
| Série ou grupo | Identificação da série tratada ou do controle |
| Métrica e unidade | A mesma definição em todos os arquivos comparáveis |
| Resultado observado | Valor realmente observado naquele dia |
| Período coberto | Início, fim e indicação verificável de completude |
| Origem | Dado real ou sintético, explicitamente identificado |
| Revisão | Identificação de correções e da versão que substituem |

Para o CausalImpact, a atualização precisa cobrir também os controles usados no período posterior. O resultado da campanha isolado não basta para reconstruir o contrafactual quando o modelo depende desses controles.

Efeitos estimados, contrafactuais e previsões são saídas do modelo. Eles não retornam ao arquivo de entrada como se fossem novas observações.

Prefira CSV UTF-8, cabeçalho estável e datas ISO `YYYY-MM-DD`. O separador e a representação decimal serão declarados no contrato para evitar interpretações diferentes no upload.

## Um novo arquivo para cada lote

Padrão proposto de nome:

`campanha_<id>_<inicio>_<fim>_r<revisao>.csv`

O nome ajuda a organizar; a validação usa o conteúdo e o controle de ingestão. Um nome correto não garante que os dias e as séries estejam completos.

- Um lote novo preserva o arquivo anterior.
- Um arquivo idêntico já concluído deve ser reconhecido pelo controle de ingestão.
- Uma correção de dias anteriores recebe outra revisão e indica o lote corrigido.
- Uma correção não deve ser simplesmente somada aos valores anteriores.
- Uma nova análise mantém referência à versão dos dados utilizada.

A documentação do conector gerenciado informa que, para formatos estruturados como CSV, a ingestão incremental incorpora novos arquivos e não captura edições em arquivos já ingeridos. Por isso, a proposta usa arquivos novos por lote ou revisão. [FAQ oficial](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/google-drive-faq).

## Totais, incrementos e identidade da observação

Cada lote precisa declarar se traz **totais diários completos** ou **incrementos**. A regra será única e explícita para cada fonte. Um total diário corrigido substitui a revisão anterior na base usada pela análise; as duas versões continuam preservadas na origem.

O hash identifica o conteúdo do arquivo. A chave lógica identifica a observação — por exemplo, série/grupo, data, métrica e campanha, quando aplicável ao contrato real. Dois arquivos com hashes diferentes podem repetir a mesma observação. Por isso, a ingestão verifica os dois níveis.

A data de upload não prova que um dia está completo. Ausência de linha não equivale a zero. O corte precisa de observações finais do tratado e de todos os controles.

Se uma correção mudar os valores do pré ou do pós já analisados, ela gera nova identificação dos dados e nova versão da análise. O mesmo `as_of` não autoriza reutilizar um resultado produzido com outro conteúdo, configuração ou código.

## Controle no projeto existente

`bronze_ingestion_control` é o objeto existente que será inspecionado para mapear esse controle. Não será presumida a presença de colunas ou regras pelo nome da tabela.

O registro precisa permitir relacionar o arquivo de origem, hash, revisão, período, destino, estado da ingestão e análise produzida. Quando a transferência for manual, a identificação do arquivo no Drive pode ser registrada junto ao lote; não é necessário inserir credenciais no código.

Os checks devem tratar separadamente:

- **Arquivo repetido:** mesmo conteúdo e processamento já concluído.
- **Nova observação:** novas datas completas para as séries esperadas.
- **Correção histórica:** dados substitutos, com revisão e precedência explícitas.
- **Entrada inválida:** calendário incompleto, duplicatas de chave, métrica ou unidade incoerente.

Arquivo recebido não significa análise concluída. O controle precisa distinguir a chegada, a validação, a incorporação dos dados e a conclusão da análise. Se houver falha após uma escrita, a retomada deve reconhecer o que já foi persistido.

## O corte em cada encontro

O corte solicitado usa, por padrão, o último dia completo no fuso `America/Sao_Paulo`. O corte analisado precisa estar coberto por dados completos da série tratada e dos controles.

A data da intervenção, o período anterior e a definição dos controles permanecem fixos após sua confirmação no projeto. A cada encontro, o período posterior cresce quando há novos dias completos.

Se a fonte for histórica, o replay usa datas históricas explícitas. Alterar as datas do CSV para aparentar atualização não é uma atualização válida.

## Integração automática: possibilidade a verificar

O Databricks documenta um conector gerenciado de Google Drive e uma alternativa por APIs Spark/SQL. A opção gerenciada **OAuth U2M: Databricks-managed**, quando habilitada no workspace, permite autenticação sem criar um projeto Google Cloud próprio. [Conector oficial](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/google-drive).

Ainda não foi verificada a disponibilidade dessa opção na conta Free informada. A existência da documentação não prova que a conexão está habilitada nesse workspace. A automação também precisa ser testada com as permissões, a rede e as quotas disponíveis.

Para manter a primeira versão do curso simples, o procedimento por upload no volume está documentado como ponto de partida. Uma integração nativa poderá ser adotada após a confirmação de suporte e autenticação, mantendo os mesmos contratos de lote, corte e análise. O conector gerenciado ingere diretamente em tabelas Delta; não se presume que ele também grave os arquivos no volume landing. Essa rota precisará de um mapeamento explícito para as tabelas existentes.

## Relação com os encontros

| Encontro | Uso do arquivo |
|---|---|
| 1 | Conhecer o formato e conferir a primeira base disponível |
| 2 | Processar o corte disponível e construir o primeiro contrafactual |
| 3 | Incorporar o próximo lote e comparar versões identificadas |
| 4 | Repetir o processamento pelo Job manual com controle de ingestão |
| 5 | Incorporar a atualização final e interpretar o painel |

O calendário dos encontros e os períodos dos arquivos serão preenchidos com as datas reais do curso e da fonte.

Manifestos operacionais com referências privadas, arquivos de campanha e saídas da análise ficam fora deste repositório público. O Git guarda o contrato e exemplos sanitizados.
