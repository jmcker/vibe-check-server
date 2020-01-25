import sqlite3

from bottle import Bottle, HTTPError, request, response, run, static_file, view

app = application = Bottle()

# Initialize the database
db = sqlite3.connect('db/vibe-check.db')
db.row_factory = sqlite3.Row

with open('db/sqlite-init.sql', mode='r') as f:
    qstring = f.read()

    db.executescript(qstring)
    db.commit()


@app.get('/')
def bottle_index():

    return '''
        <h1>Vibe Check API</h1>
        <ul>
            <li>[GET] - /api/vibes?lat=X&lon=X&radius=X&limit=X</li>
            <li>[POST] - /api/vibes</li>
        </ul>
    '''

@app.get('/api/vibe')
def bottle_vibe_get():

    latitude = request.query.lat
    longitute = request.query.lon
    radius = request.query.radius or 10     # miles
    limit = request.query.limit or 15

    if (not latitude):
        raise HTTPError(400, 'Missing "latitude"')

    if (not longitute):
        raise HTTPError(400, 'Missing "longitude"')

    vibes = get_top_vibes(latitude, longitute, radius, limit)

    return {
        'count': len(vibes),
        'vibes': vibes
    }

@app.post('/api/vibe')
def bottle_vibe_post():

    location_id = add_location(request.json['latitude'], request.json['longitude'])

    track_ids = []
    for track in request.json['tracks']:
        db_id = add_track(track)
        track_ids.append(db_id)

    for track_id in track_ids:
        add_vibe(location_id, track_id)

    response.status = 201

def add_location(latitude, longitude):

    qstring = '''
        INSERT OR IGNORE INTO location (
            latitude,
            longitude
        ) VALUES (?, ?)
    '''

    db.execute(qstring, [
        latitude,
        longitude
    ])

    db.commit()

    # Get the id of what we just inserted
    qstring = '''
        SELECT id FROM location
        WHERE
            latitude = ?
            AND longitude = ?
    '''
    cursor = db.execute(qstring, [
        latitude,
        longitude
    ])

    location_id = cursor.fetchone()['id']
    return location_id

def add_track(track_info):

    qstring = '''
        INSERT OR IGNORE INTO track (
            spotify_id,
            title,
            artist,
            genre,
            popularity
        ) VALUES (?, ?, ?, ?, ?)
    '''

    db.execute(qstring, [
        track_info['spotify_id'],
        track_info['title'],
        track_info['artist'],
        track_info['genre'],
        track_info['popularity']
    ])

    db.commit()

    # Get the id of what we just inserted
    qstring = '''
        SELECT id FROM track
        WHERE
            spotify_id = ?
    '''

    cursor = db.execute(qstring, [
        track_info['spotify_id']
    ])

    track_id = cursor.fetchone()['id']
    return track_id

def add_vibe(location_id, track_id):

    qstring = '''
        INSERT OR IGNORE INTO vibe (
            location_id,
            track_id
        ) VALUES (?, ?)
    '''

    db.execute(qstring, [
        location_id,
        track_id
    ])

    db.commit()

    qstring = '''
        UPDATE vibe SET
            count = count + 1
        WHERE
            location_id = ?
            AND track_id = ?
    '''

    db.execute(qstring, [
        location_id,
        track_id
    ])

    db.commit()

def get_top_vibes(latitude, longitude, radius = 15, limit = 10):

    qstring = '''
        SELECT * FROM vibe AS v
            LEFT JOIN location AS l ON v.location_id = l.id
            LEFT JOIN track AS t ON v.track_id = t.id
        WHERE
            l.latitude = ?
            AND l.longitude = ?
        ORDER BY count DESC, popularity DESC
        LIMIT ?
    '''

    # TODO: Create bounding box with latitude and longitude

    cursor = db.execute(qstring, [latitude, longitude, limit])
    return sqlite_result_to_serializable(cursor.fetchall())

def sqlite_result_to_serializable(result):
    return [dict(row) for row in result]

if (__name__ == '__main__'):
    app.run(host='0.0.0.0', port=8080, catchall=True, debug=True)
