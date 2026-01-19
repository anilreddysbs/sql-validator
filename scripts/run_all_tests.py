import os
import sys
import glob

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from validator.validator import validate_sql_text

def run_all_tests():
    # Go one level up if running from scripts/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_dir = os.path.join(base_dir, "test")
    report_path = os.path.join(base_dir, "full_test_report.txt")
    config_path = os.path.join(base_dir, "config", "checks.json")
    
    test_files = glob.glob(os.path.join(test_dir, "test_*.txt"))
    
    print(f"Found {len(test_files)} test files in {test_dir}.")
    
    with open(report_path, "w", encoding="utf-8") as report:
        for file_path in sorted(test_files):
            print(f"Running {os.path.basename(file_path)}...")
            report.write(f"\n{'='*60}\nFILE: {os.path.relpath(file_path, base_dir)}\n{'='*60}\n")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                results, summary = validate_sql_text(content, checks_path=config_path)
                
                report.write(f"Summary: {summary}\n\n")
                
                for res in results:
                    clean_query = res['query'][:80].replace('\n', ' ')
                    report.write(f"Query: {clean_query}...\n")
                    for val in res['validations']:
                        report.write(f"  {val}\n")
                    report.write("-" * 40 + "\n")
            
            except Exception as e:
                report.write(f"❌ Exception running file: {e}\n")
                print(f"Error in {file_path}: {e}")

    print(f"All tests completed. See {report_path}")

if __name__ == "__main__":
    run_all_tests()
