import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from validator.validator import validate_sql_text

file_path = os.path.join(os.path.dirname(__file__), 'test_user_query.txt')
checks_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'checks.json')

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

results, summary = validate_sql_text(content, checks_path=checks_path)
print(json.dumps(results, indent=2, default=str))
