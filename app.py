from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import random
import os

app = Flask(__name__)

app.secret_key = "predictx-ai-secret-key-change-this"

DATABASE = "users.db"


# =========================================================
# DATABASE
# =========================================================

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


# =========================================================
# MACHINE ANALYSIS ENGINE
# =========================================================

def analyze_machine(
    temperature,
    vibration,
    voltage,
    current,
    rpm
):

    score = 100

    warnings = []

    recommendations = []

    parameter_status = {
        "temperature": "Normal",
        "vibration": "Normal",
        "voltage": "Normal",
        "current": "Normal",
        "rpm": "Normal"
    }


    # -----------------------------------------------------
    # TEMPERATURE
    # -----------------------------------------------------

    if temperature >= 90:

        score -= 30

        parameter_status["temperature"] = "Critical"

        warnings.append(
            "Critical temperature detected"
        )

        recommendations.append(
            "Stop the machine and inspect the cooling system immediately."
        )

    elif temperature >= 75:

        score -= 15

        parameter_status["temperature"] = "Warning"

        warnings.append(
            "Machine temperature is high"
        )

        recommendations.append(
            "Inspect cooling system and lubrication."
        )

    elif temperature >= 65:

        score -= 7

        parameter_status["temperature"] = "Attention"

        warnings.append(
            "Temperature is slightly above normal."
        )


    # -----------------------------------------------------
    # VIBRATION
    # -----------------------------------------------------

    if vibration >= 8:

        score -= 30

        parameter_status["vibration"] = "Critical"

        warnings.append(
            "Critical vibration level detected"
        )

        recommendations.append(
            "Inspect bearings, shaft alignment and machine mounting."
        )

    elif vibration >= 5:

        score -= 15

        parameter_status["vibration"] = "Warning"

        warnings.append(
            "High vibration detected"
        )

        recommendations.append(
            "Inspect bearings and shaft alignment."
        )

    elif vibration >= 3:

        score -= 7

        parameter_status["vibration"] = "Attention"

        warnings.append(
            "Vibration level is increasing."
        )


    # -----------------------------------------------------
    # VOLTAGE
    # -----------------------------------------------------

    if voltage < 200 or voltage > 250:

        score -= 15

        parameter_status["voltage"] = "Critical"

        warnings.append(
            "Abnormal voltage detected"
        )

        recommendations.append(
            "Inspect electrical supply and motor connections."
        )

    elif voltage < 210 or voltage > 245:

        score -= 7

        parameter_status["voltage"] = "Warning"

        warnings.append(
            "Voltage is outside the preferred operating range."
        )


    # -----------------------------------------------------
    # CURRENT
    # -----------------------------------------------------

    if current >= 15:

        score -= 15

        parameter_status["current"] = "Critical"

        warnings.append(
            "Critical motor current detected"
        )

        recommendations.append(
            "Check motor load and possible mechanical blockage."
        )

    elif current >= 12:

        score -= 7

        parameter_status["current"] = "Warning"

        warnings.append(
            "Motor current is high"
        )

        recommendations.append(
            "Inspect motor load and mechanical resistance."
        )


    # -----------------------------------------------------
    # RPM
    # -----------------------------------------------------

    if rpm < 1200:

        score -= 10

        parameter_status["rpm"] = "Warning"

        warnings.append(
            "Motor speed is below normal"
        )

        recommendations.append(
            "Check motor load, drive settings and mechanical resistance."
        )

    elif rpm > 1800:

        score -= 10

        parameter_status["rpm"] = "Warning"

        warnings.append(
            "Motor speed is above normal"
        )

        recommendations.append(
            "Check motor controller and speed settings."
        )


    # -----------------------------------------------------
    # SCORE
    # -----------------------------------------------------

    score = max(0, min(100, score))


    # -----------------------------------------------------
    # MACHINE STATUS
    # -----------------------------------------------------

    if score >= 85:

        status = "Healthy"

        risk = "Low"

        status_type = "healthy"

    elif score >= 65:

        status = "Warning"

        risk = "Medium"

        status_type = "warning"

    else:

        status = "Critical"

        risk = "High"

        status_type = "critical"


    # -----------------------------------------------------
    # DEFAULT MESSAGES
    # -----------------------------------------------------

    if not warnings:

        warnings.append(
            "All monitored parameters are within normal range."
        )


    if not recommendations:

        recommendations.append(
            "Machine is operating normally. Continue scheduled maintenance."
        )


    # -----------------------------------------------------
    # ESTIMATED LIFE
    # -----------------------------------------------------

    remaining_life = round(
        180 * score / 100
    )


    # -----------------------------------------------------
    # MAINTENANCE PRIORITY
    # -----------------------------------------------------

    if risk == "High":

        maintenance_priority = "Immediate"

    elif risk == "Medium":

        maintenance_priority = "Scheduled"

    else:

        maintenance_priority = "Routine"


    return {

        "health": score,

        "status": status,

        "status_type": status_type,

        "risk": risk,

        "remaining_days": remaining_life,

        "maintenance_priority":
            maintenance_priority,

        "warnings":
            warnings,

        "recommendations":
            recommendations,

        "parameter_status":
            parameter_status
    }


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json()

    name = data.get("name", "").strip()

    email = data.get("email", "").strip().lower()

    password = data.get("password", "")


    if not name or not email or not password:

        return jsonify({
            "success": False,
            "message": "All fields are required."
        }), 400


    if len(password) < 6:

        return jsonify({
            "success": False,
            "message": "Password must contain at least 6 characters."
        }), 400


    connection = get_db()


    existing_user = connection.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    ).fetchone()


    if existing_user:

        connection.close()

        return jsonify({
            "success": False,
            "message": "An account with this email already exists."
        }), 409


    password_hash = generate_password_hash(
        password
    )


    connection.execute(
        """
        INSERT INTO users
        (name, email, password)
        VALUES (?, ?, ?)
        """,
        (
            name,
            email,
            password_hash
        )
    )


    connection.commit()

    connection.close()


    return jsonify({

        "success": True,

        "message":
            "Account created successfully. Please login."

    })


# =========================================================
# LOGIN
# =========================================================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json()

    email = data.get(
        "email",
        ""
    ).strip().lower()

    password = data.get(
        "password",
        ""
    )


    connection = get_db()


    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()


    connection.close()


    if not user:

        return jsonify({

            "success": False,

            "message":
                "Invalid email or password."

        }), 401


    if not check_password_hash(
        user["password"],
        password
    ):

        return jsonify({

            "success": False,

            "message":
                "Invalid email or password."

        }), 401


    session["user_id"] = user["id"]

    session["user_name"] = user["name"]

    session["user_email"] = user["email"]


    return jsonify({

        "success": True,

        "message":
            "Login successful.",

        "user": {

            "name":
                user["name"],

            "email":
                user["email"]

        }

    })


# =========================================================
# CURRENT USER
# =========================================================

@app.route("/api/user")
def current_user():

    if "user_id" not in session:

        return jsonify({

            "logged_in": False

        })


    return jsonify({

        "logged_in": True,

        "user": {

            "name":
                session["user_name"],

            "email":
                session["user_email"]

        }

    })


# =========================================================
# LOGOUT
# =========================================================

@app.route("/api/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({

        "success": True,

        "message":
            "Logged out successfully."

    })


# =========================================================
# MACHINE ANALYSIS API
# =========================================================

@app.route("/api/analyze", methods=["POST"])
def analyze():

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message":
                "Please login first."

        }), 401


    data = request.get_json()


    try:

        temperature = float(
            data.get(
                "temperature",
                65
            )
        )

        vibration = float(
            data.get(
                "vibration",
                3
            )
        )

        voltage = float(
            data.get(
                "voltage",
                230
            )
        )

        current = float(
            data.get(
                "current",
                8
            )
        )

        rpm = float(
            data.get(
                "rpm",
                1450
            )
        )

    except (TypeError, ValueError):

        return jsonify({

            "success": False,

            "message":
                "Invalid machine values."

        }), 400


    result = analyze_machine(

        temperature,

        vibration,

        voltage,

        current,

        rpm

    )


    result["success"] = True

    result["temperature"] = temperature

    result["vibration"] = vibration

    result["voltage"] = voltage

    result["current"] = current

    result["rpm"] = rpm


    return jsonify(result)


# =========================================================
# LIVE MACHINE DATA
# =========================================================

@app.route("/api/live")
def live():

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message":
                "Please login first."

        }), 401


    temperature = round(
        random.uniform(55, 82),
        1
    )

    vibration = round(
        random.uniform(1.5, 6.5),
        2
    )

    voltage = round(
        random.uniform(215, 245),
        1
    )

    current = round(
        random.uniform(6, 14),
        2
    )

    rpm = round(
        random.uniform(1250, 1500)
    )


    result = analyze_machine(

        temperature,

        vibration,

        voltage,

        current,

        rpm

    )


    result["success"] = True

    result["temperature"] = temperature

    result["vibration"] = vibration

    result["voltage"] = voltage

    result["current"] = current

    result["rpm"] = rpm


    return jsonify(result)


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_database()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )