import json
import sqlite3
from random import random

import geopy.distance
import requests
from bottle import Bottle, HTTPError, request, response, run
from bounds import BoundingBox, DividedBounds
from requests.auth import HTTPBasicAuth

spotify_datetime_format = '%Y-%m-%dT%H:%M:%fZ'
acceptable_divisions = set([1, 4, 9, 16, 64])

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
        add_artist(track)
        track_id = add_track(track)
        track_ids.append(track_id)

    for track_id in track_ids:
        add_vibe(location_id, track_id)

    response.status = 201
    return {
        'track_ids': track_ids
    }

@app.get('/api/vibe')
def bottle_get_vibe():

    params = bottle_check_vibe_params(request.query)

    big_box = DividedBounds(params['divisions'], params['lat_min'], params['lat_max'], params['lon_min'], params['lon_max'])

    vibes = []
    for box in big_box.boxes():

        vibe = get_top_vibes(box)

        # Pick just one for now
        if (len(vibe) > 0):
            vibes.append(vibe[0])

    return {
        'vibes': vibes
    }

def bottle_check_vibe_params(query_params):

    params = {}

    params['lat_min'] = request.query.lat_min
    params['lat_max'] = request.query.lat_max
    params['lon_min'] = request.query.lon_min
    params['lon_max'] = request.query.lon_max
    params['divisions'] = request.query.divisions or 9
    params['limit'] = request.query.limit or 15 # TODO: Remove

    if (not params['lat_min']):
        raise HTTPError(400, 'Missing "lat_min"')

    if (not params['lat_max']):
        raise HTTPError(400, 'Missing "lat_max"')

    if (not params['lon_min']):
        raise HTTPError(400, 'Missing "lon_min"')

    if (not params['lon_max']):
        raise HTTPError(400, 'Missing "lon_max"')

    params['lat_min'] = float(params['lat_min'])
    params['lat_max'] = float(params['lat_max'])
    params['lon_min'] = float(params['lon_min'])
    params['lon_max'] = float(params['lon_max'])
    params['divisions'] = float(params['divisions'])

    if (params['lat_max'] < params['lat_min']):
        raise HTTPError(400, 'Invalid latitude range. lat_min is smaller than lat_max')

    if (params['lon_max'] < params['lon_min'] ):
        raise HTTPError(400, 'Invalid longitude range. lon_min is smaller than lon_max')

    if (params['divisions'] not in acceptable_divisions):
        raise HTTPError(400, f'Invalid division number. Must be one of {acceptable_divisions}')

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
        INSERT OR REPLACE INTO track (
            id,
            spotify_id,
            artist_id,
            title,
            album,
            genre,
            original_genre,
            popularity
        ) VALUES (
            (SELECT id FROM track WHERE spotify_id = ?),
            ?,
            (SELECT id FROM artist WHERE spotify_id = ?),
        ?, ?, ?, ?, ?)
    '''

    db.execute(qstring, [
        track_info['track_id'],
        track_info['track_id'],
        track_info['artist_id'],
        track_info['title'],
        track_info['album'],
        track_info['genre'],
        track_info['original_genre'],
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

def get_top_vibes(box):

    qstring = f'''
        SELECT
            location_id,
            latitude,
            longitude,
            genre,
            sum(count) AS genre_total_count,
            avg(popularity) AS genre_avg_popularity,
            t.id AS track_id,
            a.id AS artist_id,
            t.spotify_id AS spotify_track_id,
            a.spotify_id AS spotify_artist_id,
            count AS top_track_count,
            last_vibed,
            title,
            album,
            a.name AS artist,
            popularity AS top_track_popularity
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
            AND genre != 'Other'
        GROUP BY genre
        ORDER BY genre_total_count DESC, genre_avg_popularity DESC
        LIMIT 1
    '''

    cursor = db.execute(qstring, [
        box.lat_min,
        box.lat_max,
        box.lon_min,
        box.lon_max
    ])
    return sqlite_result_to_serializable(cursor.fetchall())

def get_top_track(box):

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
        LIMIT 1
    '''

    cursor = db.execute(qstring, [
        box.lat_min,
        box.lat_max,
        box.lon_min,
        box.lon_max
    ])
    return sqlite_result_to_serializable(cursor.fetchall())

def randomize_locations():

    qstring = '''
        SELECT id, latitude, longitude FROM location
    '''
    cursor = db.execute(qstring)

    for row in cursor:
        lat_rand = (random() - 0.5) * 0.05
        lon_rand = (random() - 0.5) * 0.05

        print(f'Row id: {row["id"]} - {row["latitude"]} + {lat_rand} - {row["longitude"]} + {lon_rand}')

        qstring = '''
            UPDATE location SET
                latitude = latitude + ?,
                longitude = longitude + ?
            WHERE
                id = ?
        '''
        db.execute(qstring, [
            lat_rand,
            lon_rand,
            row['id']
        ])

    db.commit()

def sqlite_result_to_serializable(result):
    return [dict(row) for row in result]

if (__name__ == '__main__'):
    app.run(host='0.0.0.0', port=8080, catchall=True, debug=True)
