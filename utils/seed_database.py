import csv
from contextlib import closing
from pathlib import Path

from psycopg2 import sql
from psycopg2.extras import execute_values

from utils.database import get_connection


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

TABLES = {
    "users": {
        "columns": (
            "user_id", "first_name", "last_name", "email", "phone", "city",
            "province", "user_type", "signup_date", "is_active",
        ),
        "primary_key": "user_id",
        "definition": """
            user_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            province TEXT NOT NULL,
            user_type TEXT NOT NULL,
            signup_date DATE NOT NULL,
            is_active BOOLEAN NOT NULL
        """,
    },
    "vehicles": {
        "columns": (
            "vehicle_id", "driver_id", "make", "model", "year", "license_plate",
            "color", "is_active",
        ),
        "primary_key": "vehicle_id",
        "definition": """
            vehicle_id INTEGER PRIMARY KEY,
            driver_id INTEGER NOT NULL REFERENCES public.users(user_id),
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            year SMALLINT NOT NULL,
            license_plate TEXT NOT NULL,
            color TEXT NOT NULL,
            is_active BOOLEAN NOT NULL
        """,
    },
    "rides": {
        "columns": (
            "ride_id", "rider_id", "driver_id", "requested_at", "pickup_time",
            "dropoff_time", "pickup_latitude", "pickup_longitude", "dropoff_latitude",
            "dropoff_longitude", "distance_km", "fare", "surge_multiplier", "status",
            "cancellation_reason",
        ),
        "primary_key": "ride_id",
        "definition": """
            ride_id INTEGER PRIMARY KEY,
            rider_id INTEGER NOT NULL REFERENCES public.users(user_id),
            driver_id INTEGER NOT NULL REFERENCES public.users(user_id),
            requested_at TIMESTAMP NOT NULL,
            pickup_time TIMESTAMP,
            dropoff_time TIMESTAMP,
            pickup_latitude DOUBLE PRECISION NOT NULL,
            pickup_longitude DOUBLE PRECISION NOT NULL,
            dropoff_latitude DOUBLE PRECISION NOT NULL,
            dropoff_longitude DOUBLE PRECISION NOT NULL,
            distance_km NUMERIC(10, 2) NOT NULL,
            fare NUMERIC(12, 2) NOT NULL,
            surge_multiplier NUMERIC(5, 2) NOT NULL,
            status TEXT NOT NULL,
            cancellation_reason TEXT
        """,
    },
    "ratings": {
        "columns": (
            "rating_id", "ride_id", "rider_id", "driver_id", "rating", "comment",
            "rated_at",
        ),
        "primary_key": "rating_id",
        "definition": """
            rating_id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL REFERENCES public.rides(ride_id),
            rider_id INTEGER NOT NULL REFERENCES public.users(user_id),
            driver_id INTEGER NOT NULL REFERENCES public.users(user_id),
            rating SMALLINT NOT NULL,
            comment TEXT,
            rated_at TIMESTAMP NOT NULL
        """,
    },
    "payments": {
        "columns": (
            "payment_id", "ride_id", "user_id", "amount", "payment_method",
            "payment_status", "transaction_id", "payment_time",
        ),
        "primary_key": "payment_id",
        "definition": """
            payment_id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL REFERENCES public.rides(ride_id),
            user_id INTEGER NOT NULL REFERENCES public.users(user_id),
            amount NUMERIC(12, 2) NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT NOT NULL,
            transaction_id TEXT NOT NULL,
            payment_time TIMESTAMP NOT NULL
        """,
    },
}


def _read_rows(table_name, columns):
    csv_path = DATA_DIR / f"{table_name}.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"Missing CSV file: {csv_path}")

    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != columns:
            raise ValueError(f"Unexpected CSV columns in {csv_path.name}")
        return [
            tuple(row[column] or None for column in columns)
            for row in reader
        ]


def _create_table(cursor, table_name, definition):
    cursor.execute(
        sql.SQL("CREATE TABLE IF NOT EXISTS public.{} ({})").format(
            sql.Identifier(table_name), sql.SQL(definition)
        )
    )


def _upsert_rows(cursor, connection, table_name, table_config, rows):
    columns = table_config["columns"]
    primary_key = table_config["primary_key"]
    insert_columns = sql.SQL(", ").join(map(sql.Identifier, columns))
    update_columns = sql.SQL(", ").join(
        sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(column), sql.Identifier(column))
        for column in columns
        if column != primary_key
    )
    query = sql.SQL(
        "INSERT INTO public.{} ({}) VALUES %s "
        "ON CONFLICT ({}) DO UPDATE SET {}"
    ).format(
        sql.Identifier(table_name),
        insert_columns,
        sql.Identifier(primary_key),
        update_columns,
    )
    execute_values(cursor, query.as_string(connection), rows, page_size=1000)


def seed_database():
    with closing(get_connection()) as connection:
        with connection:
            with connection.cursor() as cursor:
                for table_name, table_config in TABLES.items():
                    _create_table(cursor, table_name, table_config["definition"])

                counts = {}
                for table_name, table_config in TABLES.items():
                    rows = _read_rows(table_name, table_config["columns"])
                    if rows:
                        _upsert_rows(cursor, connection, table_name, table_config, rows)
                    counts[table_name] = len(rows)

    return counts


if __name__ == "__main__":
    for table_name, row_count in seed_database().items():
        print(f"Seeded {row_count} rows into {table_name}")