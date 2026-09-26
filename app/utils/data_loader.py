from logging import Logger

from pyspark.sql import DataFrame


class DataLoader:

    def __init__(self, s3_output_path: str, table_name: str, partition_date: str, logger: Logger):
        self.s3_output_path = s3_output_path
        self.partition_date = partition_date
        self.table_name = table_name
        self.logger = logger
        self.target_file_size_gb = 1.0

    def load(self, df: DataFrame) -> None:
        output_path = self._build_partitioned_path()

        self.logger.info(f"Writing parquet to {output_path}")

        record_count = df.count()
        self.logger.info(f"Number of records to write: {record_count}")

        num_partitions = self._calculate_optimal_partitions(df, record_count)

        self.logger.info(
            f"Coalescing to {num_partitions} partition(s) for optimal file size (~{self.target_file_size_gb}GB per file)")

        df.coalesce(num_partitions).write.mode("overwrite").option("compression", "snappy").parquet(output_path)

        self.logger.info(f"Parquet file written successfully to {output_path}")

    def _build_partitioned_path(self) -> str:
        year = self.partition_date[0:4]
        month = self.partition_date[4:6]
        day = self.partition_date[6:8]

        partitioned_path = (
            f"{self.s3_output_path}"
            f"/{self.table_name}"
            f"/year={year}"
            f"/month={month}"
            f"/day={day}"
        )

        self.logger.info(f"Partitioned path: {partitioned_path}")
        return partitioned_path

    def _calculate_optimal_partitions(self, df: DataFrame, record_count: int) -> int:
        avg_compressed_record_size_bytes = 80

        total_size_bytes = avg_compressed_record_size_bytes * record_count
        compressed_size_gb = total_size_bytes / (1024 ** 3)

        self.logger.info(f"Estimated compressed parquet size: {compressed_size_gb:.2f} GB")

        num_partitions = max(1, int(compressed_size_gb / self.target_file_size_gb))

        if compressed_size_gb % self.target_file_size_gb > 0.5:
            num_partitions += 1

        self.logger.info(
            f"Calculated optimal partitions: {num_partitions} (target: {self.target_file_size_gb}GB per file)")

        return num_partitions