# validator/rules/grant_revoke_no_commit.py
from .rule_base import RuleBase
import re

class GrantRevokeNoCommitRule(RuleBase):
    id = "grant_revoke_no_commit"

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "GRANT/REVOKE must NOT be followed by COMMIT")

        s = statements[idx].strip()
        if not s:
            return msgs
        s_norm = re.sub(r"\s+", " ", s).lower().strip()

        if not (s_norm.startswith("grant ") or s_norm.startswith("revoke ")):
            return msgs

        if "commit" in s_norm:
            msgs.append(f"❌ {name}: COMMIT found inside statement.")
        else:
            msgs.append(f"✅ {name}: No COMMIT found after GRANT/REVOKE.")

        return msgs
