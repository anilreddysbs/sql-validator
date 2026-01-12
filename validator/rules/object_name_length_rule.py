# validator/rules/object_name_length_rule.py
from .rule_base import RuleBase
import re

class ObjectNameLengthRule(RuleBase):
    id = "object_name_length"

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "Object name <= max length")

        max_len = self.params.get("max_length", 30)
        s = statements[idx].strip()

        # Updated regex to handle optional schema prefix (e.g. schema.table)
        # Matches: CREATE TABLE [schema.]table
        m = re.search(
            r'\b(create|alter)\s+(table|index|view)\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:IF\s+EXISTS\s+)?(?:["\']?[A-Za-z0-9_]+["\']?\.)?["\']?([A-Za-z0-9_]+)["\']?',
            s, re.IGNORECASE
        )

        if not m:
            return msgs

        # group(2) from (table|index|view) is group 2? No.
        # Group 1: create/alter
        # Group 2: table/index/view
        # Non-capturing groups for IF EXISTS and schema prefix
        # Group 3: object name
        
        obj = m.group(3)

        if len(obj) > max_len:
            msgs.append(f"❌ {name}: '{obj}' exceeds {max_len} chars.")
        else:
            msgs.append(f"✅ {name}: '{obj}' length OK ({len(obj)}).")

        return msgs
