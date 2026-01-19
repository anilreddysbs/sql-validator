# validator/rules/tablespace_restriction_rule.py
from .rule_base import RuleBase
import re

class TablespaceRestrictionRule(RuleBase):
    id = "tablespace_restriction"

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "Tablespace Restriction")
        forbidden = self.params.get("forbidden_tablespaces", ["USERS", "SYSTEM", "SYSAUX", "TEMP", "DEFAULT"])
        
        s = statements[idx].strip()
        
        # Simple regex to find TABLESPACE clause followed by a name
        # Handles quoting optionally
        match = re.search(r'\bTABLESPACE\s+["\']?([A-Za-z0-9_]+)["\']?', s, re.IGNORECASE)
        
        if match:
            ts_name = match.group(1).upper()
            if ts_name in [f.upper() for f in forbidden]:
                msgs.append(self.fail(f"{name}: Object cannot be created in forbidden tablespace '{ts_name}'."))
            else:
                # Optionally pass? or just silent?
                # Usually purely negative checks warn on fail, silent on pass. 
                # But to show it was checked:
                pass
                # msgs.append(self.ok(f"{name}: Tablespace '{ts_name}' is allowed.")) 
                # ^ explicit ok might clutter report if every table has it. 
                # But consistency suggests showing 'ok' if we found a tablespace and checked it.
                msgs.append(self.ok(f"{name}: Tablespace '{ts_name}' is allowed."))
        
        return msgs
