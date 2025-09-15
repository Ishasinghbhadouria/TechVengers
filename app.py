from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a random secret key in production

# Dummy user store (username: password)
users = {
    'admin': 'admin123',
    'scheduler': 'schedule2024'
}

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# In-memory storage for timetable data (for demo purposes)
timetable_data = {}

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

@app.route('/timetable', methods=['GET', 'POST'])
@login_required
def timetable():
    if request.method == 'POST':
        # Extract form data
        try:
            num_classrooms = int(request.form.get('num_classrooms'))
            num_batches = int(request.form.get('num_batches'))
            num_subjects = int(request.form.get('num_subjects'))
            max_classes_per_day = int(request.form.get('max_classes_per_day'))
            subjects = request.form.getlist('subjects[]')
            classes_per_week = request.form.getlist('classes_per_week[]')
            faculties = request.form.getlist('faculties[]')
            # Basic validation
            if not (len(subjects) == len(classes_per_week) == len(faculties) == num_subjects):
                flash("Mismatch in subjects and classes/faculties count.", "danger")
                return redirect(url_for('timetable'))

            # Store data in session or global dict for demo
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

    # Simplified timetable generation logic:
    # Assign subjects to batches and classrooms in a round-robin fashion
    timetable = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    num_days = len(days)
    max_classes = data['max_classes_per_day']
    classrooms = [f"Room {i+1}" for i in range(data['num_classrooms'])]
    batches = [f"Batch {i+1}" for i in range(data['num_batches'])]

    # Initialize timetable dict: timetable[day][classroom][slot] = (batch, subject, faculty)
    for day in days:
        timetable[day] = {}
        for room in classrooms:
            timetable[day][room] = [None]*max_classes

    # Simple scheduling algorithm (not optimized):
    # For each subject, schedule required classes per week across days, classrooms, batches
    subject_index = 0
    for subj_i, subject in enumerate(data['subjects']):
        classes_needed = data['classes_per_week'][subj_i]
        faculty = data['faculties'][subj_i]
        classes_scheduled = 0
        day_i = 0
        room_i = 0
        batch_i = 0
        while classes_scheduled < classes_needed:
            day = days[day_i % num_days]
            room = classrooms[room_i % len(classrooms)]
            slot_list = timetable[day][room]
            # Find first empty slot
            try:
                slot_index = slot_list.index(None)
            except ValueError:
                # No slot available in this room/day, move to next room/day
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

if __name__ == '__main__':
    app.run(debug=True)
