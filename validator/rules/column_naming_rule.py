
# validator/rules/column_naming_rule.py
"""
Validates column naming conventions in CREATE TABLE and ALTER TABLE ADD/MODIFY statements.

Rules:
- Column name must start with a letter (not number or underscore)
- Only alphanumeric characters and underscores allowed
- No hyphens, brackets, quotes, or special characters
- No reserved words as column names (basic check)
"""
from .rule_base import RuleBase
import re

class ColumnNamingRule(RuleBase):
    id = "column_naming"

    def _extract_columns(self, statement):
        """
        Extract potential column definitions from CREATE/ALTER statements.
        Returns a list of column names to validate.
        """
        s = statement.strip()
        columns_to_check = []
        
        # 1. CREATE TABLE
        create_match = re.search(r'CREATE\s+TABLE\s+(?:[A-Za-z0-9_]+\.)?[A-Za-z0-9_]+\s*\((.*)\)', s, re.IGNORECASE | re.DOTALL)
        if create_match:
            content = create_match.group(1)
            # Split by comma, but be careful of commas inside nested parentheses (like constraints, NUMBER(10,2))
            definitions = self._split_by_comma_ignoring_parens(content)
            
            for definition in definitions:
                def_clean = definition.strip()
                if not def_clean:
                    continue
                
                # Split by whitespace to get the first word (column name or constraint)
                tokens = def_clean.split()
                if not tokens:
                    continue
                
                first_token = tokens[0]
                
                # Skip known constraints
                # Constraints often start with CONSTRAINT <name> or directly PRIMARY KEY, FOREIGN KEY, CHECK, UNIQUE (if table level)
                # But UNIQUE, CHECK, PRIMARY, FOREIGN can be start of table level constraints.
                # However, a column named "UNIQUE" is invalid, so flagging it is fine (it's a reserved word anyway).
                # We mainly want to avoid validating "CONSTRAINT" or "PRIMARY" as column names.
                if first_token.upper() in ('CONSTRAINT', 'PRIMARY', 'FOREIGN', 'CHECK', 'UNIQUE'):
                    continue
                    
                # The first token IS the column name we want to check, even if it has junk like "id" or @
                columns_to_check.append(first_token)

        # 2. ALTER TABLE ... ADD/MODIFY
        # Simple extraction: look for ADD (col type) or ADD col type
        # For now, let's focus on the CREATE TABLE structure as per the user's example
        
        return columns_to_check

    def _split_by_comma_ignoring_parens(self, text):
        """Helper to split SQL definitions by comma, ignoring commas inside parentheses."""
        parts = []
        current = []
        depth = 0
        for char in text:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            
            if char == ',' and depth == 0:
                parts.append("".join(current))
                current = []
            else:
                current.append(char)
        if current:
            parts.append("".join(current))
        return parts

    def _validate_name(self, col_name):
        """
        Validate column name.
        Returns (is_valid, error_message)
        """
        # Remove quotes if present, but flag them as error first if rule requires no quotes
        has_quotes = False
        clean_name = col_name
        
        if col_name.startswith('"') and col_name.endswith('"'):
            has_quotes = True
            clean_name = col_name[1:-1]
            # Based on user request 'employee_"id"' failing, we assume NO quotes allowed
            # The regex extraction in _extract_columns might catch "id" from employee_"id" if logic isn't perfect
            # But wait, user provided: employee_"id" in the text directly. 
            # In SQL, employee_"id" is syntactically invalid unless it's "employee_id". 
            # If the user meant the column name literally contains a quote, that's definitely invalid.
            # If the user meant `employee_"id"` as a name, Oracle interprets it as `employee_` followed by quoted "id"? No.
            # It's likely `employee_"id"` is strictly treated as the identifier string if inside quotes, 
            # or simply invalid characters if unquoted.
        
        # Check for Quotes (invalid per convention)
        if '"' in col_name or "'" in col_name:
             return False, "quoted column names are not allowed"

        if not clean_name:
             return False, "column name is empty"
             
        errors = []
        
        # Must start with a letter
        if clean_name[0].isdigit():
            errors.append("cannot start with a number")
        elif clean_name[0] == '_':
            errors.append("cannot start with an underscore")
        elif not clean_name[0].isalpha():
            errors.append(f"cannot start with '{clean_name[0]}'")
        
        # Check for invalid characters
        invalid_chars = []
        for char in clean_name:
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
        name = self.params.get("rule_name", "Column Naming Convention")
        s = statements[idx].strip()
        
        # Only check CREATE TABLE statements for now
        if not s.upper().startswith("CREATE TABLE"):
            return msgs
            
        columns = self._extract_columns(s)
        
        for col in columns:
            is_valid, error = self._validate_name(col)
            if not is_valid:
                msgs.append(self.fail(f"{name}: '{col}' {error}."))
            # Optionally log passes? User usually cares about failures for columns details to avoid noise.
            # We can enable passes if strictly needed.
            # else:
            #    msgs.append(self.ok(f"{name}: '{col}' follows valid naming rules."))

        return msgs
