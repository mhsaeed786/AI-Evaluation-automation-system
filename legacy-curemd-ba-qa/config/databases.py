"""
Database Connection Manager for HealthOS BA/QA Automation Suite.

Handles all SQL Server connections with connection pooling,
query execution, and result formatting.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    logger.warning("pyodbc not installed. Database features will be limited.")


class DatabaseManager:
    """Manages database connections and query execution."""

    def __init__(self):
        self._connections: Dict[str, Any] = {}
        self._query_log: List[Dict] = []

    def get_connection(self, db_key: str = "release01_fhir", autocommit: bool = False):
        """
        Get a database connection for the specified environment.

        Args:
            db_key: Database configuration key (e.g., 'release01_fhir')
            autocommit: Whether to enable autocommit mode

        Returns:
            pyodbc.Connection object
        """
        if not PYODBC_AVAILABLE:
            raise RuntimeError("pyodbc is not installed. Run: pip install pyodbc")

        from config.settings import get_settings
        settings = get_settings()
        db_config = settings.get_db_config(db_key)

        conn_str = db_config.connection_string
        conn = pyodbc.connect(conn_str, autocommit=autocommit)
        conn.timeout = db_config.timeout
        return conn

    @contextmanager
    def connection(self, db_key: str = "release01_fhir", autocommit: bool = False):
        """Context manager for database connections with automatic cleanup."""
        conn = None
        try:
            conn = self.get_connection(db_key, autocommit=autocommit)
            yield conn
        except Exception as e:
            logger.error(f"Database connection error ({db_key}): {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        db_key: str = "release01_fhir",
        fetch_all: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as list of dictionaries.

        Args:
            query: SQL query string
            params: Query parameters tuple
            db_key: Database configuration key
            fetch_all: If True fetches all rows, otherwise fetches one

        Returns:
            List of dictionaries with column names as keys
        """
        results = []
        log_entry = {
            "query": query[:500],
            "db_key": db_key,
            "params": str(params)[:200] if params else None,
        }

        try:
            with self.connection(db_key) as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch_all:
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    for row in cursor.fetchall():
                        results.append(dict(zip(columns, row)))
                else:
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    row = cursor.fetchone()
                    if row:
                        results.append(dict(zip(columns, row)))

                cursor.close()
                log_entry["status"] = "success"
                log_entry["row_count"] = len(results)

        except Exception as e:
            log_entry["status"] = "error"
            log_entry["error"] = str(e)
            logger.error(f"Query execution error: {e}\nQuery: {query[:200]}")
            raise

        finally:
            self._query_log.append(log_entry)

        return results

    def execute_non_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        db_key: str = "release01_fhir",
    ) -> int:
        """
        Execute a non-query SQL statement (INSERT, UPDATE, DELETE).

        Args:
            query: SQL statement
            params: Query parameters tuple
            db_key: Database configuration key

        Returns:
            Number of affected rows
        """
        affected = 0
        try:
            with self.connection(db_key, autocommit=True) as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                affected = cursor.rowcount
                cursor.close()
        except Exception as e:
            logger.error(f"Non-query execution error: {e}\nQuery: {query[:200]}")
            raise
        return affected

    def execute_insert(
        self,
        table: str,
        data: Dict[str, Any],
        db_key: str = "release01_fhir",
    ) -> int:
        """
        Insert a row into a table.

        Args:
            table: Target table name
            data: Column name to value mapping
            db_key: Database configuration key

        Returns:
            Number of affected rows
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute_non_query(query, tuple(data.values()), db_key)

    def get_tables(self, db_key: str = "release01_fhir") -> List[str]:
        """Get list of all user tables in the database."""
        query = """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """
        results = self.execute_query(query, db_key=db_key)
        return [r["TABLE_NAME"] for r in results]

    def get_columns(self, table: str, db_key: str = "release01_fhir") -> List[Dict]:
        """Get column information for a table."""
        query = """
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
               IS_NULLABLE, COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
        """
        return self.execute_query(query, (table,), db_key)

    def get_triggers(self, db_key: str = "release01_fhir") -> List[Dict]:
        """Get all triggers in the database."""
        query = """
        SELECT t.name AS trigger_name,
               OBJECT_NAME(t.parent_id) AS table_name,
               m.definition AS trigger_definition,
               CASE WHEN t.is_instead_of_trigger = 1 THEN 'INSTEAD OF'
                    ELSE 'AFTER' END AS trigger_type,
               CASE WHEN t.is_disabled = 0 THEN 'ENABLED'
                    ELSE 'DISABLED' END AS status
        FROM sys.triggers t
        JOIN sys.sql_modules m ON t.object_id = m.object_id
        WHERE t.is_ms_shipped = 0
        ORDER BY OBJECT_NAME(t.parent_id), t.name
        """
        return self.execute_query(query, db_key=db_key)

    def get_stored_procedures(self, db_key: str = "release01_fhir") -> List[Dict]:
        """Get all stored procedures in the database."""
        query = """
        SELECT p.name AS procedure_name,
               m.definition AS procedure_definition,
               SCHEMA_NAME(p.schema_id) AS schema_name
        FROM sys.procedures p
        JOIN sys.sql_modules m ON p.object_id = m.object_id
        WHERE p.is_ms_shipped = 0
        ORDER BY p.name
        """
        return self.execute_query(query, db_key=db_key)

    def get_foreign_keys(self, db_key: str = "release01_fhir") -> List[Dict]:
        """Get all foreign key relationships."""
        query = """
        SELECT
            OBJECT_NAME(fk.parent_object_id) AS table_name,
            COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS column_name,
            OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
            COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS referenced_column,
            fk.name AS constraint_name
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
        ORDER BY OBJECT_NAME(fk.parent_object_id)
        """
        return self.execute_query(query, db_key=db_key)

    def check_record_queue(
        self,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        db_key: str = "release01_fhir",
    ) -> List[Dict]:
        """
        Check FHIR_RecordQueue entries for verification.

        Args:
            resource_id: Filter by specific resource ID
            resource_type: Filter by resource type
            db_key: Database configuration key
        """
        conditions = []
        params = []
        if resource_id:
            conditions.append("ResourceID = ?")
            params.append(resource_id)
        if resource_type:
            conditions.append("ResourceName = ?")
            params.append(resource_type)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT * FROM FHIR_RecordQueue{where} ORDER BY QueueID DESC"
        return self.execute_query(query, tuple(params) if params else None, db_key)

    def get_query_log(self) -> List[Dict]:
        """Get the history of executed queries."""
        return self._query_log

    def test_connection(self, db_key: str = "release01_fhir") -> Dict[str, Any]:
        """Test a database connection and return status info."""
        try:
            with self.connection(db_key) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION AS version, DB_NAME() AS db_name")
                row = cursor.fetchone()
                cursor.close()
                return {
                    "status": "connected",
                    "server_version": row[0] if row else "Unknown",
                    "database": row[1] if row else "Unknown",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }


_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get the global DatabaseManager singleton."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
