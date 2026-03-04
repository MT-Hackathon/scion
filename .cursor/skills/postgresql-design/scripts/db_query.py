# /// script
# dependencies = []
# ///
"""
Database query helper for quick investigation.

Usage:
    uv run db_query.py "SELECT * FROM user_roles LIMIT 5;"
    uv run db_query.py "\dt"  # List tables
    uv run db_query.py "\d+ requests"  # Table details

Connection defaults to local dev database (procurement-api compose.yaml).
Override with environment variables:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""
import os
import subprocess
import sys


def get_connection_config():
    """Get database connection config from environment or defaults."""
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "name": os.environ.get("DB_NAME", "procurement_workflow"),
        "user": os.environ.get("DB_USER", "procurement"),
        "password": os.environ.get("DB_PASSWORD", "dev_password"),
    }


def run_query(query: str) -> int:
    """Execute a SQL query against the database using podman + psql."""
    config = get_connection_config()

    cmd = [
        "podman", "run", "--rm", "--network", "host",
        "-e", f"PGPASSWORD={config['password']}",
        "docker.io/postgres:16-alpine",
        "psql",
        "-h", config["host"],
        "-p", config["port"],
        "-U", config["user"],
        "-d", config["name"],
        "-c", query,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            # psql outputs notices to stderr, only error if exit code != 0
            if result.returncode != 0:
                print(f"Error: {result.stderr}", file=sys.stderr)
            else:
                # Some psql meta-commands output to stderr
                print(result.stderr, file=sys.stderr)
        return result.returncode
    except FileNotFoundError:
        print("Error: 'podman' command not found. Ensure Podman is installed.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print('  uv run db_query.py "SELECT * FROM user_roles;"')
        print('  uv run db_query.py "\\dt"')
        print('  uv run db_query.py "\\d+ requests"')
        sys.exit(1)

    query = sys.argv[1]
    sys.exit(run_query(query))


if __name__ == "__main__":
    main()
