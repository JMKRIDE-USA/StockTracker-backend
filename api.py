from IPython import embed
import flask
import json
from flask_cors import CORS, cross_origin
import MySQLdb
from MySQLdb.constants import FIELD_TYPE

app = flask.Flask(__name__)
CORS(app)
app.config["DEBUG"] = True
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['Access-Control-Allow-Origin'] = '*'

def byte_to_string(byte_string):
    return byte_string.decode("utf-8")

def log_query(query_string):
    print("[DEBUG] Running: \"{}\"".format(query_string))


db_conv = { 
    FIELD_TYPE.DECIMAL: int,
    FIELD_TYPE.LONG: int,
    FIELD_TYPE.FLOAT: int,
    FIELD_TYPE.DOUBLE: int,
    FIELD_TYPE.NULL: lambda _: None,
    FIELD_TYPE.TIMESTAMP: int,
    FIELD_TYPE.LONGLONG: int,
    FIELD_TYPE.INT24: int, 
    FIELD_TYPE.VARCHAR: byte_to_string,
    FIELD_TYPE.BIT: bool,
    FIELD_TYPE.JSON: byte_to_string, 
    FIELD_TYPE.VAR_STRING: byte_to_string,
    FIELD_TYPE.STRING: byte_to_string,
    FIELD_TYPE.CHAR: byte_to_string,
}

class DB:
  conn = None

  def connect(self):
    self.conn = MySQLdb.connect(
        host="localhost",user="local",
        passwd="localpassword",db="jmkridestock",
        conv=db_conv,
    )

  def query(self, sql):
    log_query(sql)
    try:
        cursor = self.conn.cursor()
        cursor.execute(sql)
    except (AttributeError, MySQLdb.OperationalError):
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute(sql)
    self.conn.commit()
    result = cursor.fetchall()
    cursor.close()
    return result

db = DB()

def parse_list_to_map(result):
    result_map = {}
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
    elif flash.request.args.get('id'):
        request_id = flash.request.args['id']

    if request_id:
        query_string += "= " + str(request_id)
    elif flask.request.args.get('id_list'):
        id_list = json.loads(flask.request.args.get('id_list'))
        query_string += "IN ({})".format(",".join(str(i) for i in id_list))
    else:
        return page_not_found(None)
    return flask.jsonify(parse_list_to_map(db.query(query_string)))

def python_get_inventory(id):
    parse_list_to_map(db.query(query_string))

@app.route('/api/v1/inventory/actions/create', methods=['PUT'])
@cross_origin()
def api_create_inventory():
    post_data = flask.request.json
    request_id = post_data.get('id')
    request_quantity = post_data.get('quantity')
    query_string = "INSERT INTO inventory (id, quantity) VALUE ({}, {})"
    if request_id and request_quantity:
        query_string = query_string.format(request_id, request_quantity)
        db.query(query_string)
        return api_get_inventory(python_id=request_id)
    else:
        return page_not_found(None)

def python_create_inventory(id, quantity):
    query_string = (
        "INSERT INTO inventory (id, quantity) VALUE ({id}, {quantity})".format(
            id=id,
            quantity=quantity,
        )
    )
    db.query(query_string)

@app.route('/api/v1/inventory/actions/increment', methods=['PUT'])
@cross_origin()
def api_increment_inventory():
    post_data = flask.request.json
    request_id = post_data.get('id')
    request_quantity = post_data.get('quantity')
    query_string = (
        "UPDATE inventory set quantity=quantity+{quantity} where id={id}"
    )
    if request_id and request_quantity:
        query_string = query_string.format(id=request_id, quantity=request_quantity)
        db.query(query_string)
        return api_get_inventory(python_id=request_id)
    else:
        return page_not_found(None)

def python_get_next_UID():
    query_string = "SELECT MAX(id) FROM inventory"
    return(db.query(query_string)[0][0] + 1)




# ==========================  PARTS  ==========================================


@app.route('/api/v1/parts/fetch-all', methods=['GET'])
@cross_origin()
def api_all_parts():
    return flask.jsonify(parse_list_to_map(db.query("SELECT * FROM parts")))

@app.route('/api/v1/parts/fetch', methods=['GET'])
@cross_origin()
def api_get_parts(python_id=None):
    query_string = "SELECT * FROM parts WHERE id "
    request_id = flask.request.args.get('id', python_id)
    if request_id:
        query_string += "=" + str(request_id);
    elif flask.request.args.get('id_list'):
        id_list = json.loads(flask.request.args.get('id_list'))
        query_string += "IN ({})".format(",".join(str(i) for i in id_list))
    else:
        return page_not_found(None)
    return flask.jsonify(parse_list_to_map(db.query(query_string)))

@app.route('/api/v1/parts/actions/create', methods=['PUT'])
@cross_origin()
def api_create_part():
    post_data = flask.request.json

    next_id = python_get_next_UID()

    expected_data = ['name', 'type', 'active', 'created_at']
    expected_string = ", ".join(expected_data)
    query_string = (
        "INSERT INTO parts (id," + expected_string + ") "
        "VALUE ({id}, \"{name}\", \"{type}\", {active}, {created_at})"
    )
    for key in expected_data:
        if key not in post_data:
            print("CREATE FAILED. MISSING: ", key)
            return page_not_found(None)

    quantity = 0
    if "quantity" in post_data:
        quantity = post_data["quantity"]

    db.query(
        query_string.format(
            id=next_id,
            name=post_data["name"],
            type=post_data["type"],
            active=post_data["active"],
            created_at=post_data["created_at"],
        )
    )

    # initialize quantity tracking of new part
    python_create_inventory(next_id, quantity) 

    return api_get_parts(python_id=next_id)


# ==========================  COMPLETE SETS  ==================================


@app.route('/api/v1/completesets/fetch-all', methods=['GET'])
@cross_origin()
def api_all_completesets():
    return flask.jsonify(db.query("SELECT * FROM completesets"))

if __name__ == "__main__":
    python_get_next_UID()
    #app.run()
