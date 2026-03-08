"""
EduPredict — Student Dropout Early Warning System
Database: students.db
Run:  python app.py
Open: http://127.0.0.1:5000
"""

from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, send_file)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, io, csv, json
from functools import wraps

# App setup
app = Flask(__name__)
app.secret_key = "edupredict_secret_2024"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB = os.path.join(BASE_DIR, "students.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            firstname TEXT NOT NULL,
            lastname  TEXT NOT NULL,
            email     TEXT NOT NULL,
            username  TEXT NOT NULL UNIQUE,
            password  TEXT NOT NULL,
            role      TEXT NOT NULL DEFAULT 'teacher'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            user_id                INTEGER NOT NULL DEFAULT 1,
            "Sudent ID"            TEXT,
            "Name"                 TEXT,
            "Gender"               TEXT,
            "Age"                  INTEGER,
            "Attendance"           INTEGER,
            "Class"                INTEGER,
            "Homework Completion"  REAL,
            "Distance from School" INTEGER,
            "Parent Income Level"  INTEGER,
            "Migration Risk"       INTEGER,
            "Student Intrest"      INTEGER,
            "Health Condition"     INTEGER,
            "Previous Year Grade"  INTEGER,
            "Fomative Marks"       INTEGER,
            "Sumative Marks"       INTEGER,
            "Behaviour"            INTEGER,
            "Dropout Risk"         INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        c.execute(
            "INSERT INTO users (firstname,lastname,email,username,password,role) VALUES (?,?,?,?,?,?)",
            ("Admin","User","admin@edupredict.com","admin",generate_password_hash("admin123"),"admin")
        )
        conn.commit()
        print("[INIT] Default admin created → username: admin  password: admin123")
    print(f"[DB] {DB}")
    conn.close()

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def current_user():
    if "user_id" not in session:
        return None
    try:
        conn = get_db()
        u = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        conn.close()
        if u:
            return dict(u)
    except Exception:
        pass
    session.clear()
    return None

def safe_current_user():
    u = current_user()
    if u:
        return u
    session.clear()
    return {"id":0,"firstname":"Guest","lastname":"","email":"","username":"guest","role":"guest"}

def map_student(r, student_id=None):
    raw = dict(r)
    def g(key, alt=None):
        v = raw.get(key)
        if v is None and alt:
            v = raw.get(alt)
        return v or 0
    dr = g("Dropout Risk", "Dropout Risk ")
    try: dr = float(dr)
    except: dr = 0
    if dr >= 60:   level = "CRITICAL"
    elif dr >= 40: level = "HIGH"
    elif dr >= 20: level = "MODERATE"
    else:          level = "SAFE"
    return {
        "id": student_id or raw.get("rowid",""),
        "user_id": raw.get("user_id",1),
        "name": raw.get("Name","") or "",
        "age": raw.get("Age",""),
        "gender": raw.get("Gender",""),
        "class_level": g("Class","Class "),
        "attendance": g("Attendance"),
        "prev_grade": g("Previous Year Grade"),
        "formative_marks": g("Fomative Marks","Fomative Marks "),
        "summative_marks": g("Sumative Marks","Sumative Marks "),
        "homework_completion": g("Homework Completion"),
        "distance_km": g("Distance from School"),
        "parent_income": g("Parent Income Level"),
        "migration_risk": g("Migration Risk"),
        "student_interest": g("Student Intrest"),
        "health_condition": g("Health Condition"),
        "behaviour": g("Behaviour","Behaviour "),
        "risk_score": dr,
        "risk_level": level,
        "interventions": [],
        "created_at": raw.get("created_at",""),
    }

def get_stats(user_id=None):
    conn = get_db()
    if user_id:
        rows = conn.execute("SELECT rowid, * FROM students WHERE user_id=?", (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT rowid, * FROM students").fetchall()
    conn.close()
    students = [map_student(r, r["rowid"]) for r in rows]
    stats = {
        "total": len(students),
        "CRITICAL": sum(1 for s in students if s["risk_level"]=="CRITICAL"),
        "HIGH": sum(1 for s in students if s["risk_level"]=="HIGH"),
        "MODERATE": sum(1 for s in students if s["risk_level"]=="MODERATE"),
        "SAFE": sum(1 for s in students if s["risk_level"]=="SAFE"),
    }
    return stats, students

def predict_risk(d):
    score = 0.0
    att = float(d.get("attendance", 75))
    if att < 50: score += 25
    elif att < 60: score += 20
    elif att < 75: score += 12
    elif att < 85: score += 5
    grade = float(d.get("prev_grade", 50))
    if grade < 35: score += 20
    elif grade < 50: score += 14
    elif grade < 65: score += 7
    elif grade < 75: score += 3
    form = float(d.get("formative_marks", 50))
    if form < 30: score += 10
    elif form < 50: score += 6
    elif form < 65: score += 3
    summ = float(d.get("summative_marks", 50))
    if summ < 30: score += 10
    elif summ < 50: score += 6
    elif summ < 65: score += 3
    hw = float(d.get("homework_completion", 50))
    if hw < 30: score += 8
    elif hw < 60: score += 4
    dist = float(d.get("distance_km", 5))
    if dist > 15: score += 5
    elif dist > 8: score += 2
    inc = float(d.get("parent_income", 50))
    if inc < 20: score += 8
    elif inc < 40: score += 4
    mig = float(d.get("migration_risk", 0))
    if mig > 70: score += 5
    elif mig > 40: score += 2
    interest = float(d.get("student_interest", 50))
    if interest < 25: score += 5
    elif interest < 50: score += 2
    health = float(d.get("health_condition", 50))
    if health < 30: score += 2
    behav = float(d.get("behaviour", 50))
    if behav < 30: score += 2
    risk_score = min(round(score,1), 100)
    if risk_score >= 60: level = "CRITICAL"
    elif risk_score >= 40: level = "HIGH"
    elif risk_score >= 20: level = "MODERATE"
    else: level = "SAFE"
    return risk_score, level, get_interventions(level, att, grade, dist, inc, mig)

def get_interventions(level, att, grade, dist, inc, mig):
    tips = []
    if att < 60: tips.append("🏠 Conduct urgent home visit — attendance critically low")
    elif att < 75: tips.append("📞 Call parents regarding irregular attendance")
    if grade < 40: tips.append("📚 Enroll in remedial classes immediately")
    elif grade < 55: tips.append("📖 Assign peer tutoring support")
    if dist > 10: tips.append("🚌 Arrange school bus or transportation support")
    if inc < 25: tips.append("💰 Apply for government scholarship / mid-day meal scheme")
    if mig > 50: tips.append("📝 Register with seasonal migration tracking program")
    if level == "CRITICAL":
        tips.append("🚨 Immediate counsellor referral required")
        tips.append("👨‍👩‍👧 Schedule emergency parent-teacher conference")
    elif level == "HIGH":
        tips.append("📋 Weekly progress monitoring by class teacher")
        tips.append("🧠 Psycho-social support assessment recommended")
    elif level == "MODERATE":
        tips.append("📊 Monthly check-in with guidance counsellor")
    else:
        tips.append("✅ Continue current support — student on track")
    return tips[:5]

# ROUTES

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login():
    session.clear()
    error = None
    if request.method == "POST":
        identifier = request.form.get("username","").strip()
        password   = request.form.get("password","")
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE LOWER(username)=LOWER(?) OR LOWER(email)=LOWER(?)",
            (identifier, identifier)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            session["role"]     = user["role"]
            print(f"[LOGIN OK] {user['username']} id={user['id']}")
            return redirect(url_for("dashboard"))
        error = "Invalid username/email or password."
    return render_template("login.html", error=error)

@app.route("/signup",   methods=["GET","POST"])
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "GET":
        session.clear()
    error = None
    if request.method == "POST":
        fn    = request.form.get("firstname","").strip()
        ln    = request.form.get("lastname","").strip()
        email = request.form.get("email","").strip()
        uname = request.form.get("username","").strip()
        pw    = request.form.get("password","")
        role  = request.form.get("role","teacher").strip()
        if role not in ("admin","teacher"):
            role = "teacher"
        if   not fn:      error = "First name is required."
        elif not ln:      error = "Last name is required."
        elif not email:   error = "Email is required."
        elif not uname:   error = "Username is required."
        elif not pw:      error = "Password is required."
        elif len(pw) < 6: error = "Password must be at least 6 characters."
        else:
            try:
                conn = sqlite3.connect(DB)
                conn.row_factory = sqlite3.Row
                conn.execute(
                    "INSERT INTO users (firstname,lastname,email,username,password,role) VALUES (?,?,?,?,?,?)",
                    (fn, ln, email, uname, generate_password_hash(pw), role)
                )
                conn.commit()
                total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                conn.close()
                print(f"[REGISTER OK] '{uname}' saved. Total users: {total}")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError as e:
                err = str(e).lower()
                error = "Username already taken." if "username" in err else "Email already registered. Try logging in."
            except Exception as e:
                error = f"Error: {e}"
    return render_template("register.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = safe_current_user()
    stats, students = get_stats(session.get("user_id"))
    return render_template("dashboard.html", user=user, students=students, stats=stats)

@app.route("/predict")
@login_required
def predict():
    return render_template("predict.html", user=safe_current_user())

@app.route("/result")
@login_required
def result():
    user = safe_current_user()
    student_id = session.get("last_prediction_id")
    if not student_id:
        return redirect(url_for("predict"))
    conn = get_db()
    row = conn.execute(
        "SELECT rowid, * FROM students WHERE rowid=? AND user_id=?",
        (student_id, session["user_id"])
    ).fetchone()
    conn.close()
    if not row:
        return redirect(url_for("predict"))
    s = map_student(row, student_id)
    s["interventions"] = session.get("last_interventions", [])
    return render_template("result.html", user=user, student=s)

@app.route("/students")
@login_required
def students():
    user = safe_current_user()
    stats, all_students = get_stats(session.get("user_id"))
    return render_template("students.html", user=user, students=all_students, stats=stats)

@app.route("/students/delete/<int:sid>", methods=["POST"])
@login_required
def delete_student(sid):
    conn = get_db()
    conn.execute("DELETE FROM students WHERE rowid=? AND user_id=?", (sid, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("students"))

@app.route("/alerts")
@login_required
def alerts():
    user = safe_current_user()
    stats, all_students = get_stats(session.get("user_id"))
    alert_list = sorted(
        [s for s in all_students if s["risk_level"] in ("CRITICAL","HIGH")],
        key=lambda x: x["risk_score"], reverse=True
    )
    return render_template("alerts.html", user=user, alerts=alert_list)

@app.route("/analytics")
@login_required
def analytics():
    user = safe_current_user()
    stats, all_students = get_stats(session.get("user_id"))
    return render_template("analytics.html", user=user, students=all_students, stats=stats)

@app.route("/reports")
@login_required
def reports():
    user = safe_current_user()
    stats, all_students = get_stats(session.get("user_id"))
    return render_template("reports.html", user=user, students=all_students, stats=stats)

@app.route("/settings")
@login_required
def settings():
    user = safe_current_user()
    return render_template("settings.html", user=user, user_data=user)

@app.route("/settings/update", methods=["POST"])
@login_required
def settings_update():
    fn  = request.form.get("firstname","").strip()
    ln  = request.form.get("lastname","").strip()
    em  = request.form.get("email","").strip()
    pw  = request.form.get("new_password","").strip()
    uid = session["user_id"]
    try:
        conn = get_db()
        if pw:
            if len(pw) < 6:
                return redirect(url_for("settings") + "?error=Password+must+be+6%2B+characters")
            conn.execute("UPDATE users SET firstname=?,lastname=?,email=?,password=? WHERE id=?",
                         (fn, ln, em, generate_password_hash(pw), uid))
        else:
            conn.execute("UPDATE users SET firstname=?,lastname=?,email=? WHERE id=?",
                         (fn, ln, em, uid))
        conn.commit()
        conn.close()
        return redirect(url_for("settings") + "?success=Profile+updated+successfully")
    except sqlite3.IntegrityError:
        return redirect(url_for("settings") + "?error=Email+already+in+use")

# JSON API

@app.route("/api/predict", methods=["POST"])
@login_required
def api_predict():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"success": False, "error": "No data received"}), 400
    name = data.get("name","").strip()
    if not name:
        return jsonify({"success": False, "error": "Student name required"}), 400
    try:
        risk_score, risk_level, interventions = predict_risk(data)
        conn = get_db()
        cols = [row[1] for row in conn.execute("PRAGMA table_info(students)").fetchall()]
        class_col = "Class " if "Class " in cols else "Class"
        frm_col   = "Fomative Marks " if "Fomative Marks " in cols else "Fomative Marks"
        sum_col   = "Sumative Marks "  if "Sumative Marks " in cols else "Sumative Marks"
        beh_col   = "Behaviour "       if "Behaviour " in cols else "Behaviour"
        drp_col   = "Dropout Risk "    if "Dropout Risk " in cols else "Dropout Risk"
        sql = f"""INSERT INTO students
            (user_id,"Name","Gender","Age","Attendance","{class_col}",
             "Homework Completion","Distance from School","Parent Income Level",
             "Migration Risk","Student Intrest","Health Condition",
             "Previous Year Grade","{frm_col}","{sum_col}","{beh_col}","{drp_col}")
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        cur = conn.execute(sql, (
            session["user_id"], name,
            data.get("gender"), data.get("age"), data.get("attendance"),
            data.get("class_level"), data.get("homework_completion"),
            data.get("distance_km"), data.get("parent_income"),
            data.get("migration_risk"), data.get("student_interest"),
            data.get("health_condition"), data.get("prev_grade"),
            data.get("formative_marks"), data.get("summative_marks"),
            data.get("behaviour"), risk_score
        ))
        session["last_prediction_id"] = cur.lastrowid
        session["last_interventions"] = interventions
        conn.commit()
        conn.close()
        print(f"[PREDICT] user={session['user_id']} '{name}' -> {risk_level} ({risk_score}%)")
        return jsonify({"success":True,"student_name":name,"risk_score":risk_score,
                        "risk_level":risk_level,"interventions":interventions,"result_url":"/result"})
    except Exception as e:
        print(f"[PREDICT ERROR] {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/students")
@login_required
def api_students():
    stats, students = get_stats(session.get("user_id"))
    return jsonify({"students": students})

@app.route("/api/bulk-upload", methods=["POST"])
@login_required
def bulk_upload():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
    f = request.files["file"]
    if not f.filename.endswith(".csv"):
        return jsonify({"success": False, "error": "Only CSV files accepted"}), 400
    stream = io.StringIO(f.stream.read().decode("utf-8"))
    reader = csv.DictReader(stream)
    inserted = 0
    errors = []
    conn = get_db()
    cols = [row[1] for row in conn.execute("PRAGMA table_info(students)").fetchall()]
    class_col = "Class " if "Class " in cols else "Class"
    frm_col   = "Fomative Marks " if "Fomative Marks " in cols else "Fomative Marks"
    sum_col   = "Sumative Marks "  if "Sumative Marks " in cols else "Sumative Marks"
    beh_col   = "Behaviour "       if "Behaviour " in cols else "Behaviour"
    drp_col   = "Dropout Risk "    if "Dropout Risk " in cols else "Dropout Risk"
    for i, row in enumerate(reader, 1):
        try:
            name = (row.get("name") or row.get("Name") or "").strip()
            if not name:
                errors.append(f"Row {i}: missing name")
                continue
            d = {
                "attendance": float(row.get("attendance",75)),
                "prev_grade": float(row.get("prev_grade",50)),
                "formative_marks": float(row.get("formative_marks",50)),
                "summative_marks": float(row.get("summative_marks",50)),
                "homework_completion": float(row.get("homework_completion",50)),
                "distance_km": float(row.get("distance_km",5)),
                "parent_income": float(row.get("parent_income",50)),
                "migration_risk": float(row.get("migration_risk",0)),
                "student_interest": float(row.get("student_interest",50)),
                "health_condition": float(row.get("health_condition",50)),
                "behaviour": float(row.get("behaviour",50)),
            }
            risk_score, risk_level, interventions = predict_risk(d)
            sql = f"""INSERT INTO students
                (user_id,"Name","Gender","Age","Attendance","{class_col}",
                 "Homework Completion","Distance from School","Parent Income Level",
                 "Migration Risk","Student Intrest","Health Condition",
                 "Previous Year Grade","{frm_col}","{sum_col}","{beh_col}","{drp_col}")
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
            conn.execute(sql, (
                session["user_id"], name,
                row.get("gender") or row.get("Gender"),
                row.get("age") or row.get("Age"),
                d["attendance"], row.get("class_level"),
                d["homework_completion"], d["distance_km"], d["parent_income"],
                d["migration_risk"], d["student_interest"], d["health_condition"],
                d["prev_grade"], d["formative_marks"], d["summative_marks"],
                d["behaviour"], risk_score
            ))
            inserted += 1
        except Exception as e:
            errors.append(f"Row {i}: {e}")
    conn.commit()
    conn.close()
    return jsonify({"success": True, "inserted": inserted, "errors": errors})

@app.route("/api/sample-csv")
@login_required
def sample_csv():
    headers = ["name","age","gender","class_level","attendance","prev_grade",
               "formative_marks","summative_marks","homework_completion",
               "distance_km","parent_income","migration_risk","student_interest",
               "health_condition","behaviour"]
    sample_rows = [
        ["Ravi Kumar","12","Male","7","55","40","45","38","20","8","15","50","20","55","55"],
        ["Priya Singh","11","Female","6","80","72","70","68","90","3","50","5","90","90","90"],
        ["Mohammed Rafi","13","Male","8","45","30","35","28","20","15","10","85","20","20","20"],
    ]
    output = io.StringIO()
    csv.writer(output).writerow(headers)
    csv.writer(output).writerows(sample_rows)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv",
                     as_attachment=True, download_name="edupredict_sample.csv")

@app.route("/debug-db")
def debug_db():
    try:
        conn = get_db()
        users   = [dict(u) for u in conn.execute("SELECT id,firstname,username,role FROM users").fetchall()]
        s_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        s_cols  = [row[1] for row in conn.execute("PRAGMA table_info(students)").fetchall()]
        conn.close()
        return jsonify({"status":"OK","db":DB,"users":users,"student_count":s_count,"student_columns":s_cols})
    except Exception as e:
        return jsonify({"status":"ERROR","error":str(e)})

# Init and run
init_db()

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  EduPredict → http://127.0.0.1:5000")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)