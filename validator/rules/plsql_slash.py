# validator/rules/plsql_slash.py
from .rule_base import RuleBase
import re

PLSQL_START_RE = re.compile(r'^\s*(declare|begin)\b', re.IGNORECASE)
PLSQL_END_WITH_SLASH_RE = re.compile(r'(?s)\bend\b\s*;.*?(/\s*$|\n/\s*$)', re.IGNORECASE)
PLSQL_END_RE = re.compile(r'\bend\b\s*;', re.IGNORECASE)
SLASH_ONLY_RE = re.compile(r'^\s*/\s*$', re.IGNORECASE)

class PLSQLSlashRule(RuleBase):
    id = "plsql_slash"

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "PL/SQL blocks must end with '/'")

        if idx < 0 or idx >= len(statements):
            return msgs

        s = statements[idx] or ""
        if not s.strip():
            return msgs

        if not PLSQL_START_RE.match(s):
            return msgs

        # If parser included slash in same token, accept
        if PLSQL_END_WITH_SLASH_RE.search(s):
            msgs.append(f"✅ {name}: trailing slash '/' found for PL/SQL block.")
            return msgs

        # otherwise check next non-empty token
        next_idx = idx + 1
        while next_idx < len(statements) and (statements[next_idx] or "").strip() == "":
            next_idx += 1

        if next_idx < len(statements):
            nxt = (statements[next_idx] or "").strip()
            if SLASH_ONLY_RE.match(nxt):
                msgs.append(f"✅ {name}: trailing slash '/' found as next token.")
                return msgs

        # If block contains END; but no slash => fail
        if PLSQL_END_RE.search(s):
            msgs.append(f"❌ {name}: PL/SQL block ended with 'END;' but missing trailing '/'.")
        else:
            msgs.append(f"❌ {name}: PL/SQL block appears incomplete or missing 'END;' and trailing '/'.")
        return msgs
