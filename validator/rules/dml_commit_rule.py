# validator/rules/dml_commit_rule.py
from .rule_base import RuleBase
import re

DML_RE = re.compile(r'^\s*(insert|update|delete)\b', re.IGNORECASE)
NEW_STMT_KEYWORD_RE = re.compile(
    r'^\s*(insert|update|delete|create|alter|drop|truncate|grant|revoke|declare|begin)\b',
    re.IGNORECASE
)

class DMLCommitRule(RuleBase):
    id = "dml_commit"

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "DML must be followed by COMMIT")

        if idx < 0 or idx >= len(statements):
            return msgs

        s = statements[idx] or ""
        if not s.strip():
            return msgs

        if not DML_RE.match(s):
            return msgs

        s_norm = re.sub(r'\s+', ' ', s).lower().strip()

        # If COMMIT exists in same combined token -> success
        if re.search(r'\bcommit\b', s_norm):
            msgs.append(f"✅ {name}: COMMIT found in same statement.")
            return msgs

        # Look ahead for next meaningful token
        j = idx + 1
        while j < len(statements):
            nxt = (statements[j] or "").strip()
            j += 1
            if not nxt:
                continue
            nxt_norm = re.sub(r'\s+', ' ', nxt).lower().strip()

            if nxt_norm.startswith("commit") or re.match(r'^commit\b', nxt_norm):
                msgs.append(f"✅ {name}: COMMIT correctly follows DML.")
                return msgs

            if NEW_STMT_KEYWORD_RE.match(nxt_norm):
                msgs.append(f"❌ {name}: DML statement not followed by COMMIT.")
                return msgs

            # otherwise continue scanning
            continue

        msgs.append(f"❌ {name}: DML statement not followed by COMMIT.")
        return msgs
