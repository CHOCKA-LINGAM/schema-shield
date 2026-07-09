def classify_schema_diff(diff: dict, old_schema: dict, new_schema: dict) -> dict:
    """
    Classify a schema diff into SAFE, WARNING, and BREAKING changes.

    Parameters
    ----------
    diff : dict
        Output of ``compare_schema``.
    old_schema : dict
        Normalized old schema (used to look up field metadata).
    new_schema : dict
        Normalized new schema (used to look up field metadata).

    Returns
    -------
    dict
        ``{"safe": [...], "warnings": [...], "breaking": [...]}``
    """

    safe = []
    warnings = []
    breaking = []

    # ------------------------------------------------------------------
    # Added fields
    # ------------------------------------------------------------------
    for field in diff["added"]:
        field_info = new_schema[field]
        if field_info["nullable"]:
            safe.append(
                f"Added nullable field '{field}' — defaults to null for existing records"
            )
        else:
            breaking.append(
                f"Added non-nullable field '{field}' — existing records cannot satisfy NOT NULL constraint"
            )

    # ------------------------------------------------------------------
    # Removed fields
    # ------------------------------------------------------------------
    for field in diff["removed"]:
        breaking.append(
            f"Removed field '{field}' — downstream consumers reading this field will fail"
        )

    # ------------------------------------------------------------------
    # Type changes
    # ------------------------------------------------------------------
    for change in diff["type_changed"]:
        breaking.append(
            f"Type changed '{change['field']}': {change['from']} → {change['to']}"
        )

    # ------------------------------------------------------------------
    # Nullable changes
    # ------------------------------------------------------------------
    for change in diff["nullable_changed"]:
        field = change["field"]
        from_val = change["from"]
        to_val = change["to"]

        if from_val is True and to_val is False:
            breaking.append(
                f"Nullable tightened '{field}': True → False — existing null values will violate the constraint"
            )
        else:
            warnings.append(
                f"Nullable relaxed '{field}': False → True — downstream may receive unexpected nulls"
            )

    return {"safe": safe, "warnings": warnings, "breaking": breaking}