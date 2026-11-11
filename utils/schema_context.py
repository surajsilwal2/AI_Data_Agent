from utils.database import get_connection


def get_schema_context(schema_name='public'):
    schema_context = []

    try:
        connection = get_connection()
        with connection:
            with connection.cursor() as cursor:
                # step 1: get all tables

                cursor.execute(
                    """ 
                  SELECT table_name
                  FROM information_schema.tables
                  WHERE table_schema = %s
                  AND table_type = 'BASE TABLE'
                  ORDER BY table_schema;                
                   """,
                    (schema_name,)
                )
                tables = cursor.fetchall()

                schema_context.append(f"Database Schema: {schema_name}")

                # step 2: process each table

                for table in tables:
                    table_name = table[0]

                    schema_context.append(f"\nTable: {table_name}")

                    # step 3: get columns
                    cursor.execute(
                        """
                        SELECT
                          column_name,
                          data_type,
                          is_nullable,
                          column_default
                        FROM information_schema.columns
                        WHERE table_schema = %s
                        AND table_name = %s
                        ORDER BY ordinal_position;
                        """,
                        (schema_name, table_name)
                    )

                    columns = cursor.fetchall()

                    for column in columns:
                        column_name = column[0]
                        data_type = column[1]
                        nullable = column[2]
                        default = column[3]

                        schema_context.append(
                            f"Column: {column_name}"
                            f"Type: {data_type}"
                            f"Nullable: {nullable}"
                            f"Default: {default}"
                        )

                    # step 4: get primary keys
                    cursor.execute(
                        """
                        SELECT column_name
                        FROM information_schema.key_column_usage
                        Where table_schema = %s
                        AND table_name = %s
                        AND constraint_name IN (
                            SELECT constraint_name
                            FROM information_schema.table_constraints
                            WHERE table_schema = %s
                            AND table_name = %s
                            AND constraint_type = 'PRIMARY KEY'

                        )
                        """,
                        (
                            schema_name,
                            table_name,
                            schema_name,
                            table_name
                        )
                    )
                    primary_keys = cursor.fetchall()
                    schema_context.append(
                        f"Primary keys: {[pk[0] for pk in primary_keys]}"
                    )

                    # step 5: get foreign keys
                    cursor.execute(
                        """
                        SELECT
                            kcu.column_name,
                            ccu.table_name AS foreign_table,
                            ccu.column_name AS foreign_column
                        FROM information_schema.key_column_usage kcu
                        JOIN information_schema.constraint_column_usage ccu
                            ON kcu.constraint_name = ccu.constraint_name
                            AND kcu.constraint_schema = ccu.constraint_schema
                        WHERE kcu.table_schema = %s
                        AND kcu.table_name = %s
                        AND kcu.position_in_unique_constraint IS NOT NULL;
                        """,
                        (schema_name, table_name)
                    )

                    foreign_keys = cursor.fetchall()
                    for fk in foreign_keys:
                        schema_context.append(
                            f"Relationships:"
                            f"{table_name}.{fk[0]}"
                            f"{fk[1]}.{fk[2]}"
                        )
        return "\n".join(schema_context)
    except Exception as e:
        raise RuntimeError(
            f"failed to retrieve database schema: {e}"
        ) from e
    finally:
        if connection is not None:
            connection.close()
