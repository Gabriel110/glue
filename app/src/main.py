import sys
import logging

from app.utils.data_extractor import CardExtractor
from app.utils.data_loader import DataLoader
from app.utils.data_transformer import DataTransformer
from app.utils.job_config import JobConfig

table_name = "yugioh_card"

def configure_logger() -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(handler)

    return logger


def extract_dataframes(config: JobConfig, logger: logging.Logger) -> dict:
    logger.info("Extracting Card data")
    card_df = CardExtractor(config.glue_context, config.one_day_before_partition_date, logger).extract()

    return {
        "card": card_df
    }


def main():
    logger = configure_logger()
    logger.info("Starting Glue job: xxxx")

    try:
        config = JobConfig.build()
        logger.info(
            f"Job config: today_partition_date={config.today_partition_date}, "
            f"one_day_before_partition_date={config.one_day_before_partition_date}, "
            f"s3_output_path={config.s3_output_path}"
        )

        dataframes = extract_dataframes(config, logger)

        transformer = DataTransformer(logger)
        result_df = transformer.transform(
            card=dataframes["card"]
        )

        result_df = result_df.cache()

        loader = DataLoader(config.s3_output_path, table_name, config.today_partition_date, logger)
        loader.load(result_df)

        logger.info("Glue job completed successfully")

    except Exception as e:
        logger.error(f"Unexpected error ended with the exception: {e}")
        raise


if __name__ == "__main__":
    main()

