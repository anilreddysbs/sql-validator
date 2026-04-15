# validator/validator.py
from .parser import split_sql_queries
from .engine import RuleEngine

def validate_sql_text(text, checks_path="config/checks.json", backup_toggle=False):
    """
    Parse SQL text into logical statements and run all active rules
    against each statement. Return (results, summary).
    """
    statements = split_sql_queries(text)

    engine = RuleEngine(checks_config_path=checks_path)
    rules = engine.get_active_rules()

    results = []
    total = 0
    passed = 0
    failed = 0
    shared_context = {
        "backup_toggle": backup_toggle,
        "global_validations": []
    }

    for idx, stmt in enumerate(statements):
        # defensive: ignore pure slash token if parser somehow left it standalone
        if stmt is None:
            continue
        total += 1
        rule_messages = []
        failure_found = False
        context = shared_context

        for rule in rules:
            try:
                msgs = rule.apply(statements, idx, context)
            except Exception as e:
                msgs = [f"❌ Error in {getattr(rule, 'id', 'unknown_rule')}: {e}"]

            if any(m.startswith("❌") for m in msgs):
                failure_found = True

            rule_messages.extend(msgs)

        if failure_found:
            failed += 1
        else:
            passed += 1

        results.append({
            "index": idx,
            "query": stmt,
            "validations": rule_messages
        })

    warnings = []
    for item in results:
        for msg in item["validations"]:
            if msg.startswith("âš ï¸") or msg.startswith("⚠️"):
                warnings.append({
                    "query_index": item["index"] + 1,
                    "message": msg
                })

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "global_validations": shared_context["global_validations"]
    }

    return results, summary
