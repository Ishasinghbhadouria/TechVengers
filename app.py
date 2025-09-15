from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from datetime import datetime

# ----------------- APP SETUP -----------------
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production

# ----------------- GLOBAL STORAGE -----------------
users = {
    "admin": "admin123",
    "scheduler": "schedule2024"
}
timetable_data = {}
faculty_leaves = {}

# ----------------- DECORATORS -----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------- ROUTES -----------------
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users and users[username] == password:
            session['username'] = username
            flash(f"Welcome {username}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session['username'])

# ----------------- TIMETABLE -----------------
@app.route('/timetable', methods=['GET', 'POST'])
@login_required
def timetable():
    if request.method == 'POST':
        try:
            num_classrooms = int(request.form.get('num_classrooms'))
            num_batches = int(request.form.get('num_batches'))
            num_subjects = int(request.form.get('num_subjects'))
            max_classes_per_day = int(request.form.get('max_classes_per_day'))
            subjects = request.form.getlist('subjects[]')
            classes_per_week = request.form.getlist('classes_per_week[]')
            faculties = request.form.getlist('faculties[]')

            if not (len(subjects) == len(classes_per_week) == len(faculties) == num_subjects):
                flash("Mismatch in subjects and classes/faculties count.", "danger")
                return redirect(url_for('timetable'))

            timetable_data[session['username']] = {
                'num_classrooms': num_classrooms,
                'num_batches': num_batches,
                'num_subjects': num_subjects,
                'max_classes_per_day': max_classes_per_day,
                'subjects': subjects,
                'classes_per_week': list(map(int, classes_per_week)),
                'faculties': faculties
            }

            flash("Timetable data saved. Generating timetable...", "success")
            return redirect(url_for('view_timetable'))
        except Exception as e:
            flash(f"Error processing form: {e}", "danger")
            return redirect(url_for('timetable'))

    return render_template('timetable.html')

@app.route('/view_timetable')
@login_required
def view_timetable():
    data = timetable_data.get(session['username'])
    if not data:
        flash("No timetable data found. Please input timetable details first.", "warning")
        return redirect(url_for('timetable'))

    timetable = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    num_days = len(days)
    max_classes = data['max_classes_per_day']
    classrooms = [f"Room {i+1}" for i in range(data['num_classrooms'])]
    batches = [f"Batch {i+1}" for i in range(data['num_batches'])]

    for day in days:
        timetable[day] = {}
        for room in classrooms:
            timetable[day][room] = [None]*max_classes

    for subj_i, subject in enumerate(data['subjects']):
        classes_needed = data['classes_per_week'][subj_i]
        faculty = data['faculties'][subj_i]
        classes_scheduled = 0
        day_i, room_i, batch_i = 0, 0, 0
        while classes_scheduled < classes_needed:
            day = days[day_i % num_days]
            room = classrooms[room_i % len(classrooms)]
            slot_list = timetable[day][room]
            try:
                slot_index = slot_list.index(None)
            except ValueError:
                room_i += 1
                if room_i >= len(classrooms):
                    room_i = 0
                    day_i += 1
                continue

            batch = batches[batch_i % len(batches)]
            slot_list[slot_index] = (batch, subject, faculty)
            classes_scheduled += 1
            batch_i += 1
            room_i += 1
            if room_i >= len(classrooms):
                room_i = 0
                day_i += 1

    return render_template('view_timetable.html', timetable=timetable, days=days, max_classes=max_classes)

# ----------------- ANALYTICS -----------------
@app.route('/analytics')
@login_required
def analytics():
    data = timetable_data.get(session['username'])
    if not data:
        flash("No timetable data found. Please create a timetable first.", "warning")
        return redirect(url_for('timetable'))

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    max_classes = data['max_classes_per_day']
    classrooms = [f"Room {i+1}" for i in range(data['num_classrooms'])]

    timetable = {}
    for day in days:
        timetable[day] = {}
        for room in classrooms:
            timetable[day][room] = [None]*max_classes

    for subj_i, subject in enumerate(data['subjects']):
        classes_needed = data['classes_per_week'][subj_i]
        faculty = data['faculties'][subj_i]
        classes_scheduled = 0
        day_i, room_i, batch_i = 0, 0, 0
        while classes_scheduled < classes_needed:
            day = days[day_i % len(days)]
            room = classrooms[room_i % len(classrooms)]
            slot_list = timetable[day][room]
            try:
                slot_index = slot_list.index(None)
            except ValueError:
                room_i += 1
                if room_i >= len(classrooms):
                    room_i = 0
                    day_i += 1
                continue
            batch = f"Batch {batch_i+1}"
            slot_list[slot_index] = (batch, subject, faculty)
            classes_scheduled += 1
            batch_i += 1
            room_i += 1
            if room_i >= len(classrooms):
                room_i = 0
                day_i += 1

    faculty_load = {f: 0 for f in data['faculties']}
    classroom_load = {room: 0 for room in classrooms}
    total_slots = len(days) * max_classes

    for day in days:
        for room in classrooms:
            for slot in timetable[day][room]:
                if slot:
                    batch, subject, faculty = slot
                    faculty_load[faculty] += 1
                    classroom_load[room] += 1

    faculties = list(faculty_load.keys())
    actual_load = list(faculty_load.values())
    max_capacity = [max_classes * len(days)] * len(faculties)

    classrooms = list(classroom_load.keys())
    utilization = [
        round((classroom_load[room] / total_slots) * 100, 2) for room in classrooms
    ]

    return render_template(
        "analytics.html",
        faculties=faculties,
        actual_load=actual_load,
        max_capacity=max_capacity,
        classrooms=classrooms,
        utilization=utilization
    )

# ----------------- LEAVE APPLY -----------------
@app.route('/apply_leave', methods=['GET', 'POST'])
@login_required
def apply_leave():
    faculties = []
    if session['username'] in timetable_data:
        faculties = timetable_data[session['username']]['faculties']
    else:
        faculties = ["Prof. Sharma", "Prof. Iyer", "Prof. Khan"]

    if request.method == 'POST':
        faculty = request.form.get('faculty')
        date = request.form.get('date')

        if faculty and date:
            faculty_leaves.setdefault(faculty, []).append(date)
            flash(f"Leave applied for {faculty} on {date}", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Faculty and date required.", "danger")

    return render_template("apply_leave.html",
                           faculties=faculties,
                           faculty_leaves=faculty_leaves)

# ----------------- APPROVALS -----------------
@app.route('/approvals', methods=['GET', 'POST'])
@login_required
def approvals():
    # ✅ Only admin can approve/deny
    if session['username'] != 'admin':
        flash("Access denied. Only admin can approve/deny leaves.", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        faculty = request.form.get('faculty')
        date = request.form.get('date')
        action = request.form.get('action')

        if faculty and date:
            if action == 'approve':
                flash(f"Leave for {faculty} on {date} has been APPROVED ✅", "success")
            elif action == 'deny':
                flash(f"Leave for {faculty} on {date} has been DENIED ❌", "danger")

            if faculty in faculty_leaves and date in faculty_leaves[faculty]:
                faculty_leaves[faculty].remove(date)

    return render_template("approvals.html", faculty_leaves=faculty_leaves)

# ----------------- MAIN -----------------
if __name__ == '__main__':
    app.run(debug=True)
    
