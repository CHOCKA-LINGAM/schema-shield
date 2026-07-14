# Schema Shield

[![PyPI version](https://img.shields.io/pypi/v/schema-shield)](https://pypi.org/project/schema-shield/)
[![Python](https://img.shields.io/pypi/pyversions/schema-shield)](https://pypi.org/project/schema-shield/)
[![CI](https://github.com/chocka-dev/schema-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/chocka-dev/schema-guard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Schema Shield** classifies schema changes as SAFE, WARNING, or BREAKING — so you know immediately whether a schema evolution is safe to deploy.

> **What changed between two schemas — and will it break my pipeline?**

---

## Why Schema Shield?

Schema diff tools tell you *what* changed. Schema Shield tells you *what it means*.

| Classification | When it applies |
|---|---|
| ✅ **SAFE** | Change is backward-compatible; pipelines continue working |
| ⚠️ **WARNING** | Change is risky; review before deploying |
| 💥 **BREAKING** | Change will cause pipeline failures |

---

## Installation

```bash
# Core
pip install schema-shield

# With PySpark / Delta Lake support
pip install "schema-shield[spark]"

# With Databricks SDK support
pip install "schema-shield[databricks]"
```

---

## Quick Start

```python
from schema_guard import check_schema_transfer, format_result

result = check_schema_transfer(old_schema, new_schema)
print(format_result(result))
```

```
────────────────────────────────────────────────────
  Schema Shield — Compatibility Report
────────────────────────────────────────────────────

✅  SAFE  (1 change)
    • Added nullable field 'country' — defaults to null for existing records

⚠️   WARNINGS  (1 change)
    • Nullable relaxed 'id': False → True — downstream may receive unexpected nulls

💥  BREAKING  (2 changes)
    • Removed field 'mode' — downstream consumers reading this field will fail
    • Type changed 'amount': double → decimal

────────────────────────────────────────────────────
```

---

## Usage

### With Python dict / JSON schemas

Pass schemas as Python dicts. Each field needs a `"type"` key; `"nullable"` defaults to `True`.

```python
from schema_guard import check_schema_transfer, format_result

result = check_schema_transfer(old_schema, new_schema)

# Human-readable report
print(format_result(result))

# JSON string — useful for logging or CI output
print(format_result(result, output_format="json"))

# Raw dict — useful for programmatic checks
classification = format_result(result, output_format="dict")
if classification["breaking"]:
    raise SystemExit("Breaking schema changes detected — deployment blocked.")
```

---

### With the CLI

Compare two JSON schema files directly from your terminal or CI pipeline:

```bash
schema-shield compare old_schema.json new_schema.json
```

**Schema file format:**

```json
{
  "user_id":    { "type": "string",    "nullable": false },
  "revenue":    { "type": "double",    "nullable": true  },
  "created_at": { "type": "timestamp", "nullable": true  }
}
```

---

### With PySpark

Pass a live `SparkSession` and table names — Schema Shield reads the schemas for you:

```python
from schema_guard import compare_tables, format_result

result = compare_tables(spark, "dev.catalog.sales", "prod.catalog.sales")
print(format_result(result))
```

You can also pass PySpark `StructType` objects directly into `check_schema_transfer` — no conversion needed.

---

### With Databricks Delta Lake

Use the `CompareDelta` adapter to compare live Delta tables or audit schema drift across Delta versions:

```python
from schema_guard.adapters.delta import CompareDelta

checker = CompareDelta(
    source_schema="catalog.schema.events",
    target_schema="catalog.schema.events_v2",   # omit to compare versions of same table
    spark_session=spark,
)

# Compare current schemas of two tables
print(checker.compare_delta_tables())

# Compare the same table at two different Delta versions
print(checker.compare_delta_versions(source_version=5, target_version=12))
```

---

## Output Formats

`format_result` supports three output formats:

| Format | Returns | Use case |
|---|---|---|
| `"text"` *(default)* | `str` | Terminal output, logs |
| `"json"` | `str` | CI pipelines, structured logging |
| `"dict"` | `dict` | Programmatic checks, custom reporting |

```python
# Text (default)
format_result(result)
format_result(result, output_format="text")

# JSON string
format_result(result, output_format="json")

# Raw classification dict
format_result(result, output_format="dict")
# → {"safe": [...], "warnings": [...], "breaking": [...]}
```

---

## Supported Schema Types

| Source | How to use |
|---|---|
| Python `dict` | Pass directly to `check_schema_transfer` |
| JSON file | Load with `json.load()`, pass as dict |
| PySpark `StructType` | Pass directly — normalized automatically |
| Delta table (live) | Use `CompareDelta.compare_delta_tables()` |
| Delta table (versions) | Use `CompareDelta.compare_delta_versions()` |
| Spark table name | Use `compare_tables(spark, src, tgt)` |

---

## Classification Rules

| Change | Classification | Reason |
|---|---|---|
| Added nullable field | ✅ SAFE | Existing records unaffected; field defaults to null |
| Added non-nullable field | 💥 BREAKING | Existing records violate the NOT NULL constraint |
| Removed field | 💥 BREAKING | Downstream readers of this field will fail |
| Type changed | 💥 BREAKING | Data cannot be implicitly cast |
| Nullable `True → False` | 💥 BREAKING | Existing nulls violate the new constraint |
| Nullable `False → True` | ⚠️ WARNING | Constraint relaxed; downstream may receive unexpected nulls |

---

## Contributing

```bash
git clone https://github.com/CHOCKA-LINGAM/schema-shield
pip install -e ".[spark]"
pytest
```

Pull requests are welcome. CI runs automatically on all PRs.

---

## License

MIT © [chocka.dev](https://chocka.dev)
