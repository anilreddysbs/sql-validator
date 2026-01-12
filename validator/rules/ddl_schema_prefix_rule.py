# validator/rules/ddl_schema_prefix_rule.py
"""
Validates that DDL statements include a schema prefix.

DDL Statements covered:
- CREATE TABLE / INDEX / VIEW / SEQUENCE / SYNONYM
- ALTER TABLE
- DROP TABLE
- TRUNCATE TABLE
- RENAME
- COMMENT ON COLUMN
- GRANT (on objects)
- REVOKE (on objects)

Example:
  ✅ CREATE TABLE hr.employees (id NUMBER);
  ❌ CREATE TABLE employees (id NUMBER);     -- missing schema
  ❌ CREATE TABLE "hr".employees (id NUMBER); -- quotes not allowed
"""
from .rule_base import RuleBase
import re


class DDLSchemaPrefixRule(RuleBase):
    id = "ddl_schema_prefix"

    # DDL patterns that require schema prefix
    DDL_PATTERNS = [
        # CREATE statements
        (r'\bCREATE\s+TABLE\b', 'CREATE TABLE'),
        (r'\bCREATE\s+INDEX\b', 'CREATE INDEX'),
        (r'\bCREATE\s+(?:OR\s+REPLACE\s+)?VIEW\b', 'CREATE VIEW'),
        (r'\bCREATE\s+SEQUENCE\b', 'CREATE SEQUENCE'),
        (r'\bCREATE\s+(?:OR\s+REPLACE\s+)?SYNONYM\b', 'CREATE SYNONYM'),
        # ALTER / DROP / TRUNCATE
        (r'\bALTER\s+TABLE\b', 'ALTER TABLE'),
        (r'\bDROP\s+TABLE\b', 'DROP TABLE'),
        (r'\bTRUNCATE\s+TABLE\b', 'TRUNCATE TABLE'),
        # RENAME
        (r'\bRENAME\b', 'RENAME'),
        # COMMENT ON
        (r'\bCOMMENT\s+ON\s+COLUMN\b', 'COMMENT ON COLUMN'),
        (r'\bCOMMENT\s+ON\s+TABLE\b', 'COMMENT ON TABLE'),
        # GRANT / REVOKE (when they reference objects)
        (r'\bGRANT\s+\w+\s+ON\b', 'GRANT'),
        (r'\bREVOKE\s+\w+\s+ON\b', 'REVOKE'),
    ]

    def _detect_ddl_type(self, statement):
        """Detect DDL type from statement. Returns (pattern_match, ddl_name) or (None, None)."""
        s_upper = statement.upper()
        for pattern, ddl_name in self.DDL_PATTERNS:
            if re.search(pattern, s_upper):
                return pattern, ddl_name
        return None, None

    def _has_quotes_in_identifiers(self, statement, ddl_type):
        """
        Check if statement has quotes in object/identifier references.
        Excludes string values (like comment text in COMMENT ON statements).
        """
        s = statement.strip()
        
        # For COMMENT statements, only check the part before IS
        if ddl_type in ('COMMENT ON COLUMN', 'COMMENT ON TABLE'):
            is_pos = s.upper().find(' IS ')
            if is_pos > 0:
                s = s[:is_pos]  # Only check part before IS
        
        # Check for quoted identifiers (double quotes for Oracle, but also single quotes in wrong places)
        # Look for quotes near keywords that should have identifiers
        if re.search(r'\bTABLE\s+["\']', s, re.IGNORECASE):
            return True
        if re.search(r'\bINDEX\s+["\']', s, re.IGNORECASE):
            return True
        if re.search(r'\bVIEW\s+["\']', s, re.IGNORECASE):
            return True
        if re.search(r'\bSEQUENCE\s+["\']', s, re.IGNORECASE):
            return True
        if re.search(r'\bSYNONYM\s+["\']', s, re.IGNORECASE):
            return True
        if re.search(r'\bON\s+["\']', s, re.IGNORECASE):
            return True
        if re.search(r'\bCOLUMN\s+["\']', s, re.IGNORECASE):
            return True
        if re.search(r'\bRENAME\s+["\']', s, re.IGNORECASE):
            return True
        # Check for quotes around schema.table patterns
        if re.search(r'["\'][A-Za-z0-9_]+["\']\.', s):
            return True
        if re.search(r'\.["\'][A-Za-z0-9_]+["\']', s):
            return True
        
        return False

    def _extract_object_reference(self, statement, ddl_type):
        """
        Extract the object reference from DDL statement.
        Returns (has_schema, object_ref)
        """
        s = statement.strip()
        
        # Different patterns for different DDL types
        if ddl_type in ('CREATE TABLE', 'ALTER TABLE', 'DROP TABLE', 'TRUNCATE TABLE'):
            # Pattern: ... TABLE [schema.]table_name
            match = re.search(
                r'\bTABLE\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)',
                s, re.IGNORECASE
            )
            if match:
                obj_ref = match.group(1)
                has_schema = '.' in obj_ref
                return has_schema, obj_ref
        
        elif ddl_type == 'CREATE INDEX':
            # Pattern: CREATE INDEX idx_name ON [schema.]table_name
            match = re.search(
                r'\bON\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)',
                s, re.IGNORECASE
            )
            if match:
                obj_ref = match.group(1)
                has_schema = '.' in obj_ref
                return has_schema, obj_ref
        
        elif ddl_type in ('CREATE VIEW', 'CREATE SEQUENCE'):
            # Pattern: CREATE VIEW/SEQUENCE [schema.]name
            match = re.search(
                r'\b(?:VIEW|SEQUENCE)\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)',
                s, re.IGNORECASE
            )
            if match:
                obj_ref = match.group(1)
                has_schema = '.' in obj_ref
                return has_schema, obj_ref
        
        elif ddl_type == 'CREATE SYNONYM':
            # Pattern: CREATE SYNONYM [schema.]syn_name FOR [schema.]target
            # Check both synonym name and target
            syn_match = re.search(
                r'\bSYNONYM\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)',
                s, re.IGNORECASE
            )
            for_match = re.search(
                r'\bFOR\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)',
                s, re.IGNORECASE
            )
            # Check target object (after FOR)
            if for_match:
                obj_ref = for_match.group(1)
                has_schema = '.' in obj_ref
                return has_schema, obj_ref
            elif syn_match:
                obj_ref = syn_match.group(1)
                has_schema = '.' in obj_ref
                return has_schema, obj_ref
        
        elif ddl_type == 'RENAME':
            # Pattern: RENAME [schema.]old_name TO new_name
            match = re.search(
                r'\bRENAME\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)\s+TO\b',
                s, re.IGNORECASE
            )
            if match:
                obj_ref = match.group(1)
                has_schema = '.' in obj_ref
                return has_schema, obj_ref
        
        elif ddl_type in ('COMMENT ON COLUMN', 'COMMENT ON TABLE'):
            # Pattern: COMMENT ON COLUMN [schema.]table.column or COMMENT ON TABLE [schema.]table
            if ddl_type == 'COMMENT ON COLUMN':
                match = re.search(
                    r'\bCOLUMN\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+){1,2})',
                    s, re.IGNORECASE
                )
            else:
                match = re.search(
                    r'\bTABLE\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)',
                    s, re.IGNORECASE
                )
            if match:
                obj_ref = match.group(1)
                parts = obj_ref.split('.')
                # For COMMENT ON COLUMN: schema.table.column (3 parts) or table.column (2 parts)
                if ddl_type == 'COMMENT ON COLUMN':
                    has_schema = len(parts) >= 3
                else:
                    has_schema = len(parts) >= 2
                return has_schema, obj_ref
        
        elif ddl_type in ('GRANT', 'REVOKE'):
            # Pattern: GRANT/REVOKE ... ON [schema.]object
            match = re.search(
                r'\bON\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)',
                s, re.IGNORECASE
            )
            if match:
                obj_ref = match.group(1)
                has_schema = '.' in obj_ref
                return has_schema, obj_ref
        
        return None, None

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "DDL Schema Prefix")

        s = statements[idx].strip()

        # Detect DDL type
        pattern, ddl_type = self._detect_ddl_type(s)
        if not ddl_type:
            return msgs  # Not a DDL statement we care about

        # Check for quotes in identifiers (not allowed)
        if self._has_quotes_in_identifiers(s, ddl_type):
            msgs.append(self.fail(
                f"{name}: {ddl_type} statement contains quoted identifiers - not allowed."
            ))
            return msgs

        # Extract object reference and check for schema
        has_schema, obj_ref = self._extract_object_reference(s, ddl_type)
        
        if obj_ref is None:
            return msgs  # Could not extract object reference
        
        if has_schema:
            msgs.append(self.ok(
                f"{name}: {ddl_type} has schema prefix '{obj_ref}'."
            ))
        else:
            msgs.append(self.fail(
                f"{name}: {ddl_type} missing schema prefix. Found '{obj_ref}' - should be 'schema.{obj_ref}'."
            ))
        
        return msgs
