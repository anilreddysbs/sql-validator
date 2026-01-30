from validator.validator import validate_sql_text
import json
import sys

# Force UTF-8 for Windows consoles
sys.stdout.reconfigure(encoding='utf-8')

test_sql = """
CREATE TABLE T_CUSTOMERS_BKP AS SELECT * FROM T_CUSTOMERS;
UPDATE T_ORDERS SET STATUS = 'SHIPPED' WHERE ORDER_DATE < SYSDATE - 7;
"""

print("Running Validator with AI Integration...")
results, summary = validate_sql_text(test_sql)

print("\n--- AI Summary ---")
print(summary.get('ai_summary', 'MISSING'))

print("\n--- AI Insights ---")
insights = summary.get('ai_insights', [])
if insights:
    for i in insights:
        print(f"[{i['type']}] {i['message']} (Severity: {i['severity']})")
else:
    print("MISSING INSIGHTS")

if summary.get('ai_summary'):
    if "Simulation" in summary['ai_summary']:
        print("\n⚠️ NOTE: Running in SIMULATION mode (No API Key found).")
    else:
        print("\n🚀 SUCCESS: Running in REAL AI mode!")
else:
    print("\n❌ FAILURE: AI info missing.")
