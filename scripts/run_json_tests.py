
import os
import sys
import glob
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from validator.validator import validate_sql_text

def run_tests():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(test_dir)
    
    test_files = glob.glob(os.path.join(test_dir, "*.txt"))
    
    all_results = {}

    checks_path = os.path.join(project_root, "config", "checks.json")

    for file_path in test_files:
        filename = os.path.basename(file_path)
        all_results[filename] = {'status': 'error', 'violations': []}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            results, summary = validate_sql_text(content, checks_path=checks_path)
            
            if not results:
                all_results[filename]['status'] = 'pass'
            else:
                all_results[filename]['status'] = 'fail'
                all_results[filename]['violations'] = results # results is a list of dicts
        
        except Exception as e:
            all_results[filename]['status'] = 'error'
            all_results[filename]['error'] = str(e)
            
    with open('test_results.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)

if __name__ == "__main__":
    run_tests()
