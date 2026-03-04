#!/usr/bin/env python3
"""
Description: Summarize pytest results, failures by category, and performance analysis
Usage: 841-analyze-test-results.py [test-file-or-directory]
"""

import contextlib
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def run_pytest(path, timeout_seconds=300):
    """
    Run pytest and return JSON results.

    Args:
        path: Path to test file or directory
        timeout_seconds: Maximum time to wait for tests (default: 300s for large suites)

    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    try:
        result = subprocess.run(
            ['pytest', str(path), '--tb=no', '--json-report', '--json-report-file=/tmp/report.json', '-v'],
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"pytest timed out after {timeout_seconds} seconds"
    except FileNotFoundError:
        return 127, "", "pytest not found. Install with: pip install pytest pytest-json-report"
    except Exception:
        # Fallback: parse pytest output without JSON report
        try:
            result = subprocess.run(
                ['pytest', str(path), '--tb=short', '-v'],
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"pytest timed out after {timeout_seconds} seconds"
        except Exception as fallback_error:
            return 2, "", f"Error running pytest: {fallback_error}"


def analyze_pytest_output(stdout: str, stderr: str) -> tuple:
    """
    Parse pytest output and extract test results.

    Args:
        stdout: Standard output from pytest
        stderr: Standard error from pytest

    Returns:
        Tuple of (passed_count, failed_count, skipped_count, error_count)
    """
    passed = 0
    failed = 0
    skipped = 0
    errors = 0

    lines = stdout.split('\n') + stderr.split('\n')
    for line in lines:
        if ' passed' in line:
            with contextlib.suppress(ValueError, IndexError):
                passed = int(line.split()[0])
        if ' failed' in line:
            with contextlib.suppress(ValueError, IndexError):
                failed = int(line.split()[0])
        if ' skipped' in line:
            with contextlib.suppress(ValueError, IndexError):
                skipped = int(line.split()[0])
        if ' error' in line:
            with contextlib.suppress(ValueError, IndexError):
                errors = int(line.split()[0])

    return passed, failed, skipped, errors


def analyze_test_results(path, timeout_seconds=300):
    """
    Analyze test results for a given path.

    Args:
        path: Path to test file or directory
        timeout_seconds: Maximum time to wait for tests (default: 300s)
    """
    path = Path(path) if isinstance(path, str) else path

    if not path.exists():
        print(f"Error: {path} does not exist", file=sys.stderr)
        sys.exit(2)

    # Run pytest
    returncode, stdout, stderr = run_pytest(path, timeout_seconds)

    # Handle timeout or pytest not found
    if returncode == 124:
        print(f"Error: {stderr}", file=sys.stderr)
        sys.exit(1)
    elif returncode == 127:
        print(f"Error: {stderr}", file=sys.stderr)
        sys.exit(2)

    # Parse results
    passed, failed, skipped, errors = analyze_pytest_output(stdout, stderr)

    total = passed + failed + skipped + errors
    if total == 0:
        print("No test results found")
        sys.exit(1)

    # Calculate percentages
    passed_pct = (passed / total * 100) if total > 0 else 0
    failed_pct = (failed / total * 100) if total > 0 else 0

    # Print results
    print("Test Results")
    print(f"Total: {total} tests")
    print(f"Passed: {passed} ({passed_pct:.0f}%)")
    print(f"Failed: {failed} ({failed_pct:.0f}%)")
    if skipped > 0:
        print(f"Skipped: {skipped}")
    if errors > 0:
        print(f"Errors: {errors}")

    if failed == 0:
        print("All tests passed")
    else:
        # Extract failure details from output
        failure_lines = [line for line in stdout.split('\n') if 'FAILED' in line]
        categories = defaultdict(int)

        for line in failure_lines[:10]:
            if 'test_' in line:
                parts = line.split('::')
                if len(parts) >= 2:
                    category = parts[1].split('[')[0]
                    categories[category] += 1

        if categories:
            print("Failure categories:")
            for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                print(f"  {category}: {count}")
        else:
            print(f"  {failed} test(s) failed")

    if failed > 0:
        print(f"Status: {failed} failures detected")
        sys.exit(1)
    else:
        print("Status: All passed")
        sys.exit(0)


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'tests/'
    analyze_test_results(path)

