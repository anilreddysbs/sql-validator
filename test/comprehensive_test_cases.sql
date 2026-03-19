-- ==========================================================
-- SQL VALIDATOR - COMPREHENSIVE TEST SUITE
-- This file contains test cases for all 16 validation rules.
-- ==========================================================

-- 1️⃣ DML Commit Rule & 14️⃣ Semicolon Rule
-- PASS: DML followed by COMMIT
DELETE FROM hr.employees WHERE id = 101;
COMMIT;

-- FAIL: DML missing COMMIT
UPDATE hr.employees SET salary = 5000 WHERE id = 101;

-- 2️⃣ DDL No-Commit Rule & 15️⃣ Tablespace Restriction
-- PASS: DDL with correct tablespace, no commit
CREATE TABLE hr.test_table (id NUMBER) TABLESPACE DATA_TBS;

-- FAIL: DDL followed by COMMIT
CREATE TABLE hr.wrong_logic (id NUMBER) TABLESPACE DATA_TBS;
COMMIT;

-- FAIL: Forbidden Tablespace (SYSTEM)
CREATE TABLE hr.forbidden_tbs (id NUMBER) TABLESPACE SYSTEM;

-- 3️⃣ GRANT / REVOKE No-Commit Rule & 10️⃣ GRANT ALL & 11️⃣ Grant Privilege
-- PASS: Grant SELECT to regular user
GRANT SELECT ON hr.employees TO APP_USER;

-- PASS: Grant UPDATE to a LOADER Alias (RDEP_FRAUD)
GRANT UPDATE ON hr.employees TO RDEP_FRAUD;

-- FAIL: GRANT ALL forbidden
GRANT ALL ON hr.employees TO LOADER;

-- FAIL: Grant INSERT to regular user (Strictly SELECT only)
GRANT INSERT ON hr.employees TO SOME_OTHER_USER;

-- 4️⃣ PL/SQL Slash Rule
-- PASS: Ends with /
BEGIN
  NULL;
END;
/

-- FAIL: Missing /
BEGIN
  NULL;
END;

-- 5️⃣ Object Name Length (Max 30) & 7️⃣ Table Naming
-- PASS: Valid name
CREATE TABLE hr.valid_name (id NUMBER) TABLESPACE DATA_TBS;

-- FAIL: Too long (> 30 chars)
CREATE TABLE hr.this_name_is_way_too_long_for_oracle_database_limits (id NUMBER) TABLESPACE DATA_TBS;

-- FAIL: Invalid naming (starts with number)
CREATE TABLE hr.123_invalid (id NUMBER) TABLESPACE DATA_TBS;

-- 6️⃣ Backup Table Rules & 9️⃣ Backup Grant & 13️⃣ NOLOGGING
-- PASS: Correct backup table setup
CREATE TABLE hr.data_bkp_tbd (id NUMBER) TABLESPACE BACKUP_TBS;

-- FAIL: Backup missing _TBD suffix
CREATE TABLE hr.data_bkp (id NUMBER) TABLESPACE BACKUP_TBS;

-- FAIL: Backup in wrong tablespace
CREATE TABLE hr.data_bkp_tbd (id NUMBER) TABLESPACE DATA_TBS;

-- FAIL: NOLOGGING forbidden
CREATE TABLE hr.no_log_tbd (id NUMBER) TABLESPACE BACKUP_TBS NOLOGGING;

-- 8️⃣ Schema Validation (Prefix & Consistency)
-- FAIL: Missing schema prefix
CREATE TABLE no_prefix (id NUMBER) TABLESPACE DATA_TBS;

-- FAIL: Mixed schemas (must be strict single-schema)
CREATE TABLE finance.foreign_table (id NUMBER) TABLESPACE DATA_TBS;

-- 12️⃣ Backup Table Drop Limit & 16️⃣ Backup Drop Separation
-- This file will trigger Rule 16 because it MIXES Drops with Creates.
DROP TABLE hr.temp_data_tbd;
