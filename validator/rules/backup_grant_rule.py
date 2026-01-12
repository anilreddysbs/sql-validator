# validator/rules/backup_grant_rule.py
"""
Validates that GRANT SELECT on backup tables is only given to LOADER user.

Backup tables are identified by suffixes: _BKP, _BACKUP, or _TBD

Examples:
  ✅ GRANT SELECT ON hr.employees_bkp_tbd TO LOADER;
  ❌ GRANT SELECT ON hr.employees_bkp_tbd TO APP_USER;
  ❌ GRANT SELECT ON hr.employees_bkp_tbd TO LOADER, APP_USER;
"""
from .rule_base import RuleBase
import re


class BackupGrantRule(RuleBase):
    id = "backup_grant_select"

    def _is_backup_table(self, table_name, suffixes):
        """Check if table name indicates a backup table."""
        table_upper = table_name.upper()
        for suf in suffixes:
            suf_upper = suf.upper()
            if f"_{suf_upper}" in table_upper or table_upper.endswith(suf_upper):
                return True
        if table_upper.endswith("_TBD"):
            return True
        return False

    def _extract_grant_info(self, statement):
        """
        Extract grant information from statement.
        Returns (privilege, table_name, grantees) or (None, None, None)
        """
        s = statement.strip()
        s_upper = s.upper()
        
        # Check if this is a GRANT statement
        if not s_upper.startswith('GRANT'):
            return None, None, None
        
        # Extract privilege (looking for SELECT specifically)
        priv_match = re.search(r'\bGRANT\s+(\w+)', s, re.IGNORECASE)
        if not priv_match:
            return None, None, None
        privilege = priv_match.group(1).upper()
        
        # Extract table name (after ON)
        table_match = re.search(
            r'\bON\s+([A-Za-z0-9_]+\.)?([A-Za-z0-9_]+)',
            s, re.IGNORECASE
        )
        if not table_match:
            return None, None, None
        table_name = table_match.group(2)
        
        # Extract grantees (after TO)
        to_match = re.search(r'\bTO\s+(.+?)(?:;|$)', s, re.IGNORECASE)
        if not to_match:
            return None, None, None
        
        grantees_str = to_match.group(1).strip().rstrip(';')
        # Split by comma and clean up
        grantees = [g.strip().upper() for g in grantees_str.split(',')]
        
        return privilege, table_name, grantees

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "Backup Table Grant Restriction")
        allowed_user = self.params.get("allowed_user", "LOADER").upper()
        suffixes = self.params.get("backup_suffixes", ["BACKUP", "BKP"])

        s = statements[idx].strip()

        # Extract grant information
        privilege, table_name, grantees = self._extract_grant_info(s)
        
        if not privilege or not table_name or not grantees:
            return msgs  # Not a valid GRANT statement
        
        # Only check SELECT privilege
        if privilege != "SELECT":
            return msgs
        
        # Check if this is a backup table
        if not self._is_backup_table(table_name, suffixes):
            return msgs  # Not a backup table, skip
        
        # Check grantees
        invalid_grantees = [g for g in grantees if g != allowed_user]
        
        if invalid_grantees:
            invalid_list = ', '.join(invalid_grantees)
            msgs.append(self.fail(
                f"{name}: GRANT SELECT on backup table '{table_name.upper()}' "
                f"can only be given to {allowed_user}. Found: {invalid_list}."
            ))
        else:
            msgs.append(self.ok(
                f"{name}: GRANT SELECT on backup table '{table_name.upper()}' "
                f"correctly granted to {allowed_user}."
            ))
        
        return msgs
