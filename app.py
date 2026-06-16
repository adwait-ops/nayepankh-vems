import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for

current_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(current_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'nayepankh_secret_session_key'

DATABASE_FILE = 'nayepankh.db'

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS volunteers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            assigned_drive TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            campaign_category TEXT NOT NULL,
            event_date TEXT NOT NULL,
            location TEXT NOT NULL,
            volunteers_needed INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Upcoming'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS allocations (
            event_id INTEGER,
            volunteer_id INTEGER,
            PRIMARY KEY (event_id, volunteer_id),
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY (volunteer_id) REFERENCES volunteers(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  
    return conn

def auto_assign_volunteers():
    conn = get_db_connection()
    cursor = conn.cursor()
    events = cursor.execute('SELECT * FROM events').fetchall()
    volunteers = cursor.execute('SELECT * FROM volunteers').fetchall()
    
    for event in events:
        event_id = event['id']
        event_category = event['campaign_category'].lower().replace('_', ' ').replace('drive', '').replace('campaign', '').strip()
        max_capacity = event['volunteers_needed']
        
        current_count = cursor.execute('SELECT COUNT(*) FROM allocations WHERE event_id = ?', (event_id,)).fetchone()[0]
        slots_available = max_capacity - current_count
        
        if slots_available > 0:
            for vol in volunteers:
                vol_id = vol['id']
                vol_track = vol['assigned_drive'].lower().replace('_', ' ').replace('drive', '').replace('campaign', '').strip()
                
                if vol_track == event_category or vol_track in event_category or event_category in vol_track:
                    already_assigned = cursor.execute(
                        'SELECT 1 FROM allocations WHERE event_id = ? AND volunteer_id = ?',
                        (event_id, vol_id)
                    ).fetchone()
                    
                    if not already_assigned and slots_available > 0:
                        cursor.execute('INSERT INTO allocations (event_id, volunteer_id) VALUES (?, ?)', (event_id, vol_id))
                        slots_available -= 1
                        
    conn.commit()
    conn.close()

@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

@app.route('/volunteers', methods=['GET'])
def view_volunteers():
    auto_assign_volunteers()  
    conn = get_db_connection()
    query = '''
        SELECT v.*, GROUP_CONCAT(e.title, ', ') as assigned_events
        FROM volunteers v
        LEFT JOIN allocations a ON v.id = a.volunteer_id
        LEFT JOIN events e ON a.event_id = e.id
        GROUP BY v.id
    '''
    volunteers = conn.execute(query).fetchall()
    conn.close()
    return render_template('volunteers.html', volunteers=volunteers)

@app.route('/add-volunteer', methods=['POST'])
def add_volunteer():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    assigned_drive = request.form.get('assigned_drive')
    
    if name and email and phone and assigned_drive:
        try:
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO volunteers (name, email, phone, assigned_drive)
                VALUES (?, ?, ?, ?)
            ''', (name, email, phone, assigned_drive))
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            pass
            
    return redirect(url_for('view_volunteers'))

@app.route('/remove-volunteer/<int:volunteer_id>', methods=['POST', 'GET'])
def remove_volunteer(volunteer_id):
    conn = get_db_connection()
    # FIX: Purge mapped relationships explicitly before removing the primary record
    conn.execute('DELETE FROM allocations WHERE volunteer_id = ?', (volunteer_id,))
    conn.execute('DELETE FROM volunteers WHERE id = ?', (volunteer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_volunteers'))

@app.route('/events', methods=['GET'])
def view_events():
    auto_assign_volunteers()  
    conn = get_db_connection()
    
    # Extract structural event records and aggregate roster strings
    query_events = '''
        SELECT e.*, 
               COUNT(a.volunteer_id) as total_assigned,
               (e.volunteers_needed - COUNT(a.volunteer_id)) as slots_remaining,
               GROUP_CONCAT(v.name, '||') as volunteer_names
        FROM events e
        LEFT JOIN allocations a ON e.id = a.event_id
        LEFT JOIN volunteers v ON a.volunteer_id = v.id
        GROUP BY e.id
        ORDER BY e.event_date ASC
    '''
    raw_events = conn.execute(query_events).fetchall()
    
    events = []
    for row in raw_events:
        event_dict = dict(row)
        # Parse names list cleanly into a JavaScript/JSON friendly format
        if event_dict['volunteer_names']:
            event_dict['volunteer_list'] = event_dict['volunteer_names'].split('||')
        else:
            event_dict['volunteer_list'] = []
        events.append(event_dict)
    
    query_unassigned = '''
        SELECT * FROM volunteers 
        WHERE id NOT IN (SELECT DISTINCT volunteer_id FROM allocations)
    '''
    unassigned_volunteers = conn.execute(query_unassigned).fetchall()
    
    conn.close()
    return render_template('events.html', events=events, unassigned_volunteers=unassigned_volunteers)

@app.route('/add-event', methods=['POST'])
def add_event():
    title = request.form.get('title')
    category = request.form.get('category')
    event_date = request.form.get('event_date')
    location = request.form.get('location')
    volunteers_needed = request.form.get('volunteers_needed') or 0

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO events (title, campaign_category, event_date, location, volunteers_needed, status)
        VALUES (?, ?, ?, ?, ?, 'Upcoming')
    ''', (title, category, event_date, location, int(volunteers_needed)))
    conn.commit()
    conn.close()
    return redirect('/events')

@app.route('/manual-assign', methods=['POST'])
def manual_assign():
    event_id = request.form.get('event_id')
    volunteer_id = request.form.get('volunteer_id')
    
    if event_id and volunteer_id:
        conn = get_db_connection()
        event = conn.execute('SELECT volunteers_needed FROM events WHERE id = ?', (event_id,)).fetchone()
        current_count = conn.execute('SELECT COUNT(*) FROM allocations WHERE event_id = ?', (event_id,)).fetchone()[0]
        
        if event and current_count < event['volunteers_needed']:
            try:
                conn.execute('INSERT INTO allocations (event_id, volunteer_id) VALUES (?, ?)', (int(event_id), int(volunteer_id)))
                conn.commit()
            except sqlite3.IntegrityError:
                pass
        conn.close()
    return redirect('/events')

@app.route('/remove-event/<int:id>')
def remove_event(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM allocations WHERE event_id = ?', (id,))
    conn.execute('DELETE FROM events WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/events')

if __name__ == '__main__':
    init_db()  
    app.run(debug=True)