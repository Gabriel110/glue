from abc import ABC, abstractmethod
from logging import Logger

from pyspark.sql import DataFrame, functions as F


class DataExtractor(ABC):

    @abstractmethod
    def extract(self) -> DataFrame:
        raise NotImplementedError

class CardExtractor(DataExtractor):
    DATABASE = "db_cards"
    TABLE_NAME = "cards"
    COLUMNS = [
        "name",
        "level",
        "attribute",
        "type",
        "card_type",
        "effect",
        "atk",
        "defesa"
    ]

    def __init__(self, glue_context, partition_date: str, logger: Logger):
        self.glue_context = glue_context
        self.partition_date = partition_date
        self.logger = logger

    def extract(self) -> DataFrame:
        push_down_predicate = f"anomesdia = {self.partition_date}"

        self.logger.info(
            f"Loading table {self.TABLE_NAME} with predicate: {push_down_predicate}"
        )

        dynamic_frame = self.glue_context.create_dynamic_frame.from_catalog(
            database=self.DATABASE,
            table_name=self.TABLE_NAME,
            push_down_predicate=push_down_predicate,
            additional_options={"columns": self.COLUMNS}
        )

        df = dynamic_frame.toDF()
        df = df.toDF(*[col.lower() for col in df.columns])

        self.logger.info(f"Table {self.TABLE_NAME} loaded successfully")
        return df
