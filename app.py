from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import json
import matplotlib.pyplot as plt
import io
import os
import base64
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Admin credentials
admin_user = {'username': 'admin', 'password': 'admin123'}
STUDENTS_FILE = 'students.json'

# -------------------- Helpers --------------------
def load_students():
    try:
        with open(STUDENTS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_students(students):
    with open(STUDENTS_FILE, 'w') as f:
        json.dump(students, f, indent=4)

# -------------------- Routes --------------------
@app.route('/')
def home():
    if 'username' in session:
        if session['username'] == admin_user['username']:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    if username == admin_user['username'] and password == admin_user['password']:
        session['username'] = username
        flash("Welcome Admin!", "success")
        return redirect(url_for('admin_dashboard'))

    students = load_students()
    if username in students and students[username]['password'] == password:
        session['username'] = username
        flash(f"Welcome {username}!", "success")
        return redirect(url_for('dashboard'))

    flash("Invalid username or password", "danger")
    return redirect(url_for('home'))

# ---------------- Student Dashboard ----------------
@app.route('/dashboard')
def dashboard():
    if 'username' not in session or session['username'] == admin_user['username']:
        return redirect(url_for('home'))

    username = session['username']
    students = load_students()
    attendance = students[username]['attendance']
    grades = students[username]['grades']

    # Create grades chart for student
    subjects = list(grades.keys())
    marks = list(grades.values())
    plt.figure(figsize=(6,4))
    plt.bar(subjects, marks, color='skyblue')
    plt.ylim(0,100)
    plt.title(f"{username} Grades")
    plt.ylabel('Marks')
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    chart_data = base64.b64encode(img.getvalue()).decode()
    plt.close()

    return render_template('dashboard.html', username=username, attendance=attendance, grades=grades, chart_data=chart_data)

# ---------------- Admin Dashboard ----------------
@app.route('/admin')
def admin_dashboard():
    if 'username' not in session or session['username'] != admin_user['username']:
        return redirect(url_for('home'))

    students = load_students()
    return render_template('admin.html', students=students)

# ---------------- Add Student ----------------
@app.route('/admin/add', methods=['POST'])
def add_student():
    if 'username' not in session or session['username'] != admin_user['username']:
        return redirect(url_for('home'))

    students = load_students()
    username = request.form['username']
    password = request.form['password']
    attendance = int(request.form['attendance'])
    math = int(request.form['math'])
    science = int(request.form['science'])
    english = int(request.form['english'])

    if username in students:
        flash("Student already exists!", "danger")
    else:
        students[username] = {
            'password': password,
            'attendance': attendance,
            'grades': {'Math': math, 'Science': science, 'English': english}
        }
        save_students(students)
        flash(f"Student {username} added successfully!", "success")
    return redirect(url_for('admin_dashboard'))

# ---------------- Edit Student ----------------
@app.route('/admin/edit/<username>', methods=['GET', 'POST'])
def edit_student(username):
    if 'username' not in session or session['username'] != admin_user['username']:
        return redirect(url_for('home'))

    students = load_students()
    if username not in students:
        flash("Student not found!", "danger")
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        students[username]['attendance'] = int(request.form['attendance'])
        students[username]['grades']['Math'] = int(request.form['math'])
        students[username]['grades']['Science'] = int(request.form['science'])
        students[username]['grades']['English'] = int(request.form['english'])
        save_students(students)
        flash(f"Student {username} updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    student = students[username]
    return render_template('edit_student.html', username=username, student=student)

# ---------------- Delete Student ----------------
@app.route('/admin/delete/<username>')
def delete_student(username):
    if 'username' not in session or session['username'] != admin_user['username']:
        return redirect(url_for('home'))

    students = load_students()
    if username in students:
        del students[username]
        save_students(students)
        flash(f"Student {username} deleted successfully!", "success")
    else:
        flash("Student not found!", "danger")
    return redirect(url_for('admin_dashboard'))

# ---------------- Download PDF with Charts ----------------
@app.route('/admin/download_pdf')
def download_pdf():
    if 'username' not in session or session['username'] != admin_user['username']:
        return redirect(url_for('home'))

    students = load_students()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Student Report", ln=True, align="C")
    pdf.ln(10)

    for username, data in students.items():
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Username: {username}", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, f"Attendance: {data['attendance']}%", ln=True)
        pdf.cell(0, 10, f"Math: {data['grades']['Math']}", ln=True)
        pdf.cell(0, 10, f"Science: {data['grades']['Science']}", ln=True)
        pdf.cell(0, 10, f"English: {data['grades']['English']}", ln=True)
        pdf.ln(5)

        # Create chart for grades
        subjects = list(data['grades'].keys())
        marks = list(data['grades'].values())
        plt.figure(figsize=(4,2.5))
        plt.bar(subjects, marks, color='skyblue')
        plt.ylim(0,100)
        plt.title(f"{username} Grades")
        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='PNG')
        plt.close()
        img_buffer.seek(0)

        # Save temp image to embed in PDF
        img_path = f"{username}_chart.png"
        with open(img_path, "wb") as f:
            f.write(img_buffer.getbuffer())

        pdf.image(img_path, x=10, w=180)
        pdf.ln(10)
        os.remove(img_path)

    pdf_file = "students_report.pdf"
    pdf.output(pdf_file)
    return send_file(pdf_file, as_attachment=True)

# ---------------- Logout ----------------
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Logged out successfully", "info")
    return redirect(url_for('home'))

# ---------------- Run App ----------------
if __name__ == '__main__':
    app.run(debug=True)
