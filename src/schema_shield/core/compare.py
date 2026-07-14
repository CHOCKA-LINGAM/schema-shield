from schema_shield.core.normalize import normalize_schema

def compare_schema(old_schema:dict, new_schema:dict)-> dict:
    """
        Compare two schemas and return added and removed fields
    """

    old_fields = set(old_schema.keys())
    new_fields = set(new_schema.keys())

    added_fields = sorted(list(new_fields - old_fields))
    removed_fields = sorted(list(old_fields - new_fields))
    
    common_fields = old_fields.intersection(new_fields)

    type_changed = []
    nullable_changed = []
    for field in common_fields:
        old_field = old_schema[field]
        new_field = new_schema[field]

        if old_field["type"] != new_field["type"]:
            type_changed.append({
                "field" : field,
                "from" : old_field["type"],
                "to" : new_field["type"]
            })
        
        if old_field["nullable"] != new_field["nullable"]:
            nullable_changed.append({
                "field" : field,
                "from" : old_field["nullable"],
                "to" : new_field["nullable"]
            })
    return{
        "added" : added_fields,
        "removed" : removed_fields,
        "type_changed" : type_changed,
        "nullable_changed" : nullable_changed
    }