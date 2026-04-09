import hashlib
import os

from flask import Flask, flash, redirect, render_template, request, session
from sqlalchemy import text

from database import create_db_engine
from schema import init_schema


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
if os.environ.get("FLASK_ENV") == "production":
    app.config["SESSION_COOKIE_SECURE"] = True

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_db_engine()
        init_schema(_engine)
    return _engine

engine = get_engine()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = hash_password(request.form["password"])
        phone = request.form["phone"].strip()

        with engine.connect() as conn:
            existing = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            ).mappings().first()

        if existing:
            flash("Email already registered!", "error")
            return render_template("register.html")

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO users (name, email, password, phone)
                    VALUES (:name, :email, :password, :phone)
                    """
                ),
                {
                    "name": name,
                    "email": email,
                    "password": password,
                    "phone": phone,
                },
            )

        flash("Registration successful! Please login.", "success")
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = hash_password(request.form["password"])

        with engine.connect() as conn:
            user = conn.execute(
                text(
                    """
                    SELECT * FROM users
                    WHERE email = :email AND password = :password
                    """
                ),
                {"email": email, "password": password},
            ).mappings().first()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect("/dashboard")

        flash("Invalid email or password!", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    with engine.connect() as conn:
        offered = conn.execute(
            text(
                """
                SELECT * FROM rides
                WHERE user_id = :user_id
                ORDER BY date DESC, time DESC
                """
            ),
            {"user_id": session["user_id"]},
        ).mappings().all()

        booked = conn.execute(
            text(
                """
                SELECT rides.*, bookings.id AS booking_id
                FROM bookings
                JOIN rides ON bookings.ride_id = rides.ride_id
                WHERE bookings.user_id = :user_id
                ORDER BY bookings.id DESC
                """
            ),
            {"user_id": session["user_id"]},
        ).mappings().all()

    return render_template("dashboard.html", offered=offered, booked=booked)


@app.route("/offer_ride", methods=["GET", "POST"])
def offer_ride():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO rides
                    (
                        user_id,
                        rider_name,
                        from_location,
                        to_location,
                        date,
                        time,
                        price,
                        seats,
                        bike_type,
                        helmet
                    )
                    VALUES
                    (
                        :user_id,
                        :rider_name,
                        :from_location,
                        :to_location,
                        :date,
                        :time,
                        :price,
                        :seats,
                        :bike_type,
                        :helmet
                    )
                    """
                ),
                {
                    "user_id": session["user_id"],
                    "rider_name": session["user_name"],
                    "from_location": request.form["from"].strip(),
                    "to_location": request.form["to"].strip(),
                    "date": request.form["date"],
                    "time": request.form["time"],
                    "price": int(request.form["price"]),
                    "seats": int(request.form["seats"]),
                    "bike_type": request.form["bike_type"],
                    "helmet": bool(request.form.get("helmet")),
                },
            )

        flash("Ride posted successfully!", "success")
        return redirect("/dashboard")

    return render_template("offer_ride.html")


@app.route("/search")
def search():
    from_loc = request.args.get("from", "").strip()
    to_loc = request.args.get("to", "").strip()
    date = request.args.get("date", "").strip()

    query = "SELECT * FROM rides WHERE seats > 0"
    params = {}

    if from_loc:
        query += " AND LOWER(from_location) LIKE :from_loc"
        params["from_loc"] = f"%{from_loc.lower()}%"

    if to_loc:
        query += " AND LOWER(to_location) LIKE :to_loc"
        params["to_loc"] = f"%{to_loc.lower()}%"

    if date:
        query += " AND date = :date"
        params["date"] = date

    query += " ORDER BY date, time"

    with engine.connect() as conn:
        rides = conn.execute(text(query), params).mappings().all()

    return render_template(
        "search_ride.html",
        rides=rides,
        from_val=from_loc,
        to_val=to_loc,
        date_val=date,
    )


@app.route("/book/<int:ride_id>")
def book_ride(ride_id):
    if "user_id" not in session:
        return redirect("/login")

    with engine.begin() as conn:
        ride = conn.execute(
            text("SELECT * FROM rides WHERE ride_id = :ride_id"),
            {"ride_id": ride_id},
        ).mappings().first()

        if not ride:
            flash("Ride not found!", "error")
            return redirect("/search")

        if ride["user_id"] == session["user_id"]:
            flash("You cannot book your own ride!", "error")
            return redirect("/search")

        already = conn.execute(
            text(
                """
                SELECT id FROM bookings
                WHERE ride_id = :ride_id AND user_id = :user_id
                """
            ),
            {"ride_id": ride_id, "user_id": session["user_id"]},
        ).mappings().first()

        if already:
            flash("You have already booked this ride!", "error")
            return redirect("/search")

        seat_update = conn.execute(
            text(
                """
                UPDATE rides
                SET seats = seats - 1
                WHERE ride_id = :ride_id AND seats > 0
                """
            ),
            {"ride_id": ride_id},
        )

        if seat_update.rowcount != 1:
            flash("No seats available!", "error")
            return redirect("/search")

        booking_insert = conn.execute(
            text(
                """
                INSERT INTO bookings (ride_id, user_id)
                VALUES (:ride_id, :user_id)
                ON CONFLICT (ride_id, user_id) DO NOTHING
                """
            ),
            {"ride_id": ride_id, "user_id": session["user_id"]},
        )

        if booking_insert.rowcount != 1:
            conn.execute(
                text("UPDATE rides SET seats = seats + 1 WHERE ride_id = :ride_id"),
                {"ride_id": ride_id},
            )
            flash("You have already booked this ride!", "error")
            return redirect("/search")

    flash("Ride booked successfully!", "success")
    return redirect("/dashboard")


@app.route("/cancel_booking/<int:booking_id>")
def cancel_booking(booking_id):
    if "user_id" not in session:
        return redirect("/login")

    with engine.begin() as conn:
        booking = conn.execute(
            text(
                """
                SELECT * FROM bookings
                WHERE id = :booking_id AND user_id = :user_id
                """
            ),
            {"booking_id": booking_id, "user_id": session["user_id"]},
        ).mappings().first()

        if booking:
            conn.execute(
                text("UPDATE rides SET seats = seats + 1 WHERE ride_id = :ride_id"),
                {"ride_id": booking["ride_id"]},
            )
            conn.execute(
                text("DELETE FROM bookings WHERE id = :booking_id"),
                {"booking_id": booking_id},
            )
            flash("Booking cancelled.", "success")

    return redirect("/dashboard")


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
