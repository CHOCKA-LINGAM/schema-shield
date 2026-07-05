def normalize_schema(schema) -> dict:
    """
    Normalize a schema into internal format::

        {
            "field_name": {
                "type": "string",
                "nullable": True
            }
        }

    Supports:

    - Python ``dict`` / JSON-style schema
    - Spark ``StructType`` (or any object with a ``.fields`` attribute)

    Parameters
    ----------
    schema : dict or StructType
        The schema to normalize.

    Returns
    -------
    dict
        Normalized field map.

    Raises
    ------
    ValueError
        If *schema* is ``None``, a field is missing a ``"type"`` key, or the
        schema format is not recognized.
    """

    if schema is None:
        raise ValueError("Schema cannot be None.")

    # ------------------------------------------------------------------
    # Case 1: Python dict / JSON-style schema
    # ------------------------------------------------------------------
    if isinstance(schema, dict):
        normalized = {}

        for field_name, field_info in schema.items():
            if not isinstance(field_info, dict):
                raise ValueError(
                    f"Field '{field_name}' must be a dict with 'type' and optional "
                    f"'nullable' keys, got {type(field_info).__name__}."
                )

            field_type = field_info.get("type")
            if field_type is None:
                raise ValueError(
                    f"Field '{field_name}' is missing the required 'type' key."
                )

            nullable = field_info.get("nullable", True)

            normalized[field_name] = {
                "type": str(field_type).lower(),
                "nullable": bool(nullable),
            }

        return normalized

    # ------------------------------------------------------------------
    # Case 2: Spark StructType-like object (has .fields iterable)
    # ------------------------------------------------------------------
    if hasattr(schema, "fields"):
        normalized = {}

        for field in schema.fields:
            normalized[field.name] = {
                "type": field.dataType.simpleString().lower(),
                "nullable": bool(field.nullable),
            }

        return normalized

    raise ValueError(
        f"Unsupported schema format: {type(schema).__name__}. "
        "Expected a dict or a Spark StructType."
    )