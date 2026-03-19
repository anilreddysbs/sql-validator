import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from validator.validator import validate_sql_text

def run_test(file_path, out_file):
    out_file.write(f"\n{'='*60}\n")
    out_file.write(f"RUNNING TEST ON: {file_path}\n")
    out_file.write(f"{'='*60}\n")
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        sql_text = f.read()

    results, summary = validate_sql_text(sql_text, backup_toggle=True)

    out_file.write(f"Overview: {summary['passed']}/{summary['total']} Statements Passed\n\n")

    for i, res in enumerate(results):
        out_file.write(f"--- QUERY {i+1} ---\n")
        query_preview = res['query'].strip().split('\n')[0]
        if len(query_preview) > 80: query_preview = query_preview[:77] + "..."
        out_file.write(f"SQL: {query_preview}\n")
        
        out_file.write("Validations:\n")
        for v in res['validations']:
            out_file.write(f"  {v}\n")
        out_file.write("-" * 40 + "\n")

if __name__ == "__main__":
    with open("test/full_rule_test_output.txt", "w", encoding="utf-8") as outf:
        run_test("test/comprehensive_test_cases.txt", outf)
        run_test("test/pure_backup_drop.txt", outf)
        run_test("test/alias_verification.txt", outf)
