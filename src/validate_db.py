import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "data" / "airfare_intelligence.db"
c = sqlite3.connect(DB)

print("DATABASE:", DB)
total = c.execute("SELECT COUNT(*) FROM raw_fare_quotes").fetchone()[0]
print("TOTAL ROWS:", total)

checks = [
    ("origin", "origin IS NULL OR TRIM(origin)=''"),
    ("destination", "destination IS NULL OR TRIM(destination)=''"),
    ("departure_date", "departure_date IS NULL OR TRIM(departure_date)=''"),
    ("airline", "airline IS NULL OR TRIM(airline)=''"),
    ("flight_number", "flight_number IS NULL OR TRIM(flight_number)=''"),
    ("departure_time", "departure_time IS NULL OR TRIM(departure_time)=''"),
    ("arrival_time", "arrival_time IS NULL OR TRIM(arrival_time)=''"),
    ("total_fare", "total_fare IS NULL OR total_fare<=0"),
]
for label, cond in checks:
    print(f"BAD {label.upper()}:", c.execute(
        f"SELECT COUNT(*) FROM raw_fare_quotes WHERE {cond}"
    ).fetchone()[0])

print("\nBY SOURCE:")
for r in c.execute(
    "SELECT source,COUNT(*) FROM raw_fare_quotes GROUP BY source ORDER BY source"
):
    print(r)

print("\nBY HORIZON:")
for r in c.execute(
    "SELECT advance_days,COUNT(*) FROM raw_fare_quotes "
    "GROUP BY advance_days ORDER BY advance_days"
):
    print(r)

c.close()
