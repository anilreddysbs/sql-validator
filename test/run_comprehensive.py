import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from validator.validator import validate_sql_text

def run_test(file_path):
    print(f"\n{'='*60}")
    print(f"RUNNING TEST ON: {file_path}")
    print(f"{'='*60}")
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        sql_text = f.read()

    results, summary = validate_sql_text(sql_text, backup_toggle=True)

    print(f"Overview: {summary['passed']}/{summary['total']} Statements Passed\n")

    for i, res in enumerate(results):
        print(f"--- QUERY {i+1} ---")
        query_preview = res['query'].strip().split('\n')[0]
        if len(query_preview) > 80: query_preview = query_preview[:77] + "..."
        print(f"SQL: {query_preview}")
        
        print("Validations:")
        for v in res['validations']:
            print(f"  {v}")
        print("-" * 40)

if __name__ == "__main__":
    run_test("test/comprehensive_test_cases.txt")
    run_test("test/pure_backup_drop.txt")
