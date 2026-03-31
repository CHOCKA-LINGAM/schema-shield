def classify_schema_diff(diff:dict, old_schema:dict, new_schema: dict)-> dict:

    safe = []
    warnings = []
    breaking = []
    for field in diff["added"]:
        field_info = new_schema[field]

        if field_info["nullable"] == True:
            safe.append(f"Added nullable field : {field}")
        else:
            breaking.append(f"Added non-nullable field : {field}")
        
    for field in diff["removed"]:
        breaking.append(f"Removed field : {field}")
    
    for field in diff["type_changed"]:
        warnings.append(f"Type changed for {field["field"]} from {field["from"]} to {field["to"]}")
        
    for field in diff["nullable_changed"]:
        if field["from"] is True and field["to"] is False:
            breaking.append(f"Type changed for {field["field"]} from {field["from"]} to {field["to"]}")
        else:
            warnings.append(f"Type changed for {field["field"]} from {field["from"]} to {field["to"]}")

    return {"safe":safe,"warnings":warnings,"breaking":breaking}