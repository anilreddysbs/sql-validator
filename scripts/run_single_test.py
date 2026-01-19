import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from validator.validator import validate_sql_text

def run_single():
    file_path = os.path.join(os.path.dirname(__file__), 'test_user_query.txt')
    # Assuming config is in ../config relative to this script
    checks_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'checks.json')

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Validating {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        results, summary = validate_sql_text(content, checks_path=checks_path)
        
        if not results:
            print("SUCCESS: No violations found.")
        else:
            print(f"FOUND {len(results)} VIOLATIONS:")
            for res in results:
                line = res.get('line', '?')
                rule = res.get('rule_id', 'UNKNOWN')
                msg = res.get('message', '')
                print(f"Line {line} | {rule} | {msg}")
                
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_single()
