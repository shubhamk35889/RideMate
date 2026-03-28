from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, MetaData
from sqlalchemy import String, Table, UniqueConstraint, func

from database import create_db_engine


engine = create_db_engine()
metadata = MetaData()

Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(120), nullable=False),
    Column("email", String(255), nullable=False, unique=True),
    Column("password", String(255), nullable=False),
    Column("phone", String(30)),
)

Table(
    "rides",
    metadata,
    Column("ride_id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("rider_name", String(120), nullable=False),
    Column("from_location", String(255), nullable=False),
    Column("to_location", String(255), nullable=False),
    Column("date", Date, nullable=False),
    Column("time", String(10), nullable=False),
    Column("price", Integer, nullable=False),
    Column("seats", Integer, nullable=False, server_default="1"),
    Column("bike_type", String(50), nullable=False, server_default="Any"),
    Column("helmet", Boolean, nullable=False, server_default="false"),
)

Table(
    "bookings",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("ride_id", Integer, ForeignKey("rides.ride_id"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("booked_at", DateTime, nullable=False, server_default=func.now()),
    UniqueConstraint("ride_id", "user_id", name="uq_bookings_ride_user"),
)

metadata.create_all(engine)
print("Database initialized successfully.")
