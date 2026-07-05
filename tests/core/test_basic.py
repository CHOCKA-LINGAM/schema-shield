from schema_guard.core.normalize import normalize_schema
from schema_guard.core.compare import compare_schema
from schema_guard.core.classify import classify_schema_diff
import pytest


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
        assert result["safe"][0] == "Added nullable field : country"

    def test_classifies_removed_field_as_breaking(self):
        old_norm = normalize_schema(OLD_SCHEMA)
        new_norm = normalize_schema(NEW_SCHEMA)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        assert any("mode" in msg for msg in result["breaking"])

    def test_classifies_nullable_true_to_false_as_breaking(self):
        old = {"col": {"type": "string", "nullable": True}}
        new = {"col": {"type": "string", "nullable": False}}
        old_norm = normalize_schema(old)
        new_norm = normalize_schema(new)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        assert any("col" in msg for msg in result["breaking"])

    def test_classifies_nullable_false_to_true_as_warning(self):
        old = {"col": {"type": "string", "nullable": False}}
        new = {"col": {"type": "string", "nullable": True}}
        old_norm = normalize_schema(old)
        new_norm = normalize_schema(new)
        diff = compare_schema(old_norm, new_norm)
        result = classify_schema_diff(diff, old_norm, new_norm)
        assert any("col" in msg for msg in result["warnings"])

    def test_no_changes_returns_empty_lists(self):
        schema = normalize_schema({"id": {"type": "string", "nullable": True}})
        diff = compare_schema(schema, schema)
        result = classify_schema_diff(diff, schema, schema)
        assert result == {"safe": [], "warnings": [], "breaking": []}


# ---------------------------------------------------------------------------
# check_schema_transfer & format_result (integration)
# ---------------------------------------------------------------------------

from schema_guard.core.report import check_schema_transfer, format_result


class TestSchemaTransfer:

    def test_full_pipeline_diff_keys(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        assert result["schema_diff"]["added"] == ["country"]
        assert result["schema_diff"]["removed"] == ["mode"]
        assert result["schema_diff"]["type_changed"][0]["field"] == "amount"

    def test_format_result_contains_sections(self):
        result = check_schema_transfer(OLD_SCHEMA, NEW_SCHEMA)
        report = format_result(result)
        assert "Transfer compatibility report" in report
        assert "SAFE" in report
        assert "WARNINGS" in report
        assert "BREAKING" in report

    def test_format_result_no_diff_message(self):
        schema = {"id": {"type": "string", "nullable": True}}
        result = check_schema_transfer(schema, schema)
        report = format_result(result)
        assert "No schema differences detected." in report


# ---------------------------------------------------------------------------
# compare_tables (Spark mock)
# ---------------------------------------------------------------------------

from schema_guard.core.report import compare_tables


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

    def test_compare_tables_returns_classification(self):
        spark = self._make_spark()
        result = compare_tables(spark, "dev.sales", "prod.sales")
        assert "classification" in result

    def test_compare_tables_safe_count(self):
        spark = self._make_spark()
        result = compare_tables(spark, "dev.sales", "prod.sales")
        assert len(result["classification"]["safe"]) == 1

    def test_compare_tables_breaking_count(self):
        spark = self._make_spark()
        result = compare_tables(spark, "dev.sales", "prod.sales")
        assert len(result["classification"]["breaking"]) == 1