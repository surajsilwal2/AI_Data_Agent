import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    return psycopg2.connect(database_url, connect_timeout=10)


def execute_sql_query(query: str):
    connection = None
    try:
        connection = get_connection()
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute("SET LOCAL statement_timeout = '10s';")
                cursor.execute(query)

                results = cursor.fetchall()

                columns = [
                    description[0]
                    for description in cursor.description
                ]

                formatted_results = [
                    dict(zip(columns, row)) for row in results
                ]

                return {
                    "success": True,
                    "columns": columns,
                    "data": formatted_results,
                    "row_count": len(formatted_results)
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": []
        }
    finally:
        if connection is not None:
            connection.close()


