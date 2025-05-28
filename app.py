from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import bcrypt
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# MySQL configuration (update with your XAMPP setup)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'event_management'

mysql = MySQL(app)

# Helper functions
def get_user_by_username(username):
    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id, username, password_hash, role FROM EM_Users WHERE username=%s", (username,))
    return cur.fetchone()

def get_events_by_organizer(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM EM_Events WHERE organizer_id=%s", (user_id,))
    return cur.fetchall()

def get_all_events():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT e.event_id, e.event_name, e.description, e.start_time, e.end_time, v.venue_name, e.category 
        FROM EM_Events e JOIN EM_Venues v ON e.venue_id = v.venue_id
        ORDER BY e.start_time
    """)
    return cur.fetchall()

def get_event(event_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT 
            e.event_id, 
            e.event_name, 
            e.description, 
            e.start_time, 
            e.end_time, 
            v.venue_name, 
            v.location, 
            e.category 
        FROM EM_Events e 
        JOIN EM_Venues v ON e.venue_id = v.venue_id
        WHERE e.event_id=%s
    """, (event_id,))
    return cur.fetchone()

def is_registered(event_id, user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT 1 FROM EM_EventRegistrations WHERE event_id=%s AND attendee_id=%s", (event_id, user_id))
    return cur.fetchone() is not None

# Routes

@app.route('/')
def home():
    if 'user_id' in session:
        if session['role'] == 'Organizer':
            return redirect(url_for('organizer_dashboard'))
        else:
            return redirect(url_for('attendee_dashboard'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        role = request.form['role']

        # Check if user exists
        if get_user_by_username(username):
            flash('Username already exists')
            return redirect(url_for('register'))

        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO EM_Users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
                    (username, pw_hash, email, role))
        mysql.connection.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        user = get_user_by_username(username)
        if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            flash('Logged in successfully')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out')
    return redirect(url_for('home'))

# Organizer dashboard
@app.route('/organizer')
def organizer_dashboard():
    if 'user_id' not in session or session['role'] != 'Organizer':
        flash('Access denied')
        return redirect(url_for('login'))

    events = get_events_by_organizer(session['user_id'])
    return render_template('organizer_dashboard.html', events=events)

@app.route('/organizer/create_event', methods=['GET', 'POST'])
def create_event():
    if 'user_id' not in session or session['role'] != 'Organizer':
        flash('Access denied')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM EM_Venues")
    venues = cur.fetchall()

    if request.method == 'POST':
        event_name = request.form['event_name']
        description = request.form['description']
        start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')  # Parse the datetime
        end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')    # Parse the datetime
        venue_id = request.form['venue_id']
        category = request.form['category']

        # Format for database storage
        start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')

        cur.execute("""
            INSERT INTO EM_Events (event_name, description, start_time, end_time, venue_id, organizer_id, category)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (event_name, description, start_time_str, end_time_str, venue_id, session['user_id'], category))
        mysql.connection.commit()
        flash('Event created successfully')
        return redirect(url_for('organizer_dashboard'))

    return render_template('create_event.html', venues=venues)


# Add this route in app.py after the create_event route
@app.route('/organizer/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if 'user_id' not in session or session['role'] != 'Organizer':
        flash('Access denied')
        return redirect(url_for('login'))

    # First check if the event belongs to the current organizer
    cur = mysql.connection.cursor()
    cur.execute("SELECT organizer_id FROM EM_Events WHERE event_id=%s", (event_id,))
    event = cur.fetchone()

    if not event:
        flash('Event not found')
        return redirect(url_for('organizer_dashboard'))

    if event[0] != session['user_id']:
        flash('You can only delete your own events')
        return redirect(url_for('organizer_dashboard'))

    try:
        # First delete related records to maintain referential integrity
        cur.execute("DELETE FROM EM_EventRegistrations WHERE event_id=%s", (event_id,))
        cur.execute("DELETE FROM EM_Feedbacks WHERE event_id=%s", (event_id,))
        # Then delete the event
        cur.execute("DELETE FROM EM_Events WHERE event_id=%s", (event_id,))
        mysql.connection.commit()
        flash('Event deleted successfully')
    except Exception as e:
        mysql.connection.rollback()
        flash('Error deleting event')

    return redirect(url_for('organizer_dashboard'))

# Attendee dashboard
@app.route('/attendee')
def attendee_dashboard():
    if 'user_id' not in session or session['role'] != 'Attendee':
        flash('Access denied')
        return redirect(url_for('login'))

    events = get_all_events()
    return render_template('attendee_dashboard.html', events=events)

@app.route('/event/<int:event_id>', methods=['GET', 'POST'])
def event_detail(event_id):
    event = get_event(event_id)
    if not event:
        flash('Event not found')
        return redirect(url_for('home'))

    registered = False
    if 'user_id' in session and session['role'] == 'Attendee':
        registered = is_registered(event_id, session['user_id'])

    if request.method == 'POST':
        if 'user_id' not in session or session['role'] != 'Attendee':
            flash('Login as attendee to register')
            return redirect(url_for('login'))
        if not registered:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO EM_EventRegistrations (event_id, attendee_id) VALUES (%s, %s)",
                        (event_id, session['user_id']))
            mysql.connection.commit()
            flash('Successfully registered for event')
            return redirect(url_for('event_detail', event_id=event_id))
        else:
            flash('Already registered')
            return redirect(url_for('event_detail', event_id=event_id))

    return render_template('event_detail.html', event=event, registered=registered)

if __name__ == '__main__':
    app.run(debug=True)
