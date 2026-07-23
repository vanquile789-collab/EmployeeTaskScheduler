from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "super_secret_key_for_session"

DB_NAME = "new_database.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Tạo bảng Nhân viên có cột msnv (Mã số nhân viên)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        msnv TEXT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        email TEXT UNIQUE,
        password TEXT,
        is_admin INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        task_id INTEGER,
        date TEXT,
        shift TEXT,
        FOREIGN KEY (employee_id) REFERENCES employees (id),
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )
    """)

    # Nạp sẵn dữ liệu mẫu nếu bảng trống
    cur.execute("SELECT COUNT(*) FROM employees")
    if cur.fetchone()[0] == 0:
        sample_employees = [
            ("NV001", "Quản trị viên", "Admin", "admin@gmail.com", "123456", 1),
            ("NV002", "Nguyễn Văn A", "Kỹ thuật", "nguyenvana@gmail.com", "123456", 0),
            ("NV003", "Trần Thị B", "Kinh doanh", "tranthib@gmail.com", "123456", 0)
        ]
        for emp in sample_employees:
            try:
                cur.execute("INSERT INTO employees (msnv, name, role, email, password, is_admin) VALUES (?, ?, ?, ?, ?, ?)", emp)
            except sqlite3.IntegrityError:
                pass

        sample_tasks = [
            ("Kiểm tra thiết bị",),
            ("Sửa chữa máy móc",),
            ("Tư vấn khách hàng",)
        ]
        for task in sample_tasks:
            try:
                cur.executemany("INSERT INTO tasks (title) VALUES (?)", [task])
            except sqlite3.IntegrityError:
                pass

    conn.commit()
    conn.close()

init_db()

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM employees WHERE email = ? AND password = ?", (email, password))
        employee = cur.fetchone()
        conn.close()

        if employee:
            session["employee_id"] = employee["id"]
            session["employee_name"] = employee["name"]
            session["employee_role"] = employee["role"]
            session["is_admin"] = employee["is_admin"]
            return redirect(url_for("home"))
        else:
            error = "Email hoặc mật khẩu không chính xác!"

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def home():
    if "employee_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST" and session.get("is_admin") == 1:
        employee_id = request.form.get("employee_id")
        task_id = request.form.get("task_id")
        date = request.form.get("date")
        shift = request.form.get("shift")
        
        if employee_id and task_id and date and shift:
            cur.execute(
                "INSERT INTO schedules (employee_id, task_id, date, shift) VALUES (?, ?, ?, ?)",
                (employee_id, task_id, date, shift)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("home"))

    today_date = "2025-05-19"

    cur.execute("SELECT COUNT(*) FROM employees")
    total_employees = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM schedules")
    total_schedules = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT employee_id) FROM schedules WHERE date = ?", (today_date,))
    today_working_count = cur.fetchone()[0]

    cur.execute("""
        SELECT DISTINCT e.name, e.role, s.shift, t.title as task_title
        FROM schedules s
        JOIN employees e ON s.employee_id = e.id
        JOIN tasks t ON s.task_id = t.id
        WHERE s.date = ?
    """, (today_date,))
    today_workers = cur.fetchall()

    cur.execute("SELECT * FROM employees")
    employees = cur.fetchall()

    cur.execute("SELECT * FROM tasks")
    tasks = cur.fetchall()

    cur.execute("""
        SELECT s.id, s.employee_id, s.date, s.shift, e.name as employee_name, t.title as task_title 
        FROM schedules s
        JOIN employees e ON s.employee_id = e.id
        JOIN tasks t ON s.task_id = t.id
    """)
    schedules = cur.fetchall()

    conn.close()

    return render_template(
        "index.html",
        total_employees=total_employees,
        total_tasks=total_tasks,
        total_schedules=total_schedules,
        today_working_count=today_working_count,
        today_workers=today_workers,
        employees=employees,
        tasks=tasks,
        schedules=schedules,
        is_admin=session.get("is_admin", 0)
    )

@app.route("/employees", methods=["GET", "POST"])
def manage_employees():
    if session.get("is_admin") != 1:
        return "Bạn không có quyền truy cập trang quản trị này!", 403

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        msnv = request.form.get("msnv")
        name = request.form.get("name")
        role = request.form.get("role")
        email = request.form.get("email")
        password = request.form.get("password")
        is_admin = 1 if request.form.get("is_admin") else 0

        if name and role and email and password:
            try:
                cur.execute("""
                    INSERT INTO employees (msnv, name, role, email, password, is_admin) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (msnv, name, role, email, password, is_admin))
                conn.commit()
            except sqlite3.IntegrityError:
                pass
            conn.close()
            return redirect(url_for("manage_employees"))

    cur.execute("SELECT * FROM employees")
    employees = cur.fetchall()
    conn.close()

    return render_template("employees.html", employees=employees, is_admin=session.get("is_admin", 0))

@app.route("/delete_employee_page/<int:id>")
def delete_employee_page(id):
    if session.get("is_admin") != 1:
        return "Không có quyền thực hiện!", 403

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM schedules WHERE employee_id = ?", (id,))
    cur.execute("DELETE FROM employees WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("manage_employees"))

@app.route("/tasks", methods=["GET", "POST"])
def manage_tasks():
    if "employee_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor()
    if request.method == "POST" and session.get("is_admin") == 1:
        title = request.form.get("title")
        if title:
            cur.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
            conn.commit()
            conn.close()
            return redirect(url_for("manage_tasks"))
    cur.execute("SELECT * FROM tasks")
    tasks = cur.fetchall()
    conn.close()
    return render_template("tasks.html", tasks=tasks, is_admin=session.get("is_admin", 0))

@app.route("/delete_task/<int:id>")
def delete_task(id):
    if session.get("is_admin") != 1:
        return "Không có quyền thực hiện!", 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM schedules WHERE task_id = ?", (id,))
    cur.execute("DELETE FROM tasks WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("manage_tasks"))

@app.route("/schedules")
def manage_schedules():
    if "employee_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id, e.name as employee_name, e.role, t.title as task_title, s.date, s.shift 
        FROM schedules s
        JOIN employees e ON s.employee_id = e.id
        JOIN tasks t ON s.task_id = t.id
        ORDER BY s.date DESC
    """)
    schedules = cur.fetchall()
    conn.close()
    return render_template("schedules.html", schedules=schedules, is_admin=session.get("is_admin", 0))

@app.route("/delete_schedule/<int:id>")
def delete_schedule(id):
    if session.get("is_admin") != 1:
        return "Không có quyền thực hiện!", 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM schedules WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("manage_schedules"))

@app.route("/reports")
def reports():
    if "employee_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM employees")
    total_employees = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM schedules")
    total_schedules = cur.fetchone()[0]
    cur.execute("""
        SELECT s.id, e.name as employee_name, e.role, t.title as task_title, s.date, s.shift 
        FROM schedules s
        JOIN employees e ON s.employee_id = e.id
        JOIN tasks t ON s.task_id = t.id
        ORDER BY s.date DESC
    """)
    report_schedules = cur.fetchall()
    conn.close()
    return render_template("reports.html", total_employees=total_employees, total_tasks=total_tasks, total_schedules=total_schedules, report_schedules=report_schedules, is_admin=session.get("is_admin", 0))

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "employee_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    cur = conn.cursor()
    
    current_user_id = session["employee_id"]
    cur.execute("SELECT * FROM employees WHERE id = ?", (current_user_id,))
    current_user = cur.fetchone()
    
    success_msg = None
    error_msg = None

    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "update_email":
            new_email = request.form.get("new_email")
            if new_email:
                try:
                    cur.execute("UPDATE employees SET email = ? WHERE id = ?", (new_email, current_user_id))
                    conn.commit()
                    success_msg = "Cập nhật email thành công!"
                except sqlite3.IntegrityError:
                    error_msg = "Email này đã được sử dụng bởi tài khoản khác!"
                    
        elif action == "update_password":
            current_password = request.form.get("current_password")
            new_password = request.form.get("new_password")
            
            if current_password == current_user["password"]:
                if new_password:
                    cur.execute("UPDATE employees SET password = ? WHERE id = ?", (new_password, current_user_id))
                    conn.commit()
                    success_msg = "Đổi mật khẩu thành công!"
            else:
                error_msg = "Mật khẩu hiện tại không chính xác!"

    cur.execute("SELECT * FROM employees WHERE id = ?", (current_user_id,))
    current_user = cur.fetchone()
    conn.close()
    
    return render_template("settings.html", current_user=current_user, success_msg=success_msg, error_msg=error_msg, is_admin=session.get("is_admin", 0))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)