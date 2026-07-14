import json
import pytest

from schema_shield.core.normalize import normalize_schema
from schema_shield.core.compare import compare_schema
from schema_shield.core.classify import classify_schema_diff
from schema_shield.core.report import check_schema_transfer, format_result, compare_tables


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

OLD_SCHEMA = {
    "id":     {"type": "STRING", "nullable": False},
    "amount": {"type": "Double", "nullable": True},
    "mode":   {"type": "STRING"},
}

NEW_SCHEMA = {
    "id":      {"type": "STRING",  "nullable": True},
    "amount":  {"type": "int",     "nullable": False},
    "country": {"type": "STRING",  "nullable": True},
}


# ---------------------------------------------------------------------------
# normalize_schema
# ---------------------------------------------------------------------------

class TestNormalizeSchema:

    def test_lowercases_types(self):
        schema = {"id": {"type": "STRING", "nullable": True}, "amount": {"type": "Double"}}
        result = normalize_schema(schema)
        assert result["id"]["type"] == "string"
        assert result["amount"]["type"] == "double"

    def test_defaults_nullable_to_true(self):
        schema = {"amount": {"type": "Double"}}
        result = normalize_schema(schema)
        assert result["amount"]["nullable"] is True

    def test_explicit_nullable_false(self):
        schema = {"id": {"type": "string", "nullable": False}}
        result = normalize_schema(schema)
        assert result["id"]["nullable"] is False

    def test_raises_on_none_schema(self):
        with pytest.raises(ValueError, match="Schema cannot be None"):
            normalize_schema(None)

    def test_raises_on_missing_type_key(self):
        schema = {"id": {"nullable": True}}
        with pytest.raises(ValueError, match="missing the required 'type' key"):
            normalize_schema(schema)

    def test_raises_on_non_dict_field(self):
        schema = {"id": "string"}
        with pytest.raises(ValueError, match="must be a dict"):
            normalize_schema(schema)

    def test_raises_on_unsupported_format(self):
        with pytest.raises(ValueError, match="Unsupported schema format"):
            normalize_schema("not_a_schema")

    def test_spark_like_schema(self):
        class MockDataType:
            def simpleString(self):
                return "STRING"

        class MockField:
            def __init__(self, name, nullable):
                self.name = name
                self.dataType = MockDataType()
                self.nullable = nullable

        class MockStructType:
            def __init__(self, fields):
                self.fields = fields

        schema = MockStructType([MockField("id", True), MockField("name", False)])
        result = normalize_schema(schema)
        assert result["id"]["type"] == "string"
        assert result["id"]["nullable"] is True
        assert result["name"]["nullable"] is False


# ---------------------------------------------------------------------------
# compare_schema
# ---------------------------------------------------------------------------

class TestCompareSchema:

    def test_detects_added_and_removed_fields(self):
        result = compare_schema(OLD_SCHEMA, NEW_SCHEMA)
        assert result["added"] == ["country"]
        assert result["removed"] == ["mode"]

    def test_detects_type_change(self):
        result = compare_schema(OLD_SCHEMA, NEW_SCHEMA)
        assert result["type_changed"][0]["field"] == "amount"

    def test_detects_nullable_change(self):
        result = compare_schema(OLD_SCHEMA, NEW_SCHEMA)
        changed_fields = [c["field"] for c in result["nullable_changed"]]
        assert "amount" in changed_fields
        assert "id" in changed_fields

    def test_no_diff_on_identical_schemas(self):
        schema = {"id": {"type": "string", "nullable": True}}
        result = compare_schema(schema, schema)
        assert result["added"] == []
        assert result["removed"] == []
        assert result["type_changed"] == []
        assert result["nullable_changed"] == []


# ---------------------------------------------------------------------------
# classify_schema_diff
# ---------------------------------------------------------------------------

class TestClassifySchema:

    def test_classifies_nullable_addition_as_safe(self):
        old_norm = normalize_schema(OLD_SCHEMA)
        new_norm = normalize_schema(NEW_SCHEMA)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        # Must mention the field name and land in safe
        assert any("country" in msg for msg in result["safe"])

    def test_safe_message_format(self):
        old_norm = normalize_schema(OLD_SCHEMA)
        new_norm = normalize_schema(NEW_SCHEMA)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        safe_msg = next(m for m in result["safe"] if "country" in m)
        assert "nullable" in safe_msg.lower()

    def test_classifies_removed_field_as_breaking(self):
        old_norm = normalize_schema(OLD_SCHEMA)
        new_norm = normalize_schema(NEW_SCHEMA)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        assert any("mode" in msg for msg in result["breaking"])

    def test_removed_field_message_format(self):
        old = {"col": {"type": "string", "nullable": True}}
        new = {}
        old_norm = normalize_schema(old)
        new_norm = {"__dummy__": {"type": "string", "nullable": True}}
        diff = {"added": ["__dummy__"], "removed": ["col"], "type_changed": [], "nullable_changed": []}
        result = classify_schema_diff(diff, old_norm, new_norm)
        msg = next(m for m in result["breaking"] if "col" in m)
        assert "Removed" in msg

    def test_classifies_type_change_as_breaking(self):
        old_norm = normalize_schema(OLD_SCHEMA)
        new_norm = normalize_schema(NEW_SCHEMA)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        assert any("amount" in msg for msg in result["breaking"])

    def test_type_change_message_uses_arrow(self):
        old = {"col": {"type": "double", "nullable": True}}
        new = {"col": {"type": "string", "nullable": True}}
        old_norm = normalize_schema(old)
        new_norm = normalize_schema(new)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        msg = next(m for m in result["breaking"] if "col" in m)
        assert "→" in msg
        assert "double" in msg
        assert "string" in msg

    def test_classifies_nullable_true_to_false_as_breaking(self):
        old = {"col": {"type": "string", "nullable": True}}
        new = {"col": {"type": "string", "nullable": False}}
        old_norm = normalize_schema(old)
        new_norm = normalize_schema(new)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        assert any("col" in msg for msg in result["breaking"])

    def test_nullable_tightened_message_uses_arrow(self):
        old = {"col": {"type": "string", "nullable": True}}
        new = {"col": {"type": "string", "nullable": False}}
        old_norm = normalize_schema(old)
        new_norm = normalize_schema(new)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        msg = next(m for m in result["breaking"] if "col" in m)
        assert "→" in msg

    def test_classifies_nullable_false_to_true_as_warning(self):
        old = {"col": {"type": "string", "nullable": False}}
        new = {"col": {"type": "string", "nullable": True}}
        old_norm = normalize_schema(old)
        new_norm = normalize_schema(new)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        assert any("col" in msg for msg in result["warnings"])

    def test_nullable_relaxed_message_uses_arrow(self):
        old = {"col": {"type": "string", "nullable": False}}
        new = {"col": {"type": "string", "nullable": True}}
        old_norm = normalize_schema(old)
        new_norm = normalize_schema(new)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        msg = next(m for m in result["warnings"] if "col" in m)
        assert "→" in msg

    def test_non_nullable_added_field_is_breaking(self):
        old = {"id": {"type": "string", "nullable": True}}
        new = {"id": {"type": "string", "nullable": True}, "required_col": {"type": "string", "nullable": False}}
        old_norm = normalize_schema(old)
        new_norm = normalize_schema(new)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        assert any("required_col" in msg for msg in result["breaking"])

    def test_no_changes_returns_empty_lists(self):
        schema = normalize_schema({"id": {"type": "string", "nullable": True}})
        diff = compare_schema(schema, schema)
        result = classify_schema_diff(diff, schema, schema)
        assert result == {"safe": [], "warnings": [], "breaking": []}


# ---------------------------------------------------------------------------
# check_schema_transfer & format_result — text format
# ---------------------------------------------------------------------------

class TestSchemaTransfer:

    def test_full_pipeline_diff_keys(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        assert result["schema_diff"]["added"] == ["country"]
        assert result["schema_diff"]["removed"] == ["mode"]
        assert result["schema_diff"]["type_changed"][0]["field"] == "amount"

    def test_format_text_contains_header(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        report = format_result(result)
        assert "Schema Shield" in report
        assert "Compatibility Report" in report

    def test_format_text_contains_safe_section(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        report = format_result(result)
        assert "SAFE" in report

    def test_format_text_contains_warnings_section(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        report = format_result(result)
        assert "WARNINGS" in report

    def test_format_text_contains_breaking_section(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        report = format_result(result)
        assert "BREAKING" in report

    def test_format_text_shows_change_counts(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        report = format_result(result)
        # Each section header should show a count in parentheses
        assert "change" in report

    def test_format_text_no_diff_message(self):
        schema = {"id": {"type": "string", "nullable": True}}
        result = check_schema_transfer(schema, schema)
        report = format_result(result)
        assert "No schema differences detected" in report

    def test_format_text_default_is_text(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        assert format_result(result) == format_result(result, output_format="text")


# ---------------------------------------------------------------------------
# format_result — json format
# ---------------------------------------------------------------------------

class TestFormatResultJson:

    def test_returns_valid_json_string(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        output = format_result(result, output_format="json")
        assert isinstance(output, str)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_json_contains_schema_diff_key(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        parsed = json.loads(format_result(result, output_format="json"))
        assert "schema_diff" in parsed

    def test_json_contains_classification_key(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        parsed = json.loads(format_result(result, output_format="json"))
        assert "classification" in parsed

    def test_json_classification_has_all_buckets(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        parsed = json.loads(format_result(result, output_format="json"))
        cls = parsed["classification"]
        assert "safe" in cls
        assert "warnings" in cls
        assert "breaking" in cls

    def test_json_diff_added_fields(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        parsed = json.loads(format_result(result, output_format="json"))
        assert parsed["schema_diff"]["added"] == ["country"]

    def test_json_no_diff_is_empty_lists(self):
        schema = {"id": {"type": "string", "nullable": True}}
        result = check_schema_transfer(schema, schema)
        parsed = json.loads(format_result(result, output_format="json"))
        cls = parsed["classification"]
        assert cls["safe"] == []
        assert cls["warnings"] == []
        assert cls["breaking"] == []


# ---------------------------------------------------------------------------
# format_result — dict format
# ---------------------------------------------------------------------------

class TestFormatResultDict:

    def test_returns_dict(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        output = format_result(result, output_format="dict")
        assert isinstance(output, dict)

    def test_dict_has_three_buckets(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        output = format_result(result, output_format="dict")
        assert set(output.keys()) == {"safe", "warnings", "breaking"}

    def test_dict_safe_list(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        output = format_result(result, output_format="dict")
        assert isinstance(output["safe"], list)
        assert any("country" in m for m in output["safe"])

    def test_dict_breaking_contains_removed_field(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        output = format_result(result, output_format="dict")
        assert any("mode" in m for m in output["breaking"])

    def test_dict_no_diff_returns_empty_lists(self):
        schema = {"id": {"type": "string", "nullable": True}}
        result = check_schema_transfer(schema, schema)
        output = format_result(result, output_format="dict")
        assert output == {"safe": [], "warnings": [], "breaking": []}

    def test_invalid_format_raises_value_error(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        with pytest.raises(ValueError, match="Unsupported output_format"):
            format_result(result, output_format="xml")


# ---------------------------------------------------------------------------
# compare_tables (Spark mock)
# ---------------------------------------------------------------------------

class TestCompareTables:

    @staticmethod
    def _make_spark():
        class MockDataType:
            def simpleString(self):
                return "string"

        class MockField:
            def __init__(self, name, nullable):
                self.name = name
                self.dataType = MockDataType()
                self.nullable = nullable

        class MockStructType:
            def __init__(self, fields):
                self.fields = fields

        class MockTable:
            def __init__(self, schema):
                self.schema = schema

        class MockSpark:
            def table(self, name):
                if name == "dev.sales":
                    return MockTable(MockStructType([
                        MockField("id", True),
                        MockField("amount", True),
                    ]))
                elif name == "prod.sales":
                    return MockTable(MockStructType([
                        MockField("id", False),
                        MockField("amount", True),
                        MockField("country", True),
                    ]))
                raise ValueError(f"Unknown table: {name}")

        return MockSpark()

    def test_returns_dict_with_classification(self):
        spark = self._make_spark()
        result = compare_tables(spark, "dev.sales", "prod.sales")
        assert "classification" in result

    def test_returns_dict_with_schema_diff(self):
        spark = self._make_spark()
        result = compare_tables(spark, "dev.sales", "prod.sales")
        assert "schema_diff" in result

    def test_safe_count(self):
        spark = self._make_spark()
        result = compare_tables(spark, "dev.sales", "prod.sales")
        assert len(result["classification"]["safe"]) == 1

    def test_breaking_count(self):
        spark = self._make_spark()
        result = compare_tables(spark, "dev.sales", "prod.sales")
        assert len(result["classification"]["breaking"]) == 1

    def test_result_formattable_as_text(self):
        spark = self._make_spark()
        result = compare_tables(spark, "dev.sales", "prod.sales")
        report = format_result(result, output_format="text")
        assert "Schema Shield" in report

    def test_result_formattable_as_json(self):
        spark = self._make_spark()
        result = compare_tables(spark, "dev.sales", "prod.sales")
        output = format_result(result, output_format="json")
        parsed = json.loads(output)
        assert "classification" in parsed