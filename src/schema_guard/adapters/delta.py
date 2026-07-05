from __future__ import annotations

from typing import Optional, Dict, TYPE_CHECKING
from ..core.report import check_schema_transfer, format_result

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

try:
    import pyspark
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False


class CompareDelta:
    """
    Compare schemas of Delta tables using a live SparkSession.

    Parameters
    ----------
    source_schema : str
        Fully-qualified source table name (e.g. ``"catalog.schema.table"``).
    target_schema : str, optional
        Fully-qualified target table name. Defaults to *source_schema* when
        omitted (useful for version-to-version comparisons on the same table).
    spark_session : SparkSession, optional
        Active SparkSession. Required for all comparison methods.
    """

    def __init__(
        self,
        source_schema: str,
        target_schema: Optional[str] = None,
        spark_session: Optional["SparkSession"] = None,
    ) -> None:
        self.source_schema = source_schema
        self.target_schema = target_schema if target_schema else source_schema
        self.spark = spark_session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_schema(self, table: str, version: Optional[int] = None):
        """
        Return the StructType schema for *table*.

        Parameters
        ----------
        table : str
            Fully-qualified table name.
        version : int, optional
            Delta version to read via ``versionAsOf``. Reads the latest
            version when omitted.
        """
        reader = self.spark.read.format("delta")
        if version is not None:
            reader = reader.option("versionAsOf", version)
        return reader.table(table).schema

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compare_delta_tables(self) -> str:
        """
        Compare the *current* schemas of ``source_schema`` and
        ``target_schema``.

        Returns
        -------
        str
            Human-readable compatibility report.

        Raises
        ------
        EnvironmentError
            If PySpark is not installed.
        """
        if not PYSPARK_AVAILABLE:
            raise EnvironmentError(
                "PySpark is not installed. "
                "Install it with: pip install schema-shield[spark]"
            )

        source_struct = self._read_schema(self.source_schema)
        target_struct = self._read_schema(self.target_schema)

        result = check_schema_transfer(source_struct, target_struct)
        return format_result(result)

    def compare_delta_versions(
        self,
        source_version: int,
        target_version: int,
    ) -> str:
        """
        Compare the schema of ``source_schema`` at two different Delta
        versions.

        This is useful for auditing schema drift across time on a single table,
        or for validating a schema migration before promotion.

        Parameters
        ----------
        source_version : int
            The older (baseline) Delta version to compare from.
        target_version : int
            The newer Delta version to compare to.

        Returns
        -------
        str
            Human-readable compatibility report.

        Raises
        ------
        EnvironmentError
            If PySpark is not installed.
        ValueError
            If ``source_version`` or ``target_version`` is negative.
        """
        if not PYSPARK_AVAILABLE:
            raise EnvironmentError(
                "PySpark is not installed. "
                "Install it with: pip install schema-shield[spark]"
            )

        if source_version < 0 or target_version < 0:
            raise ValueError("Delta version numbers must be non-negative integers.")

        source_struct = self._read_schema(self.source_schema, version=source_version)
        target_struct = self._read_schema(self.target_schema, version=target_version)

        result = check_schema_transfer(source_struct, target_struct)
        return format_result(result)