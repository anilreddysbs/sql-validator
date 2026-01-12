# validator/rules/ddl_no_commit.py
from .rule_base import RuleBase
import re

DDL_STARTS = ("create", "alter", "drop", "truncate")

class DDLNoCommitRule(RuleBase):
    id = "ddl_no_commit"

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "DDL must NOT be followed by COMMIT")

        s = statements[idx].strip()
        if not s:
            return msgs
        s_norm = re.sub(r"\s+", " ", s).lower().strip()

        if not any(s_norm.startswith(k + " ") for k in DDL_STARTS):
            return msgs

        if "commit" in s_norm:
            msgs.append(f"❌ {name}: COMMIT found inside DDL.")
        else:
            msgs.append(f"✅ {name}: No COMMIT found.")

        return msgs
