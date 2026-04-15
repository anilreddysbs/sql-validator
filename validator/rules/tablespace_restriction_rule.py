# validator/rules/tablespace_restriction_rule.py
from .rule_base import RuleBase
import re

class TablespaceRestrictionRule(RuleBase):
    id = "tablespace_restriction"

    TARGET_STATEMENT_RE = re.compile(
        r'^\s*(create|alter)\s+(table|index)\b',
        re.IGNORECASE
    )

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "Tablespace Restriction")
        forbidden = self.params.get("forbidden_tablespaces", ["USERS", "SYSTEM", "SYSAUX", "TEMP", "DEFAULT"])
        
        s = statements[idx].strip()

        if not self.TARGET_STATEMENT_RE.match(s):
            return msgs
        
        # Simple regex to find TABLESPACE clause followed by a name
        # Handles quoting optionally
        match = re.search(r'\bTABLESPACE\s+["\']?([A-Za-z0-9_]+)["\']?', s, re.IGNORECASE)
        
        if match:
            ts_name = match.group(1).upper()
            if ts_name in [f.upper() for f in forbidden]:
                msgs.append(self.fail(f"{name}: Object cannot be created in the specified tablespace. This tablespace is restricted."))
            else:
                msgs.append(self.ok(f"{name}: Tablespace usage is valid."))
        
        return msgs
