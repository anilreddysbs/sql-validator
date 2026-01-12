# validator/rules/backup_drop_limit_rule.py
"""
Validates that maximum 400 backup tables (_TBD format) can be dropped in a single file.

This is a file-level check that counts all DROP TABLE statements for _TBD tables.

Examples:
  ✅ File with 400 or fewer DROP TABLE ... _TBD statements
  ❌ File with more than 400 DROP TABLE ... _TBD statements
"""
from .rule_base import RuleBase
import re


class BackupDropLimitRule(RuleBase):
    id = "backup_drop_limit"

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "Backup Table Drop Limit")
        max_drops = self.params.get("max_drops", 400)

        # Only run this check once per validation (on the first statement)
        if idx != 0:
            return msgs

        # Count DROP TABLE statements for _TBD tables
        drop_count = 0
        dropped_tables = []

        for stmt in statements:
            if not stmt:
                continue
            
            s_upper = stmt.upper()
            
            # Check if this is a DROP TABLE statement
            if not re.search(r'\bDROP\s+TABLE\b', s_upper):
                continue
            
            # Extract table name
            match = re.search(
                r'\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?([A-Za-z0-9_.]+)',
                stmt,
                re.IGNORECASE
            )
            if not match:
                continue
            
            table_name = match.group(1).upper()
            
            # Check if it's a _TBD backup table
            if table_name.endswith('_TBD'):
                drop_count += 1
                if len(dropped_tables) < 5:  # Keep first 5 for error message
                    dropped_tables.append(table_name)

        # Check against limit
        if drop_count > max_drops:
            tables_preview = ', '.join(dropped_tables)
            if drop_count > 5:
                tables_preview += '...'
            
            msgs.append(self.fail(
                f"{name}: Found {drop_count} DROP TABLE statements for _TBD backup tables. "
                f"Maximum allowed is {max_drops}. Tables: {tables_preview}"
            ))
        elif drop_count > 0:
            msgs.append(self.ok(
                f"{name}: {drop_count} DROP TABLE statements for _TBD backup tables (limit: {max_drops})."
            ))
        
        return msgs
