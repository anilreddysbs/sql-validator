# validator/validator.py
from .parser import split_sql_queries
from .engine import RuleEngine
from .ai_engine import AIEngine

def validate_sql_text(text, checks_path="config/checks.json", skip_ai=False):
    """
    Parse SQL text into logical statements and run all active rules
    against each statement. Return (results, summary).
    """
    statements = split_sql_queries(text)

    engine = RuleEngine(checks_config_path=checks_path)
    rules = engine.get_active_rules()
    
    # Initialize AI Engine (Simulation Mode)
    ai_runner = AIEngine()

    results = []
    total = 0
    passed = 0
    failed = 0

    for idx, stmt in enumerate(statements):
        # defensive: ignore pure slash token if parser somehow left it standalone
        if stmt is None:
            continue
        total += 1
        rule_messages = []
        failure_found = False
        context = {}

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

    # Run AI Analysis (Only if not skipped)
    if not skip_ai:
        # distinct static violations to exclude from AI
        existing_violations = set()
        for res in results:
            for v in res['validations']:
                if v.startswith("❌") or v.startswith("⚠️"):
                    # Clean up icon and just get text
                    clean_msg = v.replace("❌", "").replace("⚠️", "").strip()
                    existing_violations.add(clean_msg)

        ai_result = ai_runner.generate_unified_analysis(text, list(existing_violations))
        
        # Map insights to specific queries
        global_insights = []
        
        for insight in ai_result['insights']:
            snippet = insight.get('related_code_snippet', '').strip()
            matched = False
            
            if snippet:
                for res in results:
                    # Simple containment check (case-insensitive for robustness)
                    if snippet.lower() in res['query'].lower():
                        # Format: 🧠 [Type] Message
                        formatted_msg = f"🧠 [{insight.get('type')}] {insight.get('message')}"
                        res['validations'].append(formatted_msg)
                        matched = True
                        break
            
            if not matched:
                global_insights.append(insight)

        summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "ai_summary": ai_result['summary'],
            "ai_insights": global_insights # Only show unmapped ones globally
        }
    else:
        # AI Skipped
        summary = {
            "total": total,
            "passed": passed,
            "failed": failed
        }

    return results, summary

