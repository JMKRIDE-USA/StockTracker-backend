from IPython import embed
import flask
import json
import os
from flask_cors import CORS, cross_origin
import flask_uploads
import time
from functools import wraps
from werkzeug.utils import secure_filename

import db


app = flask.Flask(__name__)
CORS(app)
app.config["DEBUG"] = True
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['Access-Control-Allow-Origin'] = '*'

images = flask_uploads.UploadSet(
    'images',
    flask_uploads.IMAGES,
    default_dest=lambda app: os.path.join(app.root_path, 'images'),
)
flask_uploads.configure_uploads(app, images)

def byte_to_string(byte_string):
    return byte_string.decode("utf-8")

def parse_list_to_map(result):
    result_map = {}
    if result:
        for row in result:
            if len(row[1:]) <= 1:
                result_map[row[0]] = row[1]
            else:
                result_map[row[0]] = row[1:]
    return result_map

@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404

@app.route('/', methods=['GET'])
def home():
    return "<h1>JMKRIDE Stock Tracking REST API</h1>"


# ========================  INVENTORY  =========================================


@app.route('/api/v1/inventory/fetch-all', methods=['GET'])
@cross_origin()
def api_all_inventory():
    return flask.jsonify(parse_list_to_map(db.query("SELECT * FROM inventory")))

@app.route('/api/v1/inventory/fetch', methods=['GET'])
@cross_origin()
def api_get_inventory(python_id=None):
    query_string = "SELECT * FROM inventory WHERE id "
    request_id = None;
    if python_id:
        request_id = python_id
    elif flask.request.args.get('id'):
        request_id = flask.request.args['id']

    if request_id:
        query_string += "= " + str(request_id)
    elif flask.request.args.get('id_list'):
        print(flask.request.args.get('id_list'))
        print(json.loads(flask.request.args.get('id_list')))
        id_list = json.loads(flask.request.args.get('id_list'))
        query_string += "IN ({})".format(",".join(str(i) for i in id_list))
    else:
        return page_not_found(None)
    return flask.jsonify(parse_list_to_map(db.query(query_string)))

def python_get_inventory(id):
    query_string = "SELECT quantity FROM inventory WHERE id={}".format(id)
    return int(db.query(query_string)[0][0])

def python_create_inventory(id, quantity):
    query_string = (
        "INSERT INTO inventory (id, quantity) VALUES ({id}, {quantity})".format(
            id=id,
            quantity=quantity,
        )
    )
    db.query(query_string, write=True)

@app.route('/api/v1/inventory/actions/deposit', methods=['PUT'])
@cross_origin()
def api_increment_inventory():
    data = json.loads(flask.request.data.decode('utf-8'))
    request_id = data.get('id')
    request_quantity = data.get('quantity')
    query_string = (
        "UPDATE inventory SET quantity=quantity+{quantity} WHERE id={id}"
    )
    if request_id and request_quantity:
        query_string = query_string.format(id=request_id, quantity=request_quantity)
        db.query(query_string, write=True)
        return api_get_inventory(python_id=request_id)
    else:
        return page_not_found(None)

@app.route('/api/v1/inventory/actions/withdraw', methods=['PUT'])
@cross_origin()
def api_decrement_inventory():
    data = json.loads(flask.request.data.decode('utf-8'))
    request_id = data.get('id')
    request_quantity = data.get('quantity')
    query_string = (
        "UPDATE inventory SET quantity=quantity-{quantity} WHERE id={id}"
    )
    if request_id and request_quantity:
        query_string = query_string.format(id=request_id, quantity=request_quantity)
        db.query(query_string, write=True)
        return api_get_inventory(python_id=request_id)
    else:
        return page_not_found(None)

def python_decrement_inventory(id, quantity):
    query_string = (
        "UPDATE inventory SET quantity=quantity-{quantity} WHERE id={id}"
    ).format(id=id, quantity=quantity)

    try:
        db.query(query_string, write=True)
    except:
        return False

    return True


def python_get_next_part_UID():
    query_string = "SELECT MAX(id) FROM inventory"
    return(db.query(query_string)[0][0] + 1)



# ==========================  PARTS  ==========================================


@app.route('/api/v1/parts/fetch-all', methods=['GET'])
@cross_origin()
def api_all_parts():
    return flask.jsonify(db.query("SELECT id, type, name, active, created_at, color FROM parts"))

@app.route('/api/v1/parts/fetch', methods=['GET'])
@cross_origin()
def api_get_parts(python_id=None):
    query_string = "SELECT id, type, name, active, created_at, color FROM parts WHERE "
    request_id = flask.request.args.get('id', python_id)
    if request_id:
        query_string += "id=" + str(request_id);
    elif flask.request.args.get('id_list'):
        id_list = json.loads(flask.request.args.get('id_list'))
        query_string += "id IN ({})".format(",".join(str(i) for i in id_list))
    elif flask.request.args.get('type'):
        query_string += "type=\"{}\"".format(flask.request.args.get('type'))
    else:
        return page_not_found(None)
    return flask.jsonify(db.query(query_string))

def python_get_part_active(id):
    query_string = "SELECT (active) FROM parts WHERE id={}".format(id)
    result = not bool(int(db.query(query_string)[0][0]))
    return result

def python_get_part_id_by_name(name):
    query_string = 'SELECT id FROM parts WHERE name = ' + name + ';'
    result = parse_list_to_map(db.query(query_string))
    if result:
        return result[0][0]

    return result

def python_part_name_exists(name):
    return bool(python_get_part_id_by_name(name))

@app.route('/api/v1/parts/actions/modify', methods=['PUT'])
@cross_origin()
def api_modify_part():
    data = json.loads(flask.request.data.decode('utf-8'))
    
    expected = ['id', 'action']
    for key in expected:
        if key not in data:
            print("MODIFY FAILED. {} NOT PROVIDED".format(key))
            return
    queries = [] 
    if data['action'] == 'toggle_active':
        query_string = "UPDATE parts SET "
        currently_active = python_get_part_active(data['id'])
        if currently_active:
            query_string += "active=1"
        else:
            query_string += "active=0"
        queries.append(query_string)
    elif data['action'] == 'delete':
        queries = [
            "DELETE FROM parts",
            "DELETE FROM inventory",
        ]


    for query_string in queries:
        query_string += " WHERE id=" + str(data['id'])
        db.query(query_string, write=True)
    return "True"


@app.route('/api/v1/parts/actions/create', methods=['PUT'])
@cross_origin()
def api_create_part():
    post_data = json.loads(flask.request.data.decode('utf-8'))
    next_id = python_get_next_part_UID()

    expected_data = ['name', 'type', 'active', 'color', 'created_at']
    expected_string = ", ".join(expected_data)
    query_string = (
        "INSERT INTO parts (id, " + expected_string + ") "
        "VALUES ({id}, \"{name}\", \"{type}\", {active}, \"{color}\", {created_at})"
    )
    for key in expected_data:
        if key not in post_data:
            print("CREATE FAILED. MISSING: ", key)
            return page_not_found(None)
    if python_part_name_exists(post_data['name']):
        print(
            "CREATE FAILED. NAME \"{}\" ALREADY EXISTS AS ID {}".format(
                post_data['name'],
                python_get_part_id_by_name(post_data['name']),
            )
        )

    quantity = 0
    if "quantity" in post_data:
        quantity = post_data["quantity"]

    db.query(
        query_string.format(
            id=next_id,
            name=post_data["name"],
            type=post_data["type"],
            active=0 if post_data["active"] else 1,
            color=post_data["color"],
            created_at=post_data["created_at"],
        ),
        write=True,
    )

    # initialize quantity tracking of new part
    python_create_inventory(next_id, quantity) 

    return api_get_parts(python_id=next_id)


# ==========================  COMPLETE SETS  ==================================

def python_get_next_completeset_UID():
    query_string = "SELECT MAX(id) FROM completesets"
    result = db.query(query_string)
    if result[0][0] is not None:
        return result[0][0] + 1

    return 0

@app.route('/api/v1/completesets/fetch-all', methods=['GET'])
@cross_origin()
def api_all_completesets():
    query_string = (
        "SELECT id, filename, name, active, created_at, "
        "awheel1, awheel2, atruck, adeck, agrip, "
        "bwheel1, bwheel2, btruck, bdeck, bgrip FROM completesets"
    )
    return flask.jsonify(db.query(query_string))

@app.route('/api/v1/completesets/fetch', methods=['GET'])
@cross_origin()
def api_get_completesets(python_id=None):
    query_string = (
        "SELECT id, filename, name, active, created_at, "
        "awheel1, awheel2, atruck, adeck, agrip, "
        "bwheel1, bwheel2, btruck, bdeck, bgrip FROM completesets WHERE "
    )
    request_id = flask.request.args.get('id', python_id)
    if request_id:
        query_string += "id=" + str(request_id);
    elif flask.request.args.get('id_list'):
        id_list = json.loads(flask.request.args.get('id_list'))
        query_string += "id IN ({})".format(",".join(str(i) for i in id_list))
    else:
        return page_not_found(None)
    return flask.jsonify(db.query(query_string))

@app.route('/api/v1/completesets/actions/create', methods=['PUT'])
@cross_origin()
def api_create_completeset():
    post_data = flask.request
    form_data = post_data.form

    next_id = python_get_next_completeset_UID()
    
    expected_data = [
        'name', 'active', 'created_at',
        'awheel1', 'awheel2', 'atruck', 'adeck', 'agrip',
        'bwheel1', 'bwheel2', 'btruck', 'bdeck', 'bgrip',
    ]
    for key in expected_data:
        if key not in post_data.form:
            print("CREATE FAILED. MISSING: ", key)
            return page_not_found(None)


    if 'image_data' not in post_data.files:
        print('CREATE FAILED. Not file data found.')
        return page_not_found(None)
    
    try:
        filename = images.save(post_data.files['image_data'])
        print("Saved {}".format(filename))
    except flask_uploads.UploadNotAllowed as e:
        print('Image upload failed! Filetype rejected.' + str(e))
        raise

    expected_string = ", ".join(expected_data)
    query_string = (
        "INSERT INTO completesets (id, filename, " + expected_string + ") "
        "VALUES ({id}, \"{filename}\", \"{name}\", {active}, {created_at}, "
        "{awheel1}, {awheel2}, {atruck}, {adeck}, {agrip}, "
        "{bwheel1}, {bwheel2}, {btruck}, {bdeck}, {bgrip})"
    ).format(
        id=next_id,
        filename=filename,
        name=form_data['name'],
        active=0 if form_data['active'] else 1,
        created_at=form_data['created_at'],

        awheel1=form_data['awheel1'],
        awheel2=form_data['awheel2'],
        atruck=form_data['atruck'],
        adeck=form_data['adeck'],
        agrip=form_data['agrip'],

        bwheel1=form_data['bwheel1'],
        bwheel2=form_data['bwheel2'],
        btruck=form_data['btruck'],
        bdeck=form_data['bdeck'],
        bgrip=form_data['bgrip'],
    )

    db.query(query_string, write=True)
    
    return api_get_completesets(python_id=next_id)

def python_get_completeset_active(id):
    query_string = "SELECT (active) FROM completesets WHERE id={}".format(id)
    result = not bool(int(db.query(query_string)[0][0]))
    return result

@app.route('/api/v1/completesets/actions/modify', methods=['PUT'])
@cross_origin()
def api_modify_completeset():
    data = json.loads(flask.request.data.decode('utf-8'))
    
    expected = ['id', 'action']
    for key in expected:
        if key not in data:
            print("MODIFY FAILED. {} NOT PROVIDED".format(key))
            return
    queries = [] 
    if data['action'] == 'toggle_active':
        query_string = "UPDATE parts SET "
        currently_active = python_get_completeset_active(data['id'])
        if currently_active:
            query_string += "active=1"
        else:
            query_string += "active=0"
        queries.append(query_string)
    elif data['action'] == 'delete':
        queries = [
            "DELETE FROM completesets",
        ]


    for query_string in queries:
        query_string += " WHERE id=" + str(data['id'])
        db.query(query_string, write=True)
    return "True"

def python_get_completeset_id_quantities(id):
    query_string = (
        "SELECT awheel1, awheel2, atruck, adeck, agrip, "
        "bwheel1, bwheel2, btruck, bdeck, bgrip FROM completesets WHERE id={}".format(id)
    )
    result = db.query(query_string)
    if len(result) != 1:
        print("Received none or multiple responses. Failing.")
        return {}

    id_tuple = result[0]
    id_quantities = {}
    for id in id_tuple:
        if id in id_quantities:
            id_quantities[id] += 1
        else:
            id_quantities[id] = 1

    return id_quantities

@app.route('/api/v1/completesets/actions/withdraw', methods=['PUT'])
@cross_origin()
def api_withdraw_completeset():
    data = json.loads(flask.request.data.decode('utf-8'))
    request_id = data.get('id')
    request_quantity = data.get('quantity')

    id_quantities = python_get_completeset_id_quantities(request_id)
    for id in id_quantities:
        id_quantities[id] *= int(request_quantity)
    
    for id in id_quantities:
        expected_quantity = python_get_inventory(id) - id_quantities[id]
        python_decrement_inventory(id, id_quantities[id])
        result_quantity = python_get_inventory(id) 
        if expected_quantity != result_quantity:
            print("ERROR ID {}: Expected quantity: {}. Result quantity: {}.".format(
                id, expected_quantity, result_quantity)
            )
            success = False

    return ""

"""
    actions/stock: Returns tuple: (
        the maximum amount of completesets able to be withdrawn,
        and the id of the limiting factor part
    )
"""
@app.route('/api/v1/completesets/actions/stock', methods=['GET'])
@cross_origin()
def api_get_completeset_stock():
    request_id = flask.request.args.get('id')

    id_quantities = python_get_completeset_id_quantities(request_id)
    id_inventories = {}
    for id in id_quantities:
        id_inventories[id] = python_get_inventory(id)

    id_limits = []
    for id in id_inventories:
        id_limits.append((id_inventories[id] / id_quantities[id], id))
    limit = min(id_limits)

    return flask.jsonify((int(limit[0]), limit[1]))

@app.route('/api/v1/completesets/actions/fetch-image', methods=['GET'])
@cross_origin()
def api_get_image():
    request_filename = flask.request.args.get('filename')
    if not request_filename:
        return False
    return flask.send_file(
        os.path.join(app.root_path, 'images', request_filename),
        mimetype='image/jpg',
    )




if __name__ == "__main__":
    app.run()
