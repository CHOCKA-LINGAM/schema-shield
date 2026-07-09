from __future__ import annotations

import json
from typing import Literal, Union

from schema_guard.core.normalize import normalize_schema
from schema_guard.core.compare import compare_schema
from schema_guard.core.classify import classify_schema_diff

# Output format type alias
OutputFormat = Literal["text", "json", "dict"]

_DIVIDER = "─" * 52


def check_schema_transfer(old_schema: dict, new_schema: dict) -> dict:
    """
    Run the full transfer compatibility pipeline:
    ``normalize → compare → classify``.

    Parameters
    ----------
    old_schema : dict or StructType
        The baseline (source) schema.
    new_schema : dict or StructType
        The evolved (target) schema.

    Returns
    -------
    dict
        ``{"schema_diff": {...}, "classification": {...}}``
    """
    old_normalized = normalize_schema(old_schema)
    new_normalized = normalize_schema(new_schema)

    schema_diff = compare_schema(old_normalized, new_normalized)
    classify_changes = classify_schema_diff(schema_diff, old_normalized, new_normalized)

    return {
        "schema_diff": schema_diff,
        "classification": classify_changes,
    }


def format_result(
    result: dict,
    output_format: OutputFormat = "text",
) -> Union[str, dict]:
    """
    Format the output of :func:`check_schema_transfer`.

    Parameters
    ----------
    result : dict
        Return value of ``check_schema_transfer``.
    output_format : {"text", "json", "dict"}
        - ``"text"`` *(default)* — human-readable report string.
        - ``"json"`` — JSON string of the full result dict.
        - ``"dict"`` — the raw classification dict
          ``{"safe": [...], "warnings": [...], "breaking": [...]}``.

    Returns
    -------
    str or dict
        Formatted report in the requested format.

    Raises
    ------
    ValueError
        If *output_format* is not one of the supported values.
    """
    if output_format == "dict":
        return result["classification"]

    if output_format == "json":
        return json.dumps(result, indent=2)

    if output_format != "text":
        raise ValueError(
            f"Unsupported output_format '{output_format}'. "
            "Choose from: 'text', 'json', 'dict'."
        )

    # ------------------------------------------------------------------
    # Text format — structured, human-readable report
    # ------------------------------------------------------------------
    classification = result["classification"]
    total_changes = sum(len(v) for v in classification.values())

    lines = [
        _DIVIDER,
        "  Schema Shield — Compatibility Report",
        _DIVIDER,
    ]

    if total_changes == 0:
        lines.append("")
        lines.append("  ✅  No schema differences detected. Schemas are compatible.")
        lines.append(_DIVIDER)
        return "\n".join(lines)

    def _section(label: str, items: list[str]) -> None:
        count = len(items)
        lines.append("")
        lines.append(f"{label}  ({count} change{'s' if count != 1 else ''})")
        for msg in items:
            lines.append(f"    • {msg}")

    if classification["safe"]:
        _section("✅  SAFE", classification["safe"])

    if classification["warnings"]:
        _section("⚠️   WARNINGS", classification["warnings"])

    if classification["breaking"]:
        _section("💥  BREAKING", classification["breaking"])

    lines.append("")
    lines.append(_DIVIDER)
    return "\n".join(lines)


def compare_tables(spark, source_table: str, target_table: str) -> dict:
    """
    Compare the schemas of two live Spark / Databricks tables.

    Parameters
    ----------
    spark : SparkSession
        Active SparkSession.
    source_table : str
        Fully-qualified source table name.
    target_table : str
        Fully-qualified target table name.

    Returns
    -------
    dict
        Same shape as :func:`check_schema_transfer`.
    """
    source_schema = spark.table(source_table).schema
    target_schema = spark.table(target_table).schema

    return check_schema_transfer(source_schema, target_schema)
