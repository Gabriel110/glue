# Gerador de dados locais para AWS Glue

Este diretório contém um gerador de CSV para criar dados de teste localmente. O script é executado dentro da imagem Docker do AWS Glue, mas grava os arquivos na pasta do projeto montada pelo Docker Compose.

## Estrutura esperada

No projeto, mantenha os arquivos assim:

```text
seu-projeto/
├── docker-compose.yml
├── Dockerfile
├── app/
│   ├── src/
│   ├── utils/
│   └── local/
│       ├── generate_local_data.py
│       └── local_data.yaml
└── data/                  # opcional; a configuração pode gravar em outro lugar
```

No serviço `aws-glue-local` do `docker-compose.yml`, estes volumes montam o projeto e expõem `app/local` também em `/home/hadoop/workspace/local` dentro do container:

```yaml
volumes:
  - .:/home/hadoop/workspace
  - ./app/local:/home/hadoop/workspace/local
  - "${USERPROFILE}/.aws:/home/hadoop/.aws:ro"
```

O container precisa estar em execução e o Docker Desktop deve estar usando Linux containers.

## Configuração YAML

Exemplo de `local_data.yaml`:

```yaml
# Caminho relativo à pasta deste YAML. '.' significa app/local.
path: .

data:
  - database: db_cards
    table: cards
    size: 1000
    columns:
      - name: id
        type: int
        seed: 123456
        random: false
        min: 1
        max: 1000

      - name: name
        type: string
        prefix: card_
        seed: 1
        random: true

      - name: name_padded
        type: string
        prefix: card_
        seed: "0001"
        random: true

      - name: atk
        type: int
        seed: 987654
        random: true
        min: 0
        max: 5000

      - name: attribute
        type: string
        values: [DARK, LIGHT, EARTH, WATER, FIRE, WIND]
        seed: 123
        random: true

  # Você pode declarar outras tabelas e databases aqui.
  - database: db_test
    table: sample
    size: 20
    columns:
      - name: description
        type: string
        values: [Alpha, Beta, Gamma]
        random: false
```

Cada item de `data` descreve uma tabela:

- `database`: nome do database; vira uma pasta própria.
- `table`: nome da tabela; vira o nome do CSV.
- `size`: quantidade de linhas de dados, sem contar o cabeçalho.
- `columns`: colunas que serão escritas no CSV. O gerador também aceita `coluns`, mas `columns` é a grafia recomendada.
- `path`: pasta de saída. Caminhos relativos são resolvidos a partir da pasta do YAML. Use `.` para gravar em `app/local`.

O resultado segue o formato `<path>/<database>/<table>.csv`. Com `path: .`, os exemplos geram:

```text
app/local/db_cards/cards.csv
app/local/db_test/sample.csv
```

Cada database fica separado em sua própria pasta, como um prefixo local semelhante à organização no S3.

## Campos das colunas: `name` e `type`

Cada item em `columns` descreve uma coluna do CSV.

- `name` é obrigatório e define o nome do cabeçalho. Por exemplo, `name: atk` cria uma coluna chamada `atk`. Para strings automáticas, esse nome também vira o prefixo padrão se `prefix` não for informado (`name: card_name` gera `card_name_1`, `card_name_2`, etc.).
- `type` define o tipo/formato dos valores que o gerador cria. Tipos aceitos: `string`, `int`/`integer`/`long`, `float`/`double`/`decimal` e `bool`/`boolean`.

Exemplo:

```yaml
columns:
  - name: atk
    type: int
    min: 0
    max: 5000
    seed: 42
    random: true
  - name: card_name
    type: string
    prefix: card_
    seed: 1
    random: true
```

`name` identifica a coluna; `type` determina como os dados dela são gerados. Os demais campos (`values`, `prefix`, `seed`, `random`, `min`, `max`) ajustam a geração daquele tipo.

## Como funcionam `values`, `random` e `seed`

`values` escolhe de onde vêm os valores da coluna; `random` escolhe como usar a lista. `seed` controla a sequência aleatória quando há sorteio, com uma exceção intencional: em uma coluna `string` gerada automaticamente, `seed` é o contador inicial.

| Configuração da coluna | Resultado |
| --- | --- |
| `values` contém itens e `random: true` | Sorteia um item da lista para cada linha. Com o mesmo `seed`, repete a mesma sequência de sorteios. |
| `values` contém itens e `random: false` | Percorre os itens na ordem e volta ao início da lista até preencher `size`. |
| `values` ausente ou `values: []` | Gera valores automaticamente de acordo com `type`; não usa valores padrão escondidos. |

### `prefix` e `seed` em strings automáticas

Quando `type: string` e `values` está ausente ou vazio:

- `prefix` é o texto colocado antes do contador. Por exemplo, `prefix: card_` produz valores que começam com `card_`. Se omitido, o gerador usa o nome da coluna seguido de `_`.
- `seed` é o primeiro número do contador. Com `seed: 1` e `size: 100`, os valores vão de `card_1` a `card_100`.
- Para preencher zeros à esquerda, escreva o seed como texto entre aspas: `seed: "0001"`. Com `size: 1000`, os valores vão de `card_0001` a `card_1000`.
- Se `seed` for omitido, o contador começa em `1`.
- `random` não adiciona sufixo aleatório nesta modalidade: a sequência permanece crescente para que o prefixo e o contador formem identificadores previsíveis.

```yaml
- name: name
  type: string
  prefix: card_
  seed: "0001"
  random: true
```

`prefix` e `seed` do contador são usados somente quando `values` não tem itens. Se `values` estiver preenchido, cada linha vem dessa lista; nesse caso, `seed` serve para reproduzir os sorteios quando `random: true`, e `prefix` não é aplicado.

Para tipos numéricos com `random: true`, `seed` controla a sequência pseudoaleatória e `min`/`max` definem o intervalo. Com `random: false`, números são gerados em sequência a partir de `min`; `seed` não altera essa sequência.

Exemplo de sorteio reproduzível entre valores permitidos:

```yaml
- name: attribute
  type: string
  values: [DARK, LIGHT, EARTH, WATER, FIRE, WIND]
  seed: 123
  random: true
```

Exemplo de valores em sequência, sem sorteio:

```yaml
- name: attribute
  type: string
  values: [DARK, LIGHT, EARTH]
  random: false
```

Para `size: 5`, o resultado será `DARK`, `LIGHT`, `EARTH`, `DARK`, `LIGHT`.

### Coluna `string` gerada em sequência

Quando uma coluna `string` não tem `values` (ou usa `values: []`), o gerador monta o texto com `prefix` e um contador iniciado em `seed`. Essa geração é sequencial mesmo se `random: true`; não são acrescentados caracteres aleatórios. Aqui, `seed` é o número inicial do contador, e não o seed do sorteio.

```yaml
- name: name
  type: string
  prefix: card_
  seed: 1
  random: true
```

Com `size: 100`, os valores vão de `card_1` a `card_100`.

Para manter zeros à esquerda, coloque o seed entre aspas:

```yaml
seed: "0001"
```

Com `size: 1000`, os valores vão de `card_0001` a `card_1000`. O `prefix` controla o texto (`card_`); o `seed` controla o primeiro número.

Se `prefix` for omitido, o nome da coluna será usado como prefixo. Se `seed` for omitido, a sequência começa em `1`. Essa regra sequencial só se aplica quando não há itens em `values`.

### Coluna `values`

`values` define valores permitidos para a coluna. Quando a lista contém itens:

- `random: true`: escolhe aleatoriamente entre os itens. `seed` controla a sequência sorteada e permite reproduzi-la. O `prefix` não é aplicado quando `values` tem itens.
- `random: false`: percorre os itens em ordem e reinicia a lista quando necessário para preencher `size`.

Se `values` estiver vazio ou não existir, o gerador cria valores automaticamente conforme o tipo da coluna.

### Tipos automáticos

- `string`: gera valores sequenciais usando `prefix` e `seed`.
- `int`: com `random: true`, sorteia entre `min` e `max` (padrão: 0 a 100000), usando `seed` como seed do sorteio. Com `random: false`, gera uma sequência crescente iniciada em `min` (padrão: 0).
- `float`: sorteia entre `min` e `max` quando `random: true`; sem aleatoriedade, incrementa a partir de `min`, usando `step` (padrão: 1). `decimal_places` define as casas decimais (padrão: 2).
- `bool`: gera `true`/`false`; com `random: false`, alterna entre eles.

## Gerar os CSVs

Abra o PowerShell na raiz do projeto, onde está o `docker-compose.yml`. Construa e recrie o container:

```powershell
docker compose up -d --build --force-recreate aws-glue-local
```

Confirme que os arquivos estão visíveis no caminho montado:

```powershell
docker compose exec aws-glue-local ls -la /home/hadoop/workspace/local
```

Gere os dados:

```powershell
docker compose exec aws-glue-local python /home/hadoop/workspace/local/generate_local_data.py --config /home/hadoop/workspace/local/local_data.yaml
```

O script informa o caminho de cada CSV criado. Ao rodar novamente com a mesma configuração e os mesmos seeds, os valores aleatórios são reproduzíveis; cada arquivo CSV existente é sobrescrito.

## Relação com o job AWS Glue

O gerador cria arquivos CSV locais. O `app/src/main.py` do projeto lê a tabela `db_cards.cards` pelo AWS Glue Data Catalog e grava Parquet no S3; ele não lê automaticamente os CSVs gerados aqui. Para usar os CSVs como entrada do job local, o extrator precisa ser configurado para ler o caminho local, em vez do Data Catalog.


## Extra

```powershell
docker compose exec aws-glue-local python -m app.src.main `
  --JOB_NAME local `
  --S3_OUTPUT_PATH s3://SEU-BUCKET/caminho-de-teste `
  --KMS_KEY_ID arn:aws:kms:sa-east-1:SEU_ACCOUNT_ID:key/SUA_CHAVE `
  --TODAY_PARTITION_DATE 20260926 `
  --ONE_DAY_BEFORE_PARTITION_DATE 20260925
```