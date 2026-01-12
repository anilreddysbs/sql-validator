# validator/rules/nologging_rule.py
"""
Validates that objects are not created in NOLOGGING mode.

NOLOGGING reduces redo log generation which can cause data loss
during recovery. All objects should use default LOGGING mode.

Examples:
  ❌ CREATE TABLE hr.employees (id NUMBER) NOLOGGING;
  ❌ CREATE INDEX hr.idx ON hr.employees(id) NOLOGGING;
  ❌ ALTER TABLE hr.employees NOLOGGING;
  ✅ CREATE TABLE hr.employees (id NUMBER);
  ✅ CREATE TABLE hr.employees (id NUMBER) LOGGING;
"""
from .rule_base import RuleBase
import re


class NologgingRule(RuleBase):
    id = "nologging_restriction"

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "NOLOGGING Restriction")

        s = statements[idx].strip()
        s_upper = s.upper()

        # Check for NOLOGGING keyword
        if not re.search(r'\bNOLOGGING\b', s_upper):
            return msgs

        # Determine the type of statement
        stmt_type = "Statement"
        if re.search(r'\bCREATE\s+TABLE\b', s_upper):
            stmt_type = "CREATE TABLE"
        elif re.search(r'\bCREATE\s+INDEX\b', s_upper):
            stmt_type = "CREATE INDEX"
        elif re.search(r'\bALTER\s+TABLE\b', s_upper):
            stmt_type = "ALTER TABLE"
        elif re.search(r'\bALTER\s+INDEX\b', s_upper):
            stmt_type = "ALTER INDEX"

        # Extract object name for error message
        obj_match = re.search(
            r'\b(?:TABLE|INDEX)\s+([A-Za-z0-9_.]+)',
            s, re.IGNORECASE
        )
        obj_name = obj_match.group(1) if obj_match else "object"

        msgs.append(self.fail(
            f"{name}: {stmt_type} '{obj_name}' uses NOLOGGING mode. "
            f"NOLOGGING is not allowed - use LOGGING mode for recoverability."
        ))
        
        return msgs
