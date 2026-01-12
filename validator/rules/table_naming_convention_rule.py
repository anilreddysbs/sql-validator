# validator/rules/table_naming_convention_rule.py
"""
Validates table naming conventions for ALL tables (not just backup tables).

Rules:
- Table name must start with a letter (not number or underscore)
- Only alphanumeric characters and underscores allowed
- No hyphens, brackets, quotes, or special characters
- No parenthesized table lists
- Schema.table patterns are allowed, but table name itself must be valid
"""
from .rule_base import RuleBase
import re


class TableNamingConventionRule(RuleBase):
    id = "table_naming_convention"

    def _extract_table_info(self, statement):
        """
        Extract table name from SQL statement.
        Returns (table_name, full_syntax, error_message)
        
        Handles:
        - Simple: DROP TABLE mytable
        - Schema prefix: DROP TABLE schema.mytable
        - Quoted: DROP TABLE 'mytable' (will fail validation)
        - Parenthesized: DROP TABLE (t1, t2) (will fail validation)
        """
        s = statement.strip()
        
        # Check for parenthesized table list (non-standard)
        paren_match = re.search(r'\b(?:into|table)\s*\(', s, re.IGNORECASE)
        if paren_match:
            inner = re.search(r'\b(?:into|table)\s*\(([^)]+)\)', s, re.IGNORECASE)
            content = inner.group(1) if inner else "..."
            return None, f"({content})", "parenthesized table list is not allowed"
        
        # Check for quotes in table reference (non-standard for your convention)
        # Only match if the quote is at the start of the table name
        # e.g. "CREATE TABLE 'mytable'" or "INSERT INTO 'mytable'"
        quote_match = re.search(r"\b(?:into|table)\s+['\"]", s, re.IGNORECASE)
        if quote_match:
            # Extract the full table reference for error message
            ref_match = re.search(r"\b(?:into|table)\s+([^\s;]+)", s, re.IGNORECASE)
            full_ref = ref_match.group(1) if ref_match else "..."
            return None, full_ref, "quoted table names are not allowed"
        
        # Try to match schema.table pattern (with potential invalid chars in table name)
        schema_match = re.search(
            r"\b(?:into|table)\s+([A-Za-z][A-Za-z0-9_]*)\.([^\s;(]+)",
            s, re.IGNORECASE
        )
        if schema_match:
            table_name = schema_match.group(2)
            full_ref = f"{schema_match.group(1)}.{schema_match.group(2)}"
            return table_name, full_ref, None
        
        # Simple table name - capture everything up to space, semicolon, or parenthesis
        # This allows us to catch invalid characters like hyphens for validation
        simple_match = re.search(
            r"\b(?:into|table)\s+([^\s;(]+)",
            s, re.IGNORECASE
        )
        if simple_match:
            table_name = simple_match.group(1)
            return table_name, table_name, None
        
        return None, None, None

    def _validate_name(self, table_name):
        """
        Validate table name follows naming conventions.
        Returns (is_valid, error_message)
        """
        if not table_name:
            return False, "table name is empty"
        
        errors = []
        
        # Must start with a letter
        if table_name[0].isdigit():
            errors.append("cannot start with a number")
        elif table_name[0] == '_':
            errors.append("cannot start with an underscore")
        elif not table_name[0].isalpha():
            errors.append(f"cannot start with '{table_name[0]}'")
        
        # Check for invalid characters
        invalid_chars = []
        for char in table_name:
            if not (char.isalnum() or char == '_'):
                if char not in invalid_chars:
                    invalid_chars.append(char)
        
        if invalid_chars:
            chars_display = ', '.join(f"'{c}'" for c in invalid_chars)
            errors.append(f"contains invalid characters: {chars_display}")
        
        if errors:
            return False, "; ".join(errors)
        return True, None

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "Table Naming Convention")

        s = statements[idx].strip()
        
        # Only apply to statements that reference tables
        if not re.search(r'\b(table|into)\b', s, re.IGNORECASE):
            return msgs
        
        # Extract table info
        table_name, full_ref, extraction_error = self._extract_table_info(s)
        
        # Structural errors (parentheses, quotes)
        if extraction_error:
            msgs.append(self.fail(f"{name}: '{full_ref}' - {extraction_error}."))
            return msgs
        
        if not table_name:
            return msgs
        
        # Validate the table name
        is_valid, naming_error = self._validate_name(table_name)
        if not is_valid:
            msgs.append(self.fail(
                f"{name}: '{table_name.upper()}' {naming_error}."
            ))
        else:
            msgs.append(self.ok(
                f"{name}: '{table_name.upper()}' follows valid naming rules."
            ))
        
        return msgs
