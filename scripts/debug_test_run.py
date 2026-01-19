
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from validator.validator import validate_sql_text

def run():
    print("Starting debug test...")
    file_path = "test/test_user_query.txt"
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open('debug_report.txt', 'w', encoding='utf-8') as f_out:
        print(f"Read content length: {len(content)}", file=f_out)
        
        try:
            results, summary = validate_sql_text(content, checks_path="config/checks.json")
            print("Validation finished.")
            print(f"Results: {len(results)} statements.", file=f_out)
            for res in results:
                 clean_query = res['query'][:60].replace('\n', ' ').replace('\t', '[TAB]')
                 print(f"Query: {clean_query}...", file=f_out)
                 for val in res['validations']:
                     print(f"  {val}", file=f_out)
        except Exception as e:
            print(f"Exception: {e}", file=f_out)
            import traceback
            traceback.print_exc(file=f_out)

if __name__ == "__main__":
    run()
