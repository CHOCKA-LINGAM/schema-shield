from schema_guard.normailze import normalize_schema
from schema_guard.compare import compare_schema
from schema_guard.classify import classify_schema_diff

def check_schema_transfer(old_schema:dict, new_schema:dict)->dict:
    """
    Full transfer compatibility check:
    normalize -> compare -> classify
    """
    old_normalized = normalize_schema(old_schema)
    new_normalized = normalize_schema(new_schema)

    schema_diff = compare_schema(old_normalized,new_normalized)

    classify_changes = classify_schema_diff(schema_diff,old_normalized,new_normalized)

    return {
        "schema_diff":schema_diff,
        "classification":classify_changes
    }


def format_result(result:dict)->str:
    """
    Format a human-readable compatibility report.
    """
    classification = result["classification"]
    lines =[]

    lines.append("Transfer compatibility report")

    if classification["safe"]:
        lines.append("SAFE")
        for safe in classification["safe"]:
            lines.append(f"- {safe}")
        lines.append("")
    
    if classification["warnings"]:
        lines.append("WARNINGS")
        for warnings in classification["warnings"]:
            lines.append(f"- {warnings}")
        lines.append("")
    
    if classification["breaking"]:
        lines.append("BREAKING")
        for breakings in classification["breaking"]:
            lines.append(f"- {breakings}")
        lines.append("")
    
    if not any(classification.values()):
        lines.append("No schema differences detected.")

    return "\n".join(lines)

def compare_tables(spark, source_table: str, target_table: str) -> dict:
    """
    Compare two Spark/Databricks tables by schema.
    Reuses the same transfer compatibility engine.
    """

    source_schema = spark.table(source_table).schema
    target_schema = spark.table(target_table).schema

    return check_schema_transfer(source_schema, target_schema)
    
