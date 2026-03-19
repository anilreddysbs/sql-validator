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
        # Helper to identify if a statement is a backup drop or should be ignored (comments/empty)
        def is_valid_in_backup_script(stmt):
            if not stmt: return True
            s_clean = stmt.strip().upper()
            if not s_clean or s_clean.startswith("--") or s_clean == "/":
                return True
            
            # Robustly strip whitespace, semicolons and slashes from the end
            # Using re.sub to handle any combination at the end
            s_clean = re.sub(r'[;/\s]+$', '', s_clean)
            
            if s_clean.startswith("DROP TABLE") and s_clean.endswith("_TBD"):
                return True
            return False
            
        current_is_valid = is_valid_in_backup_script(statements[idx])
        
        has_any_backup_drop = any(
            re.sub(r'[;/\s]+$', '', s.strip().upper()).startswith("DROP TABLE") and 
            re.sub(r'[;/\s]+$', '', s.strip().upper()).endswith("_TBD")
            for s in statements if s and not s.strip().startswith("--")
        )
        
        if not has_any_backup_drop:
            # No backup drops in file, so no separation issue regarding this rule
            return msgs

        if not current_is_valid:
            # This statement is NOT a backup drop/comment, but the file HAS backup drops.
            if idx == 0:
                msgs.append(f"FAIL {name}: Found mixed content. File contains DROP TABLE ... _TBD statements, "
                    f"so it must NOT contain other statements. Backup drop scripts must be isolated.")
        else:
            # Current is valid (drop or comment). Check if file has "bad" statements.
            has_invalid = any(not is_valid_in_backup_script(s) for s in statements if s)
            
            if has_invalid:
                if idx == 0:
                    msgs.append(f"FAIL {name}: File contains non-backup-drop statements. "
                        f"Backup DROP scripts must be isolated.")
            else:
                # Isolated file. 
                # If current is an actual drop (not just a comment), we can say PASS.
                s_up = statements[idx].strip().upper()
                if s_up.startswith("DROP TABLE"):
                     msgs.append(f"PASS {name}: Backup drop statement is correctly isolated.")
                
        return msgs
