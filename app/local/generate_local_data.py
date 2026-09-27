from __future__ import annotations

import argparse
import csv
import hashlib
import random
from pathlib import Path
from typing import Any

import yaml

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_DIR / "local_data.yml"


def stable_seed(seed: Any, database: str, table: str, column: str) -> int:
    value = f"{seed!r}:{database}:{table}:{column}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(value).digest()[:8], "big")


def make_value(column: dict[str, Any], row_index: int, rng: random.Random) -> Any:
    name = str(column["name"])
    kind = str(column.get("type", "string")).lower()
    randomize = bool(column.get("random", False))
    values = column.get("values")

    # Explicit values are used as a pool: randomly sampled when random=true,
    # or cycled in order when random=false. Empty/missing values means generate.
    if values:
        if not isinstance(values, list):
            raise ValueError(f"A coluna {name}: 'values' deve ser uma lista")
        return rng.choice(values) if randomize else values[row_index % len(values)]

    if kind in {"string", "str", "text"}:
        prefix = str(column.get("prefix", f"{name}_"))
        start_value = column.get("seed", 1)
        start_text = str(start_value)
        if not start_text.isdigit():
            raise ValueError(
                f"A coluna string {name}: seed deve ser um número inicial, por exemplo 1 ou '0001'"
            )
        width = len(start_text) if isinstance(start_value, str) else 1
        number = int(start_value) + row_index
        return f"{prefix}{number:0{width}d}"

    if kind in {"int", "integer", "long"}:
        minimum = int(column.get("min", 0))
        maximum = int(column.get("max", 100000))
        if minimum > maximum:
            raise ValueError(f"A coluna {name}: min não pode ser maior que max")
        if randomize:
            return rng.randint(minimum, maximum)
        value = minimum + row_index
        if value > maximum:
            raise ValueError(f"A coluna {name}: intervalo min/max insuficiente para {row_index + 1} linhas")
        return value

    if kind in {"float", "double", "decimal"}:
        minimum = float(column.get("min", 0))
        maximum = float(column.get("max", 100000))
        if minimum > maximum:
            raise ValueError(f"A coluna {name}: min não pode ser maior que max")
        places = int(column.get("decimal_places", 2))
        if randomize:
            return round(rng.uniform(minimum, maximum), places)
        value = minimum + row_index * float(column.get("step", 1))
        if value > maximum:
            raise ValueError(f"A coluna {name}: intervalo min/max insuficiente para {row_index + 1} linhas")
        return round(value, places)

    if kind in {"bool", "boolean"}:
        return rng.choice([False, True]) if randomize else bool(row_index % 2)

    raise ValueError(f"Tipo não suportado '{kind}' na coluna '{name}'")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    if not isinstance(config, dict):
        raise ValueError("O YAML deve conter 'path' e uma lista 'data'")
    if not isinstance(config.get("data"), list) or not config["data"]:
        raise ValueError("Informe ao menos uma tabela na lista 'data'")
    return config


def generate(config_path: Path) -> None:
    config_path = config_path.resolve()
    config = load_config(config_path)
    configured_path = Path(config.get("path", "data/local/input"))
    output_root = configured_path if configured_path.is_absolute() else config_path.parent / configured_path
    output_root = output_root.resolve()

    for table in config["data"]:
        database = str(table["database"])
        table_name = str(table["table"])
        size = int(table["size"])
        columns = table.get("columns", table.get("coluns"))
        if size < 0:
            raise ValueError(f"{database}.{table_name}: size não pode ser negativo")
        if not isinstance(columns, list) or not columns:
            raise ValueError(f"{database}.{table_name}: informe 'columns' como lista")

        column_names = [str(column["name"]) for column in columns]
        if len(column_names) != len(set(column_names)):
            raise ValueError(f"{database}.{table_name}: há nomes de coluna duplicados")

        output_file = output_root / database / f"{table_name}.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        column_rngs = [
            random.Random(stable_seed(column.get("seed", 0), database, table_name, str(column["name"])))
            for column in columns
        ]
        with output_file.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(column_names)
            for row_index in range(size):
                writer.writerow([
                    make_value(column, row_index, rng)
                    for column, rng in zip(columns, column_rngs)
                ])
        print(f"{database}.{table_name}: {size} linhas -> {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera dados CSV locais a partir de um YAML")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Caminho do YAML")
    args = parser.parse_args()
    generate(args.config)


if __name__ == "__main__":
    main()
