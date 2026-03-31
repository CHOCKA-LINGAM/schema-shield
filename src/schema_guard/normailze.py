def normalize_schema(schema) -> dict:
    """
    Normalize a schema into internal format:
    {
        "field_name": {
            "type": "string",
            "nullable": True
        }
    }

    Supports:
    - Python dict / JSON schema
    - Spark StructType (if available)
    """

    if schema is None:
        raise ValueError("Schema cannot be None")

    # Case 1: Python dict / JSON-style schema
    if isinstance(schema, dict):
        normalized = {}

        for field_name, field_info in schema.items():
            field_type = field_info.get("type")
            nullable = field_info.get("nullable", True)

            normalized[field_name] = {
                "type": str(field_type).lower(),
                "nullable": bool(nullable)
            }

        return normalized

    # Case 2: Spark StructType-like object
    if hasattr(schema, "fields"):
        normalized = {}

        for field in schema.fields:
            normalized[field.name] = {
                "type": field.dataType.simpleString().lower(),
                "nullable": bool(field.nullable)
            }

        return normalized

    raise ValueError("Unsupported schema format")