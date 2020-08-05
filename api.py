import flask

app = flask.Flask(__name__)
app.config["DEBUG"] = True

parts_inventory = { 0: 0 }
parts_list = { 
    0: { 
        'type': 'other', 
        'name': 'Initial Part',
        'active': True,
        'created_at': 0
    }
}

@app.route('/', methods=['GET'])
def home():
    return "<h1>JMKRIDE Stock Tracking REST API</h1>"

@app.route('/api/v1/resources/inventory/all', methods=['GET'])
def api_all_inventory():
    return flask.jsonify(parts_inventory)

@app.route('/api/v1/resources/parts/all', methods=['GET'])
def api_all_parts():
    return flask.jsonify(parts_list)


app.run()
