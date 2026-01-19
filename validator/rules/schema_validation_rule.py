# validator/rules/schema_validation_rule.py
"""
Validates schema usage in SQL statements.
Combines schema prefix validation and single-schema consistency validation.

Rules:
1. Schema Prefix: Check that target statements (DDL & DML) explicitly use a schema prefix (e.g., schema.table).
   - Fails if prefix is missing.
   - Fails if quoted identifiers are used (not allowed).
2. Single Schema: Check that all statements in the file refer to the SAME schema.
   - Ignores statements that don't have a schema/object reference.
   - Fails if multiple different schemas are detected.
"""
from .rule_base import RuleBase
import re

class SchemaValidationRule(RuleBase):
    id = "schema_validation"

    # patterns to match statements requiring verification
    # Format: (Regex Pattern, Statement Type Label, Extraction Regex for Object)
    # Note: Regex for object must have group 1 as the object reference
    PATTERNS = [
        # DDL
        (r'\bCREATE\s+TABLE\b', 'CREATE TABLE', r'\bTABLE\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bCREATE\s+INDEX\b', 'CREATE INDEX', r'\bON\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bCREATE\s+(?:OR\s+REPLACE\s+)?VIEW\b', 'CREATE VIEW', r'\bVIEW\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bCREATE\s+SEQUENCE\b', 'CREATE SEQUENCE', r'\bSEQUENCE\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bALTER\s+TABLE\b', 'ALTER TABLE', r'\bTABLE\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bDROP\s+TABLE\b', 'DROP TABLE', r'\bTABLE\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bTRUNCATE\s+TABLE\b', 'TRUNCATE TABLE', r'\bTABLE\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bRENAME\b', 'RENAME', r'\bRENAME\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)\s+TO\b'),
        (r'\bCOMMENT\s+ON\s+COLUMN\b', 'COMMENT ON COLUMN', r'\bCOLUMN\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+){1,2})'),
        (r'\bCOMMENT\s+ON\s+TABLE\b', 'COMMENT ON TABLE', r'\bTABLE\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bGRANT\s+.*?\s+ON\b', 'GRANT', r'\bON\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bREVOKE\s+.*?\s+ON\b', 'REVOKE', r'\bON\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        
        # DML - Added as per request
        (r'\bINSERT\s+INTO\b', 'INSERT', r'\bINSERT\s+INTO\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bUPDATE\b', 'UPDATE', r'\bUPDATE\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bDELETE\s+(?:FROM\b)?', 'DELETE', r'\bDELETE\s+(?:FROM\s+)?([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
        (r'\bMERGE\s+INTO\b', 'MERGE', r'\bMERGE\s+INTO\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)?)'),
    ]

    # Special handling for CREATE SYNONYM because it has two objects
    # We will handle it separately in logic

    def _get_statement_info(self, statement):
        """
        Identify statement type and extract target object.
        Returns: (type_label, object_ref, has_schema, has_quotes)
        """
        s = statement.strip()
        s_upper = s.upper()

        type_label = None
        obj_ref = None
        
        # Check SYNONYM first (special case)
        if 'CREATE SYNONYM' in s_upper or 'CREATE OR REPLACE SYNONYM' in s_upper:
            # Pattern: CREATE SYNONYM [schema.]syn_name FOR [schema.]target
            syn_match = re.search(r'\bSYNONYM\s+([A-Za-z0-9_"\']+(?:\.[A-Za-z0-9_"\']+)?)\s+FOR\s+([A-Za-z0-9_"\']+(?:\.[A-Za-z0-9_"\']+)?)\b', s, re.IGNORECASE)
            if syn_match:
                # We usually care about the TARGET for schema consistency? 
                # Or the synonym itself? Usually synonym creation is: CREATE SYNONYM schema.name FOR schema.table
                # Let's return the target 'FOR' object as the primary object to validate for prefixes?
                # Actually, the user likely wants the created object to have a prefix too.
                # Let's stick to the target table for consistency if possible, or just the synonym name.
                # Simplest consistency check: The SYNONYM name itself.
                obj_ref = syn_match.group(1)
                type_label = 'CREATE SYNONYM'

        if not type_label:
            for pattern, label, extraction_regex in self.PATTERNS:
                if re.search(pattern, s_upper):
                    match = re.search(extraction_regex, s, re.IGNORECASE)
                    if match:
                        type_label = label
                        obj_ref = match.group(1)
                        break
        
        if type_label and obj_ref:
            has_quotes = '"' in obj_ref or "'" in obj_ref
            has_schema = '.' in obj_ref
            return type_label, obj_ref, has_schema, has_quotes
        
        return None, None, None, None

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "Schema Validation")
        
        # 1. Prefix Check (Per-Statement)
        current_stmt = statements[idx]
        lbl, obj, has_schema, has_quotes = self._get_statement_info(current_stmt)

        if lbl:
            # Check for quotes
            if has_quotes:
                 msgs.append(self.fail(f"{name}: {lbl} statement contains quoted identifiers - not allowed."))

            # Check for missing prefix
            elif not has_schema:
                 msgs.append(self.fail(f"{name}: {lbl} missing schema prefix. - should be 'schema.object_name'."))
        
        # 2. Consistency Check (File-Level) - Only run once on the last statement to aggregate results?
        # Or better: We can't really "fail later" easily in this architecture without state.
        # But we can access `statements` list.
        # Let's just scan the whole file on the FIRST statement (index 0) and report consistency errors there.
        
        if idx == 0:
            found_schemas = set()
            schema_stmt_map = {}

            for i, stmt in enumerate(statements):
                _lbl, _obj, _has_schema, _has_quotes = self._get_statement_info(stmt)
                if _lbl and _has_schema and _obj and not _has_quotes:
                    # Extract schema part
                    # object is "schema.table" -> split by dot, take first part
                    parts = _obj.split('.')
                    # Handle multiple dots (e.g. comment on column schema.table.col)
                    # Use the first part as schema
                    schema_part = parts[0].upper()
                    
                    # Ignore standard oracle schemas if necessary? No, user usually wants their own schemas matches.
                    found_schemas.add(schema_part)
                    if schema_part not in schema_stmt_map:
                        schema_stmt_map[schema_part] = []
                    schema_stmt_map[schema_part].append(i + 1)

            if len(found_schemas) > 1:
                # Construct detailed error message
                details = []
                for sc in sorted(found_schemas):
                     count = len(schema_stmt_map[sc])
                     lines = ",".join(map(str, schema_stmt_map[sc][:3]))
                     if count > 3: lines += "..."
                     details.append(f"{sc} (lines {lines})")
                
                msgs.append(self.fail(
                    f"{name}: Multiple schemas detected in file: {', '.join(details)}. File must be single-schema."
                ))
            elif len(found_schemas) == 1:
                # Optionally report success for single schema? 
                # RuleBase usually reports success only if specifically checked.
                # "Validation passed" is implied if no fail, but we can add a debug/info note if needed.
                msgs.append(self.ok(f"{name}: Consistent schema usage detected ('{list(found_schemas)[0]}')."))

        return msgs
