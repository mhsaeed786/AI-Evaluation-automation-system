import sys
import json
import argparse
from core.meta.registry import ModuleRegistry
from core.meta.sandbox import SandboxEnvironment
from core.meta.module_author import ModuleAuthor


def main():
    parser = argparse.ArgumentParser(description="OneAgent Meta Core CLI Interface")
    subparsers = parser.add_subparsers(dest="command", help="Meta commands")

    # Author command
    author_parser = subparsers.add_parser("author", help="Author a new module")
    author_parser.add_argument("--name", required=True, help="Module name")
    author_parser.add_argument("--reqs", required=True, help="Requirements & logic description")

    # List command
    list_parser = subparsers.add_parser("list", help="List registered modules")
    list_parser.add_argument("--status", choices=["pending", "approved", "rejected", "reverted"], help="Filter by status")

    # Status update command
    status_parser = subparsers.add_parser("status", help="Update module lifecycle status")
    status_parser.add_argument("--id", required=True, help="Module ID or slug")
    status_parser.add_argument("--status", required=True, choices=["pending", "approved", "rejected", "reverted"], help="New status")

    # Run sandbox command
    run_parser = subparsers.add_parser("run", help="Run a module in sandbox")
    run_parser.add_argument("--id", required=True, help="Module ID or slug")
    run_parser.add_argument("--input", default="{}", help="JSON input string")

    args = parser.parse_args()
    registry = ModuleRegistry()

    if args.command == "author":
        author = ModuleAuthor(registry=registry)
        mod = author.author_module(module_name=args.name, requirements=args.reqs)
        print(json.dumps(mod.to_dict(), indent=2))

    elif args.command == "list":
        mods = registry.list_modules(status_filter=args.status)
        print(json.dumps([m.to_dict() for m in mods], indent=2))

    elif args.command == "status":
        mod = registry.update_status(module_id=args.id, new_status=args.status)
        if mod:
            print(json.dumps(mod.to_dict(), indent=2))
        else:
            print(json.dumps({"error": f"Module '{args.id}' not found"}))
            sys.exit(1)

    elif args.command == "run":
        mod = registry.get_module(args.id)
        if not mod:
            print(json.dumps({"error": f"Module '{args.id}' not found"}))
            sys.exit(1)

        input_data = json.loads(args.input)
        sandbox = SandboxEnvironment()
        res = sandbox.run_code_in_sandbox(
            code=mod.code_snippet,
            entry_function=f"{mod.slug}_processor",
            sample_input=input_data
        )
        print(json.dumps(res, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
