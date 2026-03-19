# validator/rules/backup_drop_separation_rule.py
from .rule_base import RuleBase
import re

class BackupDropSeparationRule(RuleBase):
    id = "backup_drop_separation"

    def apply(self, statements, idx, context):
        """
        Enforce that if a file contains any DROP TABLE ... _TBD statement,
        it must ONLY contain DROP TABLE ... _TBD statements.
        
        This verification logic checks the *entire* file content context, 
        so we need to be careful not to flag every single statement multiple times.
        However, standard practice in this framework seems to be validating statement by statement.
        
        To avoid redundancy, we can check the file-level condition once per file 
        (conceptually), or just let it fail on every non-compliant statement.
        
        Strategy:
        1. Check if the current statement is a "DROP TABLE ... _TBD".
        2. If yes, check if there are OTHER statements in the list that are NOT "DROP TABLE ... _TBD".
           If so, flag this statement for being in a mixed file.
        3. Check if the current statement is NOT "DROP TABLE ... _TBD".
           If there is ANY "DROP TABLE ... _TBD" elsewhere in the statements,
           flag this statement for mixing with backup drops.
        """
        msgs = []
        name = self.params.get("rule_name", "Backup Drop Separation")
        
        # Helper to identify if a statement is a backup drop
        def is_backup_drop(stmt):
            if not stmt: return False
            s_clean = stmt.strip().rstrip(';').strip().upper()
            # Must start with DROP TABLE and end with _TBD
            if s_clean.startswith("DROP TABLE") and s_clean.endswith("_TBD"):
                return True
            return False
            
        current_is_backup = is_backup_drop(statements[idx])
        
        has_any_backup_drop = any(is_backup_drop(s) for s in statements if s)
        
        if not has_any_backup_drop:
            # No backup drops in file, so no separation issue regarding this rule
            return msgs

        # If we have backup drops, ALL statements must be backup drops
        # (or maybe we allow COMMIT? The user said "separate script", implying pure containment)
        # Let's assume STRICT isolation based on "dont include it in same script".
        
        if not current_is_backup:
            # This statement is NOT a backup drop, but the file HAS backup drops.
            # This is a violation.
            msgs.append(f"FAIL {name}: Found mixed content. File contains DROP TABLE ... _TBD statements, "
                f"so it must NOT contain other statements like this one.")
        else:
            # This statement IS a backup drop.
            # We need to check if there are non-backup drops to flag the file context.
            # If the file is mixed, we can flag this too, or just flag the "polluting" statements.
            # Let's flag everything to be safe and visible.
            has_non_backup = any(not is_backup_drop(s) for s in statements if s)
            
            if has_non_backup:
                msgs.append(f"FAIL {name}: File contains non-backup-drop statements. "
                    f"Backup DROP scripts must be isolated.")
            else:
                msgs.append(f"PASS {name}: Backup drop statement is correctly isolated.")
                
        return msgs
