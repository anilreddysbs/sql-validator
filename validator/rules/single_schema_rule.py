# validator/rules/single_schema_rule.py
"""
Validates that a SQL file contains statements for only ONE schema.

This rule checks the entire file (all statements) and FAILS if multiple
different schemas are detected.

Example:
  ❌ FAIL - Mixed schemas:
    CREATE TABLE hr.employees (id NUMBER);
    CREATE TABLE finance.accounts (id NUMBER);
  
  ✅ PASS - Single schema:
    CREATE TABLE hr.employees (id NUMBER);
    CREATE TABLE hr.departments (id NUMBER);
"""
from .rule_base import RuleBase
import re


class SingleSchemaRule(RuleBase):
    id = "single_schema"
    
    # Track if we've already checked this file (to avoid duplicate messages)
    _checked_files = set()

    def _extract_schemas_from_statement(self, statement):
        """
        Extract all schema names from a statement.
        Returns a set of schema names found.
        """
        schemas = set()
        s = statement.strip()
        
        # Remove string literals to avoid matching emails or data as schemas
        # e.g. 'user@domain.com' shouldn't match schema 'domain'
        s_clean = re.sub(r"'[^']*'", '', s)
        
        # Pattern to match schema.object references
        # Matches: schema.table, schema.column, etc.
        matches = re.findall(
            r'\b([A-Za-z][A-Za-z0-9_]*)\.([A-Za-z][A-Za-z0-9_]*)',
            s_clean,
            re.IGNORECASE
        )
        
        for schema, obj in matches:
            # Exclude common keywords that might be followed by dot
            schema_upper = schema.upper()
            if schema_upper not in ('SYS', 'DUAL', 'USER', 'DATE', 'NUMBER', 'VARCHAR', 'VARCHAR2', 'CHAR', 'CLOB', 'BLOB', 'INT', 'INTEGER', 'DBMS_OUTPUT'):
                schemas.add(schema_upper)
        
        return schemas

    def apply(self, statements, idx, context):
        msgs = []
        name = self.params.get("rule_name", "Single Schema Per File")
        
        # Only run this check once per validation (on the first statement)
        if idx != 0:
            return msgs
        
        # Collect all schemas from all statements
        all_schemas = set()
        schema_statements = {}  # Track which statements use which schemas
        
        for i, stmt in enumerate(statements):
            if stmt:
                schemas = self._extract_schemas_from_statement(stmt)
                for schema in schemas:
                    all_schemas.add(schema)
                    if schema not in schema_statements:
                        schema_statements[schema] = []
                    schema_statements[schema].append(i + 1)  # 1-based index
        
        # Check results
        if len(all_schemas) == 0:
            msgs.append(self.fail(
                f"{name}: No schema prefixes found in file. All statements must use schema.object format."
            ))
        elif len(all_schemas) == 1:
            schema = list(all_schemas)[0]
            msgs.append(self.ok(
                f"{name}: File uses single schema '{schema}' consistently."
            ))
        else:
            # Multiple schemas found - FAIL
            schema_list = ', '.join(sorted(all_schemas))
            details = []
            for schema in sorted(all_schemas):
                stmt_nums = schema_statements[schema][:3]  # Show first 3 statements
                if len(schema_statements[schema]) > 3:
                    details.append(f"'{schema}' in queries {stmt_nums}...")
                else:
                    details.append(f"'{schema}' in queries {stmt_nums}")
            
            msgs.append(self.fail(
                f"{name}: Multiple schemas detected in single file. "
                f"Found: {schema_list}. Each database should have a separate DDL script."
            ))
        
        return msgs
