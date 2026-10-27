import psycopg2
import logging

DB_CONFIG = {
    "host": "103.171.96.104",
    "database": "weather",
    "user": "postgres",
    "password": "Intel@1968",
    "port": 5432
}

def update_insert_at():
    """Add one day to insert_at for records inserted two days ago."""

    conn = None

    try:
        conn = psycopg2.connect(**DB_CONFIG)

        with conn:
            with conn.cursor() as cur:
                query = """
                    UPDATE weatherdata.hazard_cyclone
                    SET insert_at = insert_at + INTERVAL '1 day'
                    WHERE DATE(insert_at) = CURRENT_DATE - 2 and 
                    "date"  >= current_date
                    RETURNING *;
                """

                cur.execute(query)
                updated_records = cur.fetchall()

                print(f"insert_at updated records: {len(updated_records)}")

                return updated_records

    except Exception:
        logging.exception("Failed to update insert_at")
        raise

    finally:
        if conn:
            conn.close()


def update_days():
    """Update days for records whose insert_at date is yesterday."""

    conn = None

    try:
        conn = psycopg2.connect(**DB_CONFIG)

        with conn:
            with conn.cursor() as cur:
                query = """
                    UPDATE weatherdata.hazard_cyclone
                    SET days = CASE
                        WHEN "date"::date = CURRENT_DATE     THEN 'Day1'
                        WHEN "date"::date = CURRENT_DATE + 1 THEN 'Day2'
                        WHEN "date"::date = CURRENT_DATE + 2 THEN 'Day3'
                        WHEN "date"::date = CURRENT_DATE + 3 THEN 'Day4'
                        WHEN "date"::date = CURRENT_DATE + 4 THEN 'Day5'
                        WHEN "date"::date = CURRENT_DATE + 5 THEN 'Day6'
                        WHEN "date"::date = CURRENT_DATE + 6 THEN 'Day7'
                        ELSE days
                    END
                    WHERE DATE(insert_at) = CURRENT_DATE -1
                     And "date"::date >= CURRENT_DATE
                      AND "date"::date BETWEEN CURRENT_DATE
                                           AND CURRENT_DATE + 6
                    RETURNING *;
                """

                cur.execute(query)
                updated_records = cur.fetchall()

                print(f"days updated records: {len(updated_records)}")
                return updated_records

    except Exception:
        logging.exception("Failed to update days")
        raise

    finally:
        if conn:
            conn.close()



if __name__ == "__main__":
    # Step 1: Shift insert_at by one day
    update_insert_at()

    # Step 2: Update the days column
    update_days()
    
    