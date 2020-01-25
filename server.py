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

    return {
        'works': True
    }

@app.get('/api/vibe')
def bottle_vibe_get():

    return {
        'works': True
    }

@app.post('/api/vibe')
def bottle_vibe_post():

    return {
        'works': True
    }

if (__name__ == '__main__'):
    app.run(host='0.0.0.0', port=8080, catchall=True, debug=True)
