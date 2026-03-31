from schema_guard.normailze import normalize_schema
from schema_guard.compare import compare_schema
from schema_guard.classify import classify_schema_diff
from schema_guard.report import check_schema_transfer,format_result
from schema_guard.report import compare_tables
import pytest

old_schema = {"id" : {"type":"STRING","nullable":True},"amount":{"type":"Double"},"mode":{"type":"STRING"}}
new_schema = {"id" : {"type":"STRING","nullable":True},"amount":{"type":"int","nullable":False},"country":{"type":"STRING","nullable":True}}

def test_normalize_schema():
    schema = {"id" : {"type":"STRING","nullable":True},"amount":{"type":"Double"}}
    
    result = normalize_schema(schema)

    assert result["id"]["type"] == "string"
    assert result["amount"]["type"] == "double"
    assert result["amount"]["nullable"] is True

# def test_normalize_schema_invalid_input():
#     # Error path: schema must be a dict
#     with pytest.raises(ValueError, match="Schema cannot be None"):
#         normalize_schema("dict")


def test_compare_schema():
    

    result = compare_schema(old_schema,new_schema)
    assert result["added"] == ["country"]
    assert result["removed"] == ["mode"]
    assert result["type_changed"][0]["field"] == "amount"
    assert result["nullable_changed"][0]["field"] == "amount"

def test_compare_schema():
    old_normalized_schema = normalize_schema(old_schema)
    new_normalized_schema = normalize_schema(new_schema)
    result = compare_schema(old_normalized_schema,new_normalized_schema)
    result = classify_schema_diff(result,old_normalized_schema,new_normalized_schema)
    assert result["safe"][0] == "Added nullable field : country"
    assert result["breaking"][0] == "Removed field : mode"
    assert result["warnings"][0] == "Type changed for amount from double to int"

def test_schema_transfer():
    

    result = check_schema_transfer(old_schema, new_schema)
    assert result["schema_diff"]["added"] == ["country"]
    assert result["schema_diff"]["removed"] == ["mode"]
    assert result["schema_diff"]["type_changed"][0]["field"] == "amount"
    assert result["schema_diff"]["nullable_changed"][0]["field"] == "amount"
    assert result["classification"]["safe"][0] == "Added nullable field : country"
    assert result["classification"]["breaking"][0] == "Removed field : mode"
    assert result["classification"]["warnings"][0] == "Type changed for amount from double to int"




def test_format_report():
    

    result = check_schema_transfer(old_schema, new_schema)
    report = format_result(result)

    assert "Transfer compatibility report" in report
    assert "SAFE" in report
    assert "WARNINGS" in report
    assert "BREAKING" in report

def test_normalize_spark_like_schema():
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

    schema = MockStructType([
        MockField("id", True),
        MockField("name", False)
    ])

    result = normalize_schema(schema)

    assert result["id"]["type"] == "string"
    assert result["id"]["nullable"] is True
    assert result["name"]["nullable"] is False

def test_compare_tables():
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
        def table(self, table_name):
            if table_name == "dev.sales":
                return MockTable(MockStructType([
                    MockField("id", True),
                    MockField("amount", True)
                ]))
            elif table_name == "prod.sales":
                return MockTable(MockStructType([
                    MockField("id", False),
                    MockField("amount", True),
                    MockField("country", True)
                ]))
            else:
                raise ValueError("Unknown table")

    spark = MockSpark()

    result = compare_tables(spark, "dev.sales", "prod.sales")

    assert "classification" in result
    assert len(result["classification"]["safe"]) == 1
    assert len(result["classification"]["breaking"]) == 1