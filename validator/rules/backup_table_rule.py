# validator/rules/backup_table_rule.py
"""
Validates backup table suffix requirements.

This rule ONLY checks backup tables for:
1. Required _TBD suffix
2. Lifecycle warning

Naming convention validation (no special chars, start with letter, etc.)
is handled by the separate table_naming_convention_rule.py
"""
from .rule_base import RuleBase
import re


class BackupTableRule(RuleBase):
    id = "backup_table_suffix"

    def _extract_table_name(self, statement):
        """Extract table name from statement, handling schema.table patterns."""
        s = statement.strip()
        
        # Skip parenthesized (handled by naming convention rule)
        if re.search(r'\b(?:into|table)\s*\(', s, re.IGNORECASE):
            return None
        
        # Try schema.table pattern
        schema_match = re.search(
            r"\b(?:into|table)\s+['\"]?([A-Za-z0-9_]+)['\"]?\.['\"]*([A-Za-z0-9_]+)['\"]*",
            s, re.IGNORECASE
        )
        if schema_match:
            return schema_match.group(2)
        
        # Simple table name
        simple_match = re.search(
            r"\b(?:into|table)\s+['\"]?([A-Za-z0-9_]+)['\"]?",
            s, re.IGNORECASE
        )
        if simple_match:
            return simple_match.group(1)
        
        return None

    def _is_backup_table(self, table_name, suffixes):
        """Check if table name indicates a backup table."""
        table_upper = table_name.upper()
        
        for suf in suffixes:
            suf_upper = suf.upper()
            # Check for _BACKUP or _BKP patterns
            if f"_{suf_upper}" in table_upper or table_upper.endswith(suf_upper):
                return True
        
        # Also consider tables ending with _TBD as backup/temp tables
        if table_upper.endswith("_TBD"):
            return True
        
        return False

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "Backup Table Suffix")

        suffixes = self.params.get("backup_suffixes", ["BACKUP", "BKP"])
        required = self.params.get("required_ending", "TBD")

        s = statements[idx].strip()

        # Extract table name
        table_name = self._extract_table_name(s)
        if not table_name:
            return msgs
        
        table_upper = table_name.upper()

        # Check if this is a backup table
        if not self._is_backup_table(table_name, suffixes):
            return msgs  # Not a backup table, skip silently

        # Validate required ending (_TBD)
        if table_upper.endswith(required.upper()):
            msgs.append(self.ok(f"{name}: '{table_upper}' ends with {required}."))
        else:
            msgs.append(self.fail(f"{name}: Backup table '{table_upper}' must end with {required}."))
            return msgs

        # Lifecycle warning
        msgs.append(
            self.warn(
                f"Backup table '{table_upper}' should be dropped in the next CR "
                f"or after its intended usage is completed."
            )
        )

        return msgs
