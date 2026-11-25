# Git, notebooks e Job manual no Databricks Free

Use a branch `main` do repositório [`EasyBigDataBR/mba_mlops`](https://github.com/EasyBigDataBR/mba_mlops) e execute o case no Databricks Free. **O fluxo principal lê os CSVs diretamente do Drive por uma conexão Unity Catalog autorizada.** O código fica no Git; dados recebidos, auditoria e resultados ficam em Delta e MLflow no Databricks. Copiar CSVs para um Volume é uma alternativa, não uma exigência da integração.

Este guia e o [template do Job](../jobs/job_template.json) foram conferidos com a documentação oficial em **25/11/2026**. A aceitação do Job, o acesso ao Drive e a execução completa nesta conta Free ainda precisam ser verificados no workspace. Validação local da biblioteca não comprova execução no Databricks.

## 1. Como os notebooks se encaixam

| Notebook | Quando usar |
| --- | --- |
| `00_Configurar.py` | Conferir parâmetros, preparar os objetos e testar a leitura da fonte antes do modelo. |
| `01_Ingerir_Atualizacoes.py` | Entender e executar a leitura dos arquivos e as validações da entrada. |
| `02_Executar_CausalImpact.py` | Estimar o contrafactual para o corte aceito. |
| `03_Painel_e_Validacao.py` | Conferir resultados, qualidade e rastreabilidade. |
| `04_Orquestrar.py` | Executar o ciclo completo pelo Job manual. |
| `05_Criar_Job.py` | Criar ou atualizar a definição do Job deste demonstrador, sem iniciar uma execução. |

O Job tem **uma tarefa**, apontando para `04_Orquestrar.py`. Ela chama funções dos módulos em `src/` e mantém ingestão, análise e validação na mesma sessão. A falha de uma etapa deve interromper o ciclo e ficar registrada, sem publicar análise parcial.

Essa escolha evita preparar três ambientes de tarefa para um exercício pequeno. Não é uma promessa de tempo ou consumo fixos. Uma cadeia de três tarefas continua sendo uma opção futura se precisarmos de ambientes, permissões ou retomadas independentes. `dbutils.notebook.run()` não é usado pelo orquestrador: cada chamada cria um Job efêmero e pode acrescentar inicializações. [Orquestração e módulos][orchestration]

## 2. Primeiro, conecte o Git folder

1. No Databricks, abra **Workspace**, escolha sua pasta e selecione **Create → Git folder**.
2. Informe `https://github.com/EasyBigDataBR/mba_mlops.git`, provedor **GitHub**, e um nome para a pasta.
3. Configure a credencial Git pela interface se for solicitada. Não coloque credenciais em notebooks ou parâmetros.
4. Selecione **main**. Antes de começar uma aula, abra o diálogo Git e use **Pull**.
5. Abra `notebooks/00_Configurar.py`. Confira a configuração antes de executar as etapas do case.

Não é necessário habilitar o Git CLI em preview. O Git folder é uma cópia de trabalho: atualizar `main` no GitHub não atualiza essa cópia sem o **Pull**. Faça a atualização antes de iniciar a sessão, pois ela pode limpar o estado do notebook. [Operações de Git folder][git-folder]

## 3. Prepare as dependências no notebook de entrada

Antes do primeiro **Run All** interativo em `02` ou `04`, selecione **Serverless**, CPU e memória padrão. No painel **Environment**, escolha **Standard versão 4** — em **More**, se necessário — e aplique. Essa versão documenta **Python 3.12.3**, pandas 2.2.3 e MLflow Skinny 2.22.0, com suporte previsto até **13/08/2028**. O ambiente ainda precisa estar disponível nesta conta Free. [Environment 4][environment-four] · [Versões e suporte][environment-versions]

O template do Job fixa `environment_version="4"` no ambiente `causalimpact_py312`, referenciado pela tarefa. Assim, o Job não depende do ambiente padrão que seria resolvido na ausência de `environment_key` e metadados no notebook. A versão do ambiente seleciona o Python; `%pip` não muda a versão do interpretador.

Os notebooks `02_Executar_CausalImpact.py` e `04_Orquestrar.py` preparam suas dependências com `%pip` e versões fixadas. As páginas oficiais de bibliotecas e de tarefa Notebook confirmam `%pip` em notebooks serverless e em Jobs. Mantenha instalação e `dbutils.library.restartPython()` antes de criar variáveis, importar módulos ou executar etapas; o reinício apaga o estado Python. Ter executado `00_Configurar.py` interativamente não instala bibliotecas na sessão futura do Job. Não instale PySpark. [Bibliotecas do notebook][pip] · [Tarefa Notebook][notebook-task] · [Reinício do Python][restart]

O **Environment do notebook** também permite configurar dependências e habilitar **Include in source file exports**, persistindo a configuração no `.py` com metadados PEP 723. É uma alternativa documentada; confira a exportação real antes de substituir as células `%pip` por ela.

O ambiente do Job fixa somente a base, sem duplicar a lista científica instalada pelas células `%pip`. Aplicar alterações pelo painel **Environment** também reinicia o processo Python. Confira a versão efetiva antes da análise. [Environment serverless][environment]

A combinação TensorFlow/TFP/Keras precisa permanecer compatível. TensorFlow 2.18.1 publica wheels para Python 3.12 em Linux x86-64 e ARM64. O TFP 0.25 documenta a família TensorFlow 2.18 e requer Keras 2 por meio de `tf-keras`. O ensaio local não reproduz todo o ambiente Databricks: o primeiro ciclo ainda deve confirmar instalação, imports e integração Spark/MLflow. [TensorFlow 2.18.1][tensorflow] · [Notas do TFP 0.25][tfp]

## 4. Parâmetros do ciclo

Os parâmetros do template estão no nível do Job e chegam automaticamente aos widgets da tarefa. **Preencha os valores privados uma vez no workspace e preserve-os no Job.** A chegada de outro CSV não exige mudar parâmetros. Use **Run now with different parameters** somente quando quiser mudar a configuração de uma execução. [Parâmetros de Job][parameters]

| Parâmetro | Valor inicial | Uso |
| --- | --- | --- |
| `catalog` | `mba` | Catálogo dos objetos do case. |
| `schema` | `mlops_causalimpact` | Schema do case. |
| `source_mode` | `drive` | Fluxo principal; `volume` é uma alternativa explícita. |
| `source_path` | vazio no Git | No workspace, informe a URL privada da pasta **`01_Entrada_Databricks`**, não a URL da pasta que contém entrada e reserva. |
| `drive_connection` | vazio no Git | No workspace, informe o nome da conexão Unity Catalog autorizada para ler o Drive. |
| `as_of` | vazio | Último dia completo presente na fonte validada; uma data ISO `AAAA-MM-DD` limita o corte do snapshot atual. |
| `num_results` | `300` | Número de amostras posteriores da análise; não é limite de arquivos. |
| `demo_id` | `campanha_demo_v1` | Identidade da demonstração. |
| `max_files_per_run` | `10` | Limite de segurança para a seleção de arquivos; não funciona como cursor de entregas. |
| `experiment_path` | `/Shared/MBA_CausalImpact_Demo` | Experimento MLflow do workspace, criado se ainda não existir e houver permissão. |

Com `as_of` vazio, o corte é o último dia completo **presente na fonte validada**, observado o calendário em `America/Sao_Paulo`; não significa automaticamente ontem. Confira o **corte efetivo** dos dados aceitos: mudar o calendário não cria observações nem autoriza preencher lacunas. Depois da conferência inicial, mantenha pré-período, data de intervenção e controles fixos. Uma correção pode mudar o snapshot sem aumentar o corte.

Informar uma data em `as_of` faz um **recorte temporal do snapshot atual**. Isso não recupera automaticamente os bytes de uma análise antiga: se o arquivo `10` corrigiu um dia anterior, o novo recorte contém essa correção. Para reproduzir a entrada e a configuração históricas, use o snapshot e os hashes originais, o commit, os parâmetros, a seed e as versões do ambiente daquela análise.

### Drive: organize a entrada e a reserva

Na pasta do Drive usada para a demonstração, mantenha estas duas **pastas irmãs**:

| Pasta | Conteúdo inicial | Uso pelo Job |
| --- | --- | --- |
| `01_Entrada_Databricks` | CSVs `01` a `05`. | É a única pasta apontada por `source_path`. |
| `02_Reserva_Proximas_Execucoes` | CSVs `06` a `10`. | Guarda as próximas entregas, fora da árvore lida pelo Job. |

A leitura Spark do Drive percorre subpastas mesmo com `recursiveFileLookup=false`. O filtro `*.csv` seleciona nomes de arquivos, não pastas. Por isso, **não aponte para a pasta que contém entrada e reserva**, nem crie a reserva dentro da entrada. Depois do primeiro ciclo, mova um arquivo da reserva para a entrada e clique em **Run now**. Mantenha na entrada todos os arquivos já entregues. [Ingestão do Drive][drive]

### Drive: autorize a conexão uma vez

Use uma **conexão Unity Catalog Google Drive existente**, com acesso à pasta, e informe seu nome em `drive_connection`. Na rota SQL/Spark, a documentação exige UC, Runtime 17.3 ou superior e os privilégios correspondentes: `USE CONNECTION` em acesso standard; `MANAGE CONNECTION` em dedicated. Criar uma conexão exige `CREATE CONNECTION`. Confira também as permissões da identidade que executará o Job, que pode diferir da sessão interativa. [Ingestão do Drive][drive]

Se precisar preparar uma conexão, o guia SQL/Spark documenta projeto Google Cloud com Drive API, consentimento OAuth, credenciais de cliente, callback do workspace e escopo `https://www.googleapis.com/auth/drive.readonly`. Esse projeto autoriza a fonte; todo o processamento do case permanece no Databricks. O conector gerenciado Lakeflow Connect também oferece OAuth **Databricks-managed**, sem projeto próprio, quando habilitado na conta. Este demonstrador usa Spark dentro do notebook, e a compatibilidade da conexão escolhida deve ser confirmada pelo teste de leitura. [OAuth e conexão][drive-connection]

Free Edition usa serverless e tem restrições de saída à internet. A documentação não proíbe genericamente a integração Drive; a restrição explícita de conectores Lakeflow CDC refere-se aos que dependem de compute clássico. Isso também não garante que o recurso esteja disponível nesta conta. O Environment 4 define a API cliente e o ambiente Python; o servidor recebe atualizações independentes. **Confirme a leitura no workspace antes de iniciar o modelo.** [Limites Free][free] · [Versões serverless][environment-versions]

Informe a URL e o nome da conexão somente nos widgets e parâmetros privados do Job. Os campos vazios do repositório são intencionais: não publique IDs de pastas, URLs privadas, tokens ou credenciais no Git, nem torne a pasta pública para contornar a autorização.

### Teste de leitura antes de executar CausalImpact

No `00_Configurar`, preencha os parâmetros, prepare as tabelas do exemplo e execute o teste de leitura. Na primeira demonstração, ele deve encontrar **exatamente os cinco CSVs iniciais**, com nomes e hashes iguais aos do [manifesto](../data_demo/manifest.json). O teste lê a fonte e confere os bytes; não ajusta o modelo nem publica um snapshot. Se falhar, resolva fonte, conexão, permissões ou arquivos antes de abrir `02`.

O leitor usa `binaryFile`; primeiro limita a quantidade e os tamanhos, depois valida o conteúdo. Em Drive, `path` é uma URL, por isso o nome vem de `_metadata.file_name`. Uma consulta de metadados não comprova, por si só, ausência de I/O remoto. [Schemas do Drive][drive] · [Metadados de `read_files`][read-files]

São até **10 CSVs pequenos**, limitados a 1 MB por arquivo e 5 MB no conjunto. A cada run, o notebook relê a entrada e recalcula hashes; o manifesto e o histórico distinguem novas entregas, repetições e correções. A persistência é idempotente e a análise pode ser reutilizada. **Não há Auto Loader, cursor de arquivos ou promessa de baixar somente o CSV novo.**

### Preciso replicar a entrada em `/Volumes`?

**Não no modo Drive.** O notebook lê a fonte diretamente pela conexão e grava os bytes originais, hash e horário em `ci_demo_bronze`. Essa tabela Delta preserva a evidência recebida para auditoria; não é necessário manter outra pasta com cópias dos CSVs. O setup em modo Drive cria os objetos Delta do exemplo e **não cria Volume**. O Databricks documenta leitura direta com Spark/SQL e, em uma rota separada, ingestão gerenciada em tabelas Delta. [Leitura direta][drive] · [Conector gerenciado][drive-managed]

Se a conexão não estiver disponível no Free, use a alternativa explícita: envie os mesmos bytes para `/Volumes/mba/mlops_causalimpact/landing/causalimpact_demo`, configure `source_mode=volume`, esse caminho em `source_path` e `drive_connection` vazio. O setup de `00` pode criar o Volume gerenciado `landing`, se não existir, e a subpasta. Para isso, precisa de `CREATE VOLUME` no schema; leitura exige `USE CATALOG`, `USE SCHEMA` e `READ VOLUME`, e envio exige `WRITE VOLUME`. Não há troca automática de fonte. [Permissões de volumes][volume]

## 5. Crie o Job uma vez e execute quando chegar um arquivo

### Rota principal — notebook `05`, com código vindo do GitHub

Depois do teste de leitura e do primeiro ciclo, abra `05_Criar_Job.py` no Git folder. Preencha os mesmos parâmetros, incluindo os valores privados de `source_path` e `drive_connection`, e execute. O notebook aplica o [template](../jobs/job_template.json) ao Job **`MBA_MLOPS_CAUSALIMPACT_MANUAL`** e mostra seu link.

O comportamento é explícito no [código de `05`](../notebooks/05_Criar_Job.py):

- Se o Job não existir, cria a definição.
- Se houver um único Job com o nome esperado e a tag `mba_mlops_demo=causalimpact_demo_v1`, **atualiza sua definição com `jobs/reset`**, preservando o ID. Usa o template atual e os parâmetros dos widgets; configurações editadas antes na interface podem ser substituídas.
- Se houver mais de um Job com o nome, ou a identificação não corresponder, interrompe sem alterar aquele Job.

**Criar ou atualizar a definição não inicia uma run.** Confira os parâmetros salvos, o ambiente Serverless/Standard e a credencial Git. Nos ciclos seguintes, mova o próximo CSV para a entrada e clique em **Run now**. Execute `05` novamente apenas quando quiser reaplicar uma configuração do Job; a chegada de arquivo não exige isso.

A tarefa usa fonte `GIT`, repositório GitHub e branch `main`. O path é **`notebooks/04_Orquestrar.py`**, relativo ao repositório, com `.py` e sem `/` ou `./` no início. Cada run resolve um snapshot do código e mostra o SHA usado. O **Pull** do Git folder atualiza os notebooks interativos, mas não controla o Git remoto do Job. Para congelar uma versão do Job, substitua `git_branch` por `git_commit` com um SHA real revisado. [Tarefa Notebook][notebook-task] · [Git em Jobs][git-jobs]

### Alternativa pela interface, se a API não estiver disponível

1. Abra **Jobs & Pipelines → Create → Job** e adicione uma tarefa **Notebook** com fonte **Git provider**.
2. Configure o repositório, a branch `main` e o path acima. Se optar por fonte **Workspace**, selecione `04_Orquestrar` no Git folder pela interface e faça Pull antes de executar uma versão nova.
3. Selecione **Serverless** e configure **Jobs Environment → Standard versão 4**; no seletor antigo, **Environment version 4**. Preencha os parâmetros da seção 4, com a URL privada da pasta de entrada.
4. Mantenha execução manual, concorrência máxima `1`, fila desativada e tentativas adicionais `0`. Desative **Enable serverless auto-optimization**, que pode incluir novas tentativas. Se disponível, desligue **Performance optimized** para usar **Standard**.
5. Salve e confira a definição antes de clicar em **Run now**. Se criou o Job manualmente sem a tag do demonstrador, continue gerenciando-o na interface; `05` não deve assumir sua propriedade.

O JSON publicado mantém os campos privados vazios. Para usar a CLI, prepare uma cópia privada com os parâmetros preenchidos; criar diretamente a partir do template vazio não prepara uma leitura válida. Não publique essa cópia. Uma mudança no template Git não atualiza automaticamente um Job já criado: a atualização ocorre pela interface ou ao executar `05` com os valores corretos. [Criar e gerenciar Jobs][automate] · [Contrato da API][jobs-api]

O template não contém agenda, gatilho, cluster clássico ou destinatários. A disponibilidade de **Standard** e do ambiente deve ser conferida na conta Free; não é necessário mudar para um plano pago para preparar o exercício. [Jobs serverless][serverless]

## 6. Entregue os 10 CSVs em ciclos

Os arquivos de `data_demo/` são **sintéticos**. O [manifesto](../data_demo/manifest.json) fixa datas, seed, ordem, hashes e correções. Para uma demonstração nova, use o procedimento do gerador; não regenere o passado apenas porque o dia atual mudou.

| Ciclo | Arquivos novos | O que conferir |
| --- | --- | --- |
| 1 | `01` a `05`, juntos | Carga inicial completa antes da análise. |
| 2 | `06` | Extensão válida da série. |
| 3 | `07` | Rejeição deliberada por controle ausente; nenhuma nova análise válida. |
| 4 | `08` | Correção explícita do arquivo `07`; rejeição anterior preservada no histórico. |
| 5 | `09` | Novos dias aceitos; comparar resultados e intervalos. |
| 6 | `10` | Correção de um dia antigo; snapshot muda, corte não recua. |

Os cinco primeiros ficam em `01_Entrada_Databricks`; os demais começam em `02_Reserva_Proximas_Execucoes`. Depois de cada demonstração, **mova somente o próximo arquivo para a entrada e clique em Run now**, sem editar o Job. Mantenha os arquivos anteriores na entrada e o limite total `10`.

Cada run relê e revalida os bytes disponíveis. Repetir os mesmos arquivos preserva o snapshot; a análise também é reutilizada se código, ambiente e configuração permanecerem iguais. As novas tentativas continuam auditadas. Uma correção chega como arquivo novo e substitui a linha da mesma `date`, sem somar as contagens antigas. A rejeição de `07` não impede o processamento posterior de `08`.

## 7. Confira a evidência antes de avançar

Em cada ciclo, confira versão do código, arquivos selecionados e seus hashes, corte solicitado e efetivo, status da ingestão, identidade da análise e resultado da validação. Em caso de rejeição, o último resultado válido deve continuar distinguível da tentativa que falhou.

Configure um **experimento MLflow do workspace** explicitamente antes de registrar runs. O notebook temporário de um Job com Git remoto não é um lugar confiável para manter um experimento do próprio notebook. O código chama `mlflow.set_experiment()` com `experiment_path`, cujo padrão é `/Shared/MBA_CausalImpact_Demo`; a identidade do Job precisa ter acesso a ele e permissão para criá-lo se necessário. Grave saídas persistentes em tabelas ou volumes; tarefas de Git remoto não podem gravar nos arquivos do workspace. [Tarefa Notebook][notebook-task] · [Git em Jobs][git-jobs]

No Free, use execução manual, uma tarefa por vez e os arquivos pequenos do exercício. A edição é gratuita, mas está sujeita a cotas de uso; oferece apenas serverless, limita tarefas simultâneas e restringe acesso de saída à internet. Uma quota esgotada pode suspender o compute até sua renovação. Não há garantia de duração ou disponibilidade da sessão. [Limites da Free Edition][free]

## Documentação oficial

[orchestration]: https://docs.databricks.com/aws/en/notebooks/notebook-workflows
[git-folder]: https://docs.databricks.com/aws/en/repos/git-operations-with-repos
[environment]: https://docs.databricks.com/aws/en/compute/serverless/dependencies
[environment-four]: https://docs.databricks.com/aws/en/release-notes/serverless/environment-version/four
[environment-versions]: https://docs.databricks.com/aws/en/release-notes/serverless/environment-version
[pip]: https://docs.databricks.com/aws/en/libraries/notebooks-python-libraries
[restart]: https://docs.databricks.com/aws/en/libraries/restart-python-process
[tfp]: https://github.com/tensorflow/probability/releases/tag/v0.25.0
[tensorflow]: https://pypi.org/project/tensorflow/2.18.1/
[parameters]: https://docs.databricks.com/aws/en/jobs/job-parameters
[volume]: https://docs.databricks.com/aws/en/volumes/privileges
[drive]: https://docs.databricks.com/aws/en/ingestion/google-drive
[drive-connection]: https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/google-drive-connection
[drive-managed]: https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/google-drive
[read-files]: https://docs.databricks.com/aws/en/sql/language-manual/functions/read_files
[notebook-task]: https://docs.databricks.com/aws/en/jobs/tasks/notebook
[git-jobs]: https://docs.databricks.com/aws/en/jobs/git
[automate]: https://docs.databricks.com/aws/en/jobs/automate
[jobs-api]: https://docs.databricks.com/api/jobs/v2/create-job
[serverless]: https://docs.databricks.com/aws/en/jobs/run-serverless-jobs
[free]: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations

- [Orquestração e módulos][orchestration]
- [Git folder][git-folder] e [Git em Jobs][git-jobs]
- [Ambientes serverless][environment], [bibliotecas][pip] e [restart][restart]
- [Environment 4][environment-four] e [versões e suporte][environment-versions]
- [TensorFlow 2.18.1][tensorflow] e [TFP 0.25: compatibilidade][tfp]
- [Parâmetros de Job][parameters] e [tarefa Notebook][notebook-task]
- [Drive como fonte][drive], [conexões OAuth][drive-connection] e [metadados de arquivos][read-files]
- [Conector gerenciado, rota distinta deste notebook][drive-managed] e [Volume opcional][volume]
- [Automação][automate], [Jobs API][jobs-api] e [Jobs serverless][serverless]
- [Limites da Free Edition][free]
