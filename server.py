import json
import sqlite3

import geopy.distance
import requests
from bottle import Bottle, HTTPError, request, response, run
from requests.auth import HTTPBasicAuth

spotify_datetime_format = '%Y-%m-%dT%H:%M:%fZ'

app = application = Bottle()

with open('secrets.json') as f:
    secrets = json.load(f)

# Initialize the database
db = sqlite3.connect('db/vibe-check.db')
db.row_factory = sqlite3.Row

with open('db/sqlite-init.sql', mode='r') as f:
    qstring = f.read()

    db.executescript(qstring)
    db.commit()

    print('Initialized SQLite database')

print()

@app.get('/')
def bottle_index():

    return '''
        <h1>Vibe Check API</h1>
        <ul>
            <li>[GET] - /api/vibes?lat_min=X&lat_max=X&lon_min=X&lon_max=X&=X&limit=X</li>
            <li>[POST] - /api/vibes</li>
        </ul>
    '''

@app.get('/auth')
def bottle_spotify_auth_landing():

    error = request.query.error

    if (error):
        print(f'Spotify auth failed: {error}')
        raise HTTPError(403, f'Spotify auth failed: {error}')

    code = request.query.code
    _ = request.query.state

    if (not code):
        raise HTTPError(400, 'Missing "code" parameter')

    return '''
        <h1>Success!</h1>
        <p>Spotify authentication was successful. You can close this window now.</p>
    '''

@app.get('/api/auth')
def bottle_spotify_auth():

    error = request.query.error

    if (error):
        print(f'Spotify auth failed: {error}')
        raise HTTPError(403, f'Spotify auth failed: {error}')

    code = request.query.code
    _ = request.query.state

    if (not code):
        raise HTTPError(400, 'Missing "code" parameter')

    # Contact Spotify to get the access and refresh tokens
    resp = requests.post('https://accounts.spotify.com/api/token',
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'https://vibecheck.tk/auth'
        },
        auth=HTTPBasicAuth(secrets['client_id'], secrets['client_secret'])
    )

    if (resp.status_code != 200):
        raise HTTPError(403, f'Spotify token exchange failed: {resp.status_code} - "{resp.text}"')

    json_resp = json.loads(resp.text)
    return json_resp

@app.post('/api/vibe')
def bottle_vibe_post():

    if (not request.json):
        raise HTTPError(400, 'Body must contain valid JSON')

    if (not 'latitude' in request.json):
        raise HTTPError(400, 'Missing "latitude"')

    if (not 'longitude' in request.json):
        raise HTTPError(400, 'Missing "longitude"')

    if (not 'tracks' in request.json):
        raise HTTPError(400, 'Missing "tracks"')

    location_id = add_location(request.json['latitude'], request.json['longitude'])

    track_ids = []
    for track in request.json['tracks']:
        artist_id = add_artist(track)
        track_id = add_track(track)
        track_ids.append(track_id)

    for track_id in track_ids:
        add_vibe(location_id, track_id)

    response.status = 201

@app.get('/api/vibe')
def bottle_vibe_all():

    params = bottle_check_vibe_params(request.query)
    vibes = get_top_vibes(params)
    genres = get_top_genres(params)

    return {
        'genres': genres,
        'vibes': vibes
    }

@app.get('/api/vibe/track')
def bottle_vibe_get_track():

    params = bottle_check_vibe_params(request.query)
    vibes = get_top_vibes(params)

    return {
        'vibes': vibes
    }

@app.get('/api/vibe/genre')
def bottle_vibe_get_genre():

    params = bottle_check_vibe_params(request.query)
    genres = get_top_genres(params)

    return {
        'genres': genres
    }

def bottle_check_vibe_params(query_params):

    params = {}

    params['lat_min'] = request.query.lat_min
    params['lat_max'] = request.query.lat_max
    params['lon_min'] = request.query.lon_min
    params['lon_max'] = request.query.lon_max
    params['limit'] = request.query.limit or 15

    if (not params['lat_min']):
        raise HTTPError(400, 'Missing "lat_min"')

    if (not params['lat_max']):
        raise HTTPError(400, 'Missing "lat_max"')

    if (not params['lon_min']):
        raise HTTPError(400, 'Missing "lon_min"')

    if (not params['lon_max']):
        raise HTTPError(400, 'Missing "lon_max"')

    lat_min = float(params['lat_min'])
    lat_max = float(params['lat_max'])
    lon_min = float(params['lon_min'])
    lon_max = float(params['lon_max'])

    if (lat_max < lat_min):
        raise HTTPError(400, 'Invalid latitude range. lat_min is smaller than lat_max')

    if (lon_max < lon_min):
        raise HTTPError(400, 'Invalid longitude range. lon_min is smaller than lon_max')

    return params

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

def add_artist(artist_info):

    qstring = '''
        INSERT OR IGNORE INTO artist (
            spotify_id,
            name
        ) VALUES (?, ?)
    '''

    db.execute(qstring, [
        artist_info['artist_id'],
        artist_info['artist']
    ])

    db.commit()

    qstring = '''
        SELECT id FROM artist
        WHERE
            spotify_id = ?
    '''

    cursor = db.execute(qstring, [
        artist_info['artist_id']
    ])

    artist_id = cursor.fetchone()['id']
    return artist_id

def add_track(track_info):

    qstring = '''
        INSERT OR IGNORE INTO track (
            spotify_id,
            artist_id,
            title,
            album,
            genre,
            popularity
        ) VALUES (?,
            (SELECT id FROM artist WHERE spotify_id = ?),
        ?, ?, ?, ?)
    '''

    db.execute(qstring, [
        track_info['track_id'],
        track_info['artist_id'],
        track_info['title'],
        track_info['album'],
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
        track_info['track_id']
    ])

    track_id = cursor.fetchone()['id']
    return track_id

def add_vibe(location_id, track_id):

    qstring = f'''
        INSERT OR IGNORE INTO vibe (
            location_id,
            track_id,
            last_vibed
        ) VALUES (?, ?, strftime('{spotify_datetime_format}', 'now'))
    '''

    db.execute(qstring, [
        location_id,
        track_id
    ])

    db.commit()

    qstring = f'''
        UPDATE vibe SET
            count = count + 1,
            last_vibed = strftime('{spotify_datetime_format}', 'now')
        WHERE
            location_id = ?
            AND track_id = ?
    '''

    db.execute(qstring, [
        location_id,
        track_id
    ])

    db.commit()

def get_top_vibes(params):

    qstring = f'''
        SELECT
            location_id,
            latitude,
            longitude,
            t.id AS track_id,
            a.id AS artist_id,
            t.spotify_id AS spotify_track_id,
            a.spotify_id AS spotify_artist_id,
            count,
            last_vibed,
            title,
            album,
            a.name AS artist,
            genre,
            popularity
        FROM vibe AS v
            LEFT JOIN location AS l ON v.location_id = l.id
            LEFT JOIN track AS t ON v.track_id = t.id
            LEFT JOIN artist AS a ON t.artist_id = a.id
        WHERE
            l.latitude > ?
            AND l.latitude < ?
            AND l.longitude > ?
            AND l.longitude < ?
            AND v.last_vibed > strftime('{spotify_datetime_format}', 'now', '-7 days')
        ORDER BY count DESC, popularity DESC
        LIMIT ?
    '''

    cursor = db.execute(qstring, [
        params['lat_min'],
        params['lat_max'],
        params['lon_min'],
        params['lon_max'],
        params['limit']
    ])
    return sqlite_result_to_serializable(cursor.fetchall())

def get_top_genres(params):

    qstring = f'''
        SELECT DISTINCT
            genre
        FROM vibe AS v
            LEFT JOIN location AS l ON v.location_id = l.id
            LEFT JOIN track AS t ON v.track_id = t.id
            LEFT JOIN artist AS a ON t.artist_id = a.id
        WHERE
            l.latitude > ?
            AND l.latitude < ?
            AND l.longitude > ?
            AND l.longitude < ?
            AND v.last_vibed > strftime('{spotify_datetime_format}', 'now', '-7 days')
        ORDER BY count DESC, popularity DESC
        LIMIT ?
    '''

    cursor = db.execute(qstring, [
        params['lat_min'],
        params['lat_max'],
        params['lon_min'],
        params['lon_max'],
        params['limit']
    ])

    genres = []
    for row in cursor:
        genres.append(row['genre'])

    return genres

def make_bound_box(latitude, longitude, radius):

    latitude = float(latitude)
    longitude = float(longitude)

    # Roughly estimate a bounding box
    degree_change = geopy.units.degrees(arcminutes=geopy.units.nautical(miles=radius / 2))
    # Backwards: geopy.units.miles(nautical=geopy.units.arcminutes(degrees=degree_change))

    print(f'Degree change: {degree_change}')

    min_latitude = latitude - degree_change
    max_latitude = latitude + degree_change
    min_longitude = longitude - degree_change
    max_longitude = longitude + degree_change

    min_point = (min_latitude, min_longitude)
    max_point = (max_latitude, max_longitude)

    hypotenuse_mi = geopy.distance.distance(min_point, max_point).miles

    print()
    print(f'Min lat: {min_latitude}')
    print(f'Max lat: {max_latitude}')
    print(f'Min lon: {min_longitude}')
    print(f'Max lon: {max_longitude}')
    print(f'Request radius (mi): {radius}')
    print(f'Box hypotenuse (mi): {hypotenuse_mi}')
    print()

    return (min_latitude, max_latitude, min_longitude, max_longitude)

def sqlite_result_to_serializable(result):
    return [dict(row) for row in result]

if (__name__ == '__main__'):
    app.run(host='0.0.0.0', port=8080, catchall=True, debug=True)
