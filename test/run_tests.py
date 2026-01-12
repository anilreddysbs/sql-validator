
import os
import sys
import glob

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from validator.validator import validate_sql_text

def run_tests():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(test_dir)
    
    # Get all .txt files in test directory
    test_files = glob.glob(os.path.join(test_dir, "*.txt"))
    
    print(f"Found {len(test_files)} test files.")
    print("-" * 50)

    for file_path in test_files:
        filename = os.path.basename(file_path)
        print(f"Testing file: {filename}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue

        try:
            # Assume running from project root or checks_path needs to be absolute
            checks_path = os.path.join(project_root, "config", "checks.json")
            results, summary = validate_sql_text(content, checks_path=checks_path)
            
            if not results:
                print("  [PASS] No violations found.")
            else:
                print(f"  [FAIL] Found {len(results)} violations:")
                for res in results:
                    rule_id = res.get('rule_id', 'Unknown Rule')
                    message = res.get('message', 'No message')
                    line = res.get('line', 'N/A')
                    print(f"    - [Line {line}] {rule_id}: {message}")
        
        except Exception as e:
            print(f"  [ERROR] Error validating {filename}: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    run_tests()
