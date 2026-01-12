# validator/rules/grant_privilege_rule.py
"""
Validates that only SELECT privilege is granted to regular users.
LOADER user can have additional privileges.

Examples:
  ✅ GRANT SELECT ON hr.employees TO app_user;     -- SELECT OK for anyone
  ✅ GRANT INSERT ON hr.employees TO LOADER;       -- LOADER can have extra privileges
  ❌ GRANT INSERT ON hr.employees TO app_user;     -- Only SELECT for non-LOADER
  ❌ GRANT UPDATE ON hr.employees TO app_user;     -- Only SELECT for non-LOADER
"""
from .rule_base import RuleBase
import re


class GrantPrivilegeRule(RuleBase):
    id = "grant_privilege_restriction"

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "Grant Privilege Restriction")
        privileged_user = self.params.get("privileged_user", "LOADER").upper()
        allowed_for_all = self.params.get("allowed_privileges", ["SELECT"])
        allowed_for_all = [p.upper() for p in allowed_for_all]

        s = statements[idx].strip()
        s_upper = s.upper()

        # Check if this is a GRANT statement (but not GRANT ALL - handled separately)
        if not s_upper.startswith('GRANT'):
            return msgs
        
        # Skip if GRANT ALL (handled by grant_all_rule)
        if re.search(r'\bGRANT\s+ALL\b', s_upper):
            return msgs

        # Extract privileges (can be comma-separated like SELECT, INSERT)
        priv_match = re.search(r'\bGRANT\s+([\w,\s]+)\s+ON\b', s, re.IGNORECASE)
        if not priv_match:
            return msgs
        
        priv_str = priv_match.group(1)
        privileges = [p.strip().upper() for p in priv_str.split(',')]

        # Extract grantees (after TO)
        user_match = re.search(r'\bTO\s+([A-Za-z0-9_,\s]+?)(?:;|$)', s, re.IGNORECASE)
        if not user_match:
            return msgs
        
        grantees_str = user_match.group(1).strip().rstrip(';')
        grantees = [g.strip().upper() for g in grantees_str.split(',')]

        # Extract object for error message
        obj_match = re.search(r'\bON\s+([A-Za-z0-9_.]+)', s, re.IGNORECASE)
        obj_name = obj_match.group(1) if obj_match else "object"

        # Check each grantee
        for grantee in grantees:
            if grantee == privileged_user:
                # LOADER can have any privilege
                continue
            
            # For non-privileged users, check privileges
            restricted_privs = [p for p in privileges if p not in allowed_for_all]
            
            if restricted_privs:
                restricted_list = ', '.join(restricted_privs)
                msgs.append(self.fail(
                    f"{name}: User '{grantee}' can only be granted SELECT. "
                    f"Found: {restricted_list}. Only {privileged_user} can have additional privileges."
                ))
                return msgs

        # All good
        if privileges:
            priv_list = ', '.join(privileges)
            user_list = ', '.join(grantees)
            msgs.append(self.ok(
                f"{name}: GRANT {priv_list} on '{obj_name}' to '{user_list}' is valid."
            ))
        
        return msgs
