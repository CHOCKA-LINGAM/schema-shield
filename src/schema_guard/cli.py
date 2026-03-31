import argparse
import json

from schema_guard.report import check_schema_transfer, format_result


def load_schema(file_path: str) -> dict:
    """
    Load schema from a JSON file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Schema Guard - validate schema compatibility and transfer safety"
    )

    subparsers = parser.add_subparsers(dest="command")

    # compare command
    compare_parser = subparsers.add_parser(
        "compare", help="Compare two schema JSON files"
    )
    compare_parser.add_argument("old_schema", help="Path to old/source schema JSON")
    compare_parser.add_argument("new_schema", help="Path to new/target schema JSON")

    args = parser.parse_args()

    if args.command == "compare":
        old_schema = load_schema(args.old_schema)
        new_schema = load_schema(args.new_schema)

        result = check_schema_transfer(old_schema, new_schema)
        report = format_result(result)

        print(report)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()