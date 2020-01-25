from bottle import Bottle, HTTPError, request, response, run, static_file, view

app = application = Bottle()

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

app.run(host='0.0.0.0', port=8080, catchall=True, debug=True)