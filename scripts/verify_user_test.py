import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from validator.validator import validate_sql_text

def run_verification():
    file_path = os.path.join(os.path.dirname(__file__), 'test_user_query.txt')
    checks_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'checks.json')

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Verifying {os.path.basename(file_path)}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    results, summary = validate_sql_text(content, checks_path=checks_path)
    
    print(f"Total Statements: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print("-" * 50)

    for res in results:
        failures = [msg for msg in res['validations'] if "❌" in msg]
        if failures:
            # Print first 50 chars of query for context
            query_snippet = res['query'][:50].replace('\n', ' ')
            print(f"Statement {res['index']} [FAIL]: {query_snippet}...")
            for fail in failures:
                print(f"  {fail}")
            print("-" * 50)
        else:
            # print(f"Statement {res['index']} [PASS]")
            pass

if __name__ == "__main__":
    run_verification()
