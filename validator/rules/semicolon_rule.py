# validator/rules/semicolon_rule.py
from .rule_base import RuleBase
import re

class SemicolonRule(RuleBase):
    id = "semicolon_required"

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "Semicolon required")

        s = statements[idx].strip()

        # skip slash
        if s == "/":
            msgs.append(f"✅ {name}: Slash is allowed here.")
            return msgs

        if re.match(r"^(declare|begin)", s, re.IGNORECASE):
            msgs.append(f"✅ {name}: PL/SQL semicolons handled by PL/SQL rule.")
            return msgs

        if s.endswith(";"):
            msgs.append(f"✅ {name}: Statement ends with semicolon.")
        else:
            msgs.append(f"❌ {name}: Statement missing semicolon.")

        return msgs
