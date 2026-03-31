# Schema Guard

Schema Guard is a lightweight Python utility for **schema compatibility validation** and **transfer safety checks** in data pipelines.

It helps answer a practical question:

> **What changed between two schemas — and will this break my pipeline or transfer?**

---

## Why Schema Guard?

Most schema diff tools can tell you:

- what fields were added
- what fields were removed
- what changed

But data engineers often need one more answer:

> **Is this change safe, risky, or breaking?**

Schema Guard is built to provide that classification layer.

---

## Features

- Normalize schemas into a common internal format
- Compare schema differences
- Detect:
  - added fields
  - removed fields
  - type changes
  - nullable changes
- Classify changes into:
  - SAFE
  - WARNING
  - BREAKING
- Generate human-readable compatibility reports
- Support:
  - Python dict / JSON schemas
  - Spark-like schemas
  - Spark / Databricks table comparison helpers

---

## Installation

### Local editable install

```bash
pip install -e .