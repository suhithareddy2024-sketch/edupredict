"""
fix_db.py — Run this ONCE to fix students.db
- Adds user_id column so each teacher sees only their own students
- Cleans up trailing spaces in column names
- Existing students get assigned to admin (id=1)

Place next to app.py and run:  python fix_db.py
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.db")
print(f"Using DB: {DB}")

conn = sqlite3.connect(DB)
c = conn.cursor()

cols = [row[1] for row in c.execute("PRAGMA table_info(students)").fetchall()]
print(f"Current columns: {cols}")
row_count = c.execute("SELECT COUNT(*) FROM students").fetchone()[0]
print(f"Existing student rows: {row_count}")

if "user_id" in cols:
    print("user_id already exists — nothing to do")
else:
    existing = c.execute("SELECT rowid, * FROM students").fetchall()
    old_cols = ["rowid"] + cols

    c.executescript("""
        DROP TABLE IF EXISTS students_old;
        ALTER TABLE students RENAME TO students_old;

        CREATE TABLE students (
            user_id               INTEGER NOT NULL DEFAULT 1,
            "Sudent ID"           TEXT,
            "Name"                TEXT,
            "Gender"              TEXT,
            "Age"                 INTEGER,
            "Attendance"          INTEGER,
            "Class"               INTEGER,
            "Homework Completion" REAL,
            "Distance from School" INTEGER,
            "Parent Income Level" INTEGER,
            "Migration Risk"      INTEGER,
            "Student Intrest"     INTEGER,
            "Health Condition"    INTEGER,
            "Previous Year Grade" INTEGER,
            "Fomative Marks"      INTEGER,
            "Sumative Marks"      INTEGER,
            "Behaviour"           INTEGER,
            "Dropout Risk"        INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    col_map = {name.strip(): i for i, name in enumerate(old_cols)}

    def gv(row, name):
        for k, i in col_map.items():
            if k == name or k == name + " " or k == name.rstrip():
                return row[i]
        return None

    for row in existing:
        c.execute("""
            INSERT INTO students
              (user_id,"Sudent ID","Name","Gender","Age","Attendance","Class",
               "Homework Completion","Distance from School","Parent Income Level",
               "Migration Risk","Student Intrest","Health Condition",
               "Previous Year Grade","Fomative Marks","Sumative Marks",
               "Behaviour","Dropout Risk")
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            1, gv(row,"Sudent ID"), gv(row,"Name"), gv(row,"Gender"),
            gv(row,"Age"), gv(row,"Attendance"),
            gv(row,"Class") or gv(row,"Class "),
            gv(row,"Homework Completion"),
            gv(row,"Distance from School"), gv(row,"Parent Income Level"),
            gv(row,"Migration Risk"), gv(row,"Student Intrest"),
            gv(row,"Health Condition"), gv(row,"Previous Year Grade"),
            gv(row,"Fomative Marks") or gv(row,"Fomative Marks "),
            gv(row,"Sumative Marks")  or gv(row,"Sumative Marks "),
            gv(row,"Behaviour")       or gv(row,"Behaviour "),
            gv(row,"Dropout Risk")    or gv(row,"Dropout Risk "),
        ))

    c.execute("DROP TABLE IF EXISTS students_old")
    conn.commit()
    print(f"Migrated {len(existing)} rows")

new_cols = [row[1] for row in c.execute("PRAGMA table_info(students)").fetchall()]
count = c.execute("SELECT COUNT(*) FROM students").fetchone()[0]
print(f"\nNew columns: {new_cols}")
print(f"Student rows: {count}")
conn.close()
print("\n✅ Done! Now restart Flask: python app.py")