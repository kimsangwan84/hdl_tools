from .cli import main

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # Fallback for unexpected errors that are not SpecError
        import sys
        print(f"[U901] {e}", file=sys.stderr)
        sys.exit(3)

