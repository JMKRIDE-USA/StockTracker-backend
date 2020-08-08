from IPython import embed
import flask
import json
from flask_cors import CORS, cross_origin
import MySQLdb
from MySQLdb.constants import FIELD_TYPE
import time
from functools import wraps


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


def retry(
    exceptions,
    tries=4,
    delay=3,
    backoff=2,
    logger=None,
    remediation_func=lambda x: x):
    """
    Retry calling the decorated function using an exponential backoff.

    Args:
        exceptions: The exception to check. may be a tuple of
            exceptions to check.
        tries: Number of times to try (not retry) before giving up.
        delay: Initial delay between retries in seconds.
        backoff: Backoff multiplier (e.g. value of 2 will double the delay
            each retry).
        logger: Logger to use. If None, print.
    """
    def deco_retry(f):

        @wraps(f)
        def f_retry(self, *args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(self, *args, **kwargs)
                except exceptions as e:
                    msg = '{}, Remediating and retrying in {} seconds...'.format(e, mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    remediation_func(self)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(self, *args, **kwargs)

        return f_retry  # true decorator

    return deco_retry

class DB:
    conn = None

    def connect(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = MySQLdb.connect(
            host="localhost",user="local",
            passwd="localpassword",db="jmkridestock",
            conv=db_conv,
        )
    
    @retry((MySQLdb.OperationalError, MySQLdb.Error), remediation_func=connect)
    def get_cursor(self):
        if not self.conn:
            self.connect()
        return self.conn.cursor()

    @retry((MySQLdb.OperationalError, MySQLdb.Error), remediation_func=connect)
    def execute_cursor(self, cursor, sql):
        cursor.execute(sql)
  
    def query(self, sql):
      log_query(sql)

      cursor = self.get_cursor()
      self.execute_cursor(cursor, sql)
  
      result = []
      try:
          result = cursor.fetchall()
          self.conn.commit()
          cursor.close()
      except MySQLdb._exceptions.ProgrammingError:
          print("execute() failed twice...")
  
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
    parse_list_to_map(db.query(query_string))

def python_create_inventory(id, quantity):
    query_string = (
        "INSERT INTO inventory (id, quantity) VALUE ({id}, {quantity})".format(
            id=id,
            quantity=quantity,
        )
    )
    db.query(query_string)

@app.route('/api/v1/inventory/actions/deposit', methods=['PUT'])
@cross_origin()
def api_increment_inventory():
    data = json.loads(flask.request.data.decode('utf-8'))
    request_id = data.get('id')
    request_quantity = data.get('quantity')
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
    return flask.jsonify(parse_list_to_map(db.query("SELECT id, type, name, active, created_at, color FROM parts")))

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
    return flask.jsonify(parse_list_to_map(db.query(query_string)))

def python_get_part_active(id):
    query_string = "SELECT (active) FROM parts WHERE id={}".format(id)
    result = not bool(int(db.query(query_string)[0][0]))
    return result

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
        db.query(query_string)
    return "True"


@app.route('/api/v1/parts/actions/create', methods=['PUT'])
@cross_origin()
def api_create_part():
    post_data = json.loads(flask.request.data.decode('utf-8'))
    next_id = python_get_next_UID()

    expected_data = ['name', 'type', 'active', 'color', 'created_at']
    expected_string = ", ".join(expected_data)
    query_string = (
        "INSERT INTO parts (id, " + expected_string + ") "
        "VALUE ({id}, \"{name}\", \"{type}\", {active}, \"{color}\", {created_at})"
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
            color=post_data["color"],
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
    python_get_part_active(1)
    #app.run()
