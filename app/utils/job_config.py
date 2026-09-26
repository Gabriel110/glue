import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark import conf


BRASILIA_TZ = ZoneInfo("America/Sao_Paulo")
DAYS_OFFSET = 1


@dataclass
class JobConfig:
    job_name: str
    s3_output_path: str
    today_partition_date: str
    one_day_before_partition_date: str
    glue_context: GlueContext

    @classmethod
    def build(cls) -> "JobConfig":
        args = getResolvedOptions(
            sys.argv,
            ["JOB_NAME", "S3_OUTPUT_PATH", "KMS_KEY_ID"],
        )

        spark_conf = conf.SparkConf().setAll(
            [
                ("spark.hadoop.fs.s3.enableServerSideEncryption", "true"),
                ("spark.hadoop.fs.s3.serverSideEncryption.kms.keyId", args["KMS_KEY_ID"])
            ]
        )
        sc = SparkContext(conf=spark_conf)
        glue_context = GlueContext(sc)

        try:
            date_args = getResolvedOptions(
                sys.argv,
                ["ONE_DAY_BEFORE_PARTITION_DATE", "TODAY_PARTITION_DATE"],
            )

            return cls(
                job_name=args["JOB_NAME"],
                s3_output_path=args["S3_OUTPUT_PATH"],
                today_partition_date=date_args["TODAY_PARTITION_DATE"],
                one_day_before_partition_date=date_args["ONE_DAY_BEFORE_PARTITION_DATE"],
                glue_context=glue_context,
            )
        except Exception:
            one_day_before_partition_date, today_partition_date = _calculate_partitions_dates()

            return cls(
                job_name=args["JOB_NAME"],
                s3_output_path=args["S3_OUTPUT_PATH"],
                today_partition_date=today_partition_date,
                one_day_before_partition_date=one_day_before_partition_date,
                glue_context=glue_context,
            )


def _calculate_partitions_dates() -> str:
    today = datetime.now(BRASILIA_TZ)
    one_day_before = today - timedelta(days=DAYS_OFFSET)
    return one_day_before.strftime("%Y%m%d"), today.strftime("%Y%m%d")
