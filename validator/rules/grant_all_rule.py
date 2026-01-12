# validator/rules/grant_all_rule.py
"""
Validates that GRANT ALL is not used.

GRANT ALL gives excessive privileges and should not be granted to any user.

Examples:
  ❌ GRANT ALL ON hr.employees TO app_user;
  ❌ GRANT ALL PRIVILEGES ON hr.employees TO app_user;
  ✅ GRANT SELECT, INSERT ON hr.employees TO app_user;  -- specific privileges OK
"""
from .rule_base import RuleBase
import re


class GrantAllRule(RuleBase):
    id = "grant_all_restriction"

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "GRANT ALL Restriction")

        s = statements[idx].strip()
        s_upper = s.upper()

        # Check if this is a GRANT statement
        if not s_upper.startswith('GRANT'):
            return msgs

        # Check for GRANT ALL or GRANT ALL PRIVILEGES
        if re.search(r'\bGRANT\s+ALL\b', s_upper):
            # Extract the object and user for error message
            obj_match = re.search(r'\bON\s+([A-Za-z0-9_.]+)', s, re.IGNORECASE)
            user_match = re.search(r'\bTO\s+([A-Za-z0-9_,\s]+?)(?:;|$)', s, re.IGNORECASE)
            
            obj_name = obj_match.group(1) if obj_match else "object"
            user_name = user_match.group(1).strip().rstrip(';') if user_match else "user"
            
            msgs.append(self.fail(
                f"{name}: GRANT ALL on '{obj_name}' to '{user_name}' is not allowed. "
                f"Use specific privileges (SELECT, INSERT, UPDATE, DELETE) instead."
            ))
        
        return msgs
