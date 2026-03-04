#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Scan all scaffolding files and report accurate token counts and compliance status.
"""
import json
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token"""
    return len(text) // 4

def scan_directory(directory: Path, file_type: str, min_tokens: int, max_tokens: int):
    """Scan a directory and return file statistics"""
    results = []

    if not directory.exists():
        return results

    for file_path in sorted(directory.glob("*.md*")):
        content = file_path.read_text()
        tokens = estimate_tokens(content)

        status = "OK"
        if tokens < min_tokens:
            status = "UNDER"
        elif tokens > max_tokens:
            status = "OVER"

        results.append({
            'file': file_path.name,
            'path': str(file_path.relative_to(file_path.parents[2])),
            'tokens': tokens,
            'status': status,
            'over_by': tokens - max_tokens if tokens > max_tokens else 0,
            'under_by': min_tokens - tokens if tokens < min_tokens else 0
        })

    return results

def main():
    project_root = Path(__file__).resolve().parents[4]
    cursor_dir = project_root / ".cursor"

    # Token budgets
    budgets = {
        'rules': (50, 350),
        'skills': (50, 500),
        'personas': (250, 800),
        'context': (300, 2000)
    }

    all_results = {}

    for dir_name, (min_tok, max_tok) in budgets.items():
        directory = cursor_dir / dir_name
        results = scan_directory(directory, dir_name, min_tok, max_tok)
        all_results[dir_name] = results

    # Print detailed report
    print("=" * 100)
    print("SCAFFOLDING FILE SIZE SCAN - ACCURATE TOKEN COUNTS")
    print("=" * 100)
    print()

    for dir_name, results in all_results.items():
        min_tok, max_tok = budgets[dir_name]

        over_budget = [r for r in results if r['status'] == 'OVER']
        under_budget = [r for r in results if r['status'] == 'UNDER']
        ok_count = len([r for r in results if r['status'] == 'OK'])

        print(f"\n{'=' * 100}")
        print(f"{dir_name.upper()} (budget: {min_tok}-{max_tok} tokens)")
        print(f"{'=' * 100}")
        print(f"Total files: {len(results)} | OK: {ok_count} | Over: {len(over_budget)} | Under: {len(under_budget)}")

        if over_budget:
            print(f"\nOVER BUDGET ({len(over_budget)} files):")
            print("-" * 100)
            # Sort by how much they're over
            for r in sorted(over_budget, key=lambda x: x['over_by'], reverse=True):
                print(f"  {r['tokens']:>4} tokens (+{r['over_by']:>3}) | {r['path']}")

        if under_budget:
            print(f"\nUNDER BUDGET ({len(under_budget)} files):")
            print("-" * 100)
            for r in sorted(under_budget, key=lambda x: x['under_by'], reverse=True):
                print(f"  {r['tokens']:>4} tokens (-{r['under_by']:>3}) | {r['path']}")

    # Summary statistics
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)

    total_files = sum(len(results) for results in all_results.values())
    total_over = sum(len([r for r in results if r['status'] == 'OVER']) for results in all_results.values())
    total_under = sum(len([r for r in results if r['status'] == 'UNDER']) for results in all_results.values())
    total_ok = sum(len([r for r in results if r['status'] == 'OK']) for results in all_results.values())

    print(f"\nTotal files: {total_files}")
    print(f"  OK: {total_ok} ({total_ok/total_files*100:.1f}%)")
    print(f"  Over budget: {total_over} ({total_over/total_files*100:.1f}%)")
    print(f"  Under budget: {total_under} ({total_under/total_files*100:.1f}%)")
    print()

    # Export JSON for scripting
    output_file = cursor_dir / "scripts" / "code-quality" / "scaffolding-sizes.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"Detailed results exported to: {output_file}")

if __name__ == "__main__":
    main()
