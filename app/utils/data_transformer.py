from logging import Logger

from pyspark.sql import DataFrame, functions as F


class DataTransformer:

    def __init__(self, logger: Logger):
        self.logger = logger

    def transform(
        self,
        card: DataFrame
    ) -> DataFrame:
        self.logger.info("Starting data transformation")

        base_df = self._build_base_dataframe(
            card
        )
        self.logger.info("Data transformation completed successfully")
        return base_df

    def _build_base_dataframe(
        self,
        card: DataFrame
    ) -> DataFrame:
        self.logger.info("Filtering for cards with an attack greater than 2000.")
        base_df = card.filter(F.col("atk") > 2000)

        return base_df
