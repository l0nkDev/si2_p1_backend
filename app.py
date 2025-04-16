from flask import Flask, request, jsonify, abort
from flask_cors import CORS, cross_origin # type: ignore
from secrets import token_urlsafe
import psycopg2 # type: ignore

conn = psycopg2.connect(
        host="localhost",
        database="flask_db",
        user="sammy",
        password="password"
        )

cur = conn.cursor()

app = Flask(__name__)
cors = CORS(app)
app.config['DEBUG'] = True
app.config['CORS_HEADERS'] = 'application/json'

def requestVerify(contents: list, request):
    if not request: return False
    for cont in contents: 
        if cont not in request.json: return False
    return True
        
def authVerify(token):
    if (token == None): return False
    cur.execute('SELECT id, email, name, lname FROM users WHERE token = \'{0}\''.format(token))
    res = cur.fetchall()
    if (len(res) == 0): return False
    return True

def getUserId(token):
    cur.execute('SELECT id, email, name, lname FROM users WHERE token = \'{0}\''.format(token))
    res = cur.fetchall()
    return res[0][0]

@app.route('/auth/login/email', methods=['POST', 'OPTIONS'])
@cross_origin(origin="*")
def email_login():
    if not requestVerify(['email', 'password'], request):
        return jsonify({"detail": "Insufficient arguments"}), 400
    json = request.json
    print(json)
    cur.execute('SELECT id, token FROM users WHERE email = %s AND password = %s', (json["email"], json["password"]))
    res = cur.fetchall()
    print(res)
    if (len(res) == 0): return jsonify({"detail": "Incorrect email and/or password."}), 400
    return jsonify({
        "access_token": res[0][1],
        "id": res[0][0]
        }), 200



@app.route('/auth/register', methods=['POST', 'OPTIONS'])
@cross_origin(origin="*")
def register():
    token = token_urlsafe()
    json = request.json
    print(request.json)
    if not requestVerify(['email', 'password', 'name', 'lname'], json):
        return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('SELECT email FROM users WHERE email = \'{0}\''.format(json["email"]))
    res = cur.fetchall()
    if (len(res) != 0): return jsonify({"detail": "Email exists"}), 400
    cur.execute('INSERT INTO users (email, password, name, lname, role, token)'
        'VALUES (%s, %s, %s, %s, %s, %s)',
        (
            json["email"],
            json["password"],
            json["name"],
            json["lname"],
            "guest",
            token
            )
        )
    conn.commit()
    cur.execute('SELECT id FROM users WHERE email = \'{0}\''.format(json["email"]))
    res = cur.fetchall()
    cur.execute('INSERT INTO carts (userid) VALUES ({0})'.format(res[0][0]))
    conn.commit()
    return jsonify({"access_token": token, "id": res[0][0]}), 200 

@app.route('/users/self', methods=['GET', 'OPTIONS'])
@cross_origin(origin="*")
def self():
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
    cur.execute('SELECT id, email, name, lname FROM users WHERE token = \'{0}\''.format(token))
    res = cur.fetchall()
    return jsonify({
        "email": res[0][1],
        "id": res[0][0],
        "name": res[0][2],
        "lname": res[0][3]
        }), 200 

@app.route('/products', methods=['GET'])
@cross_origin(origin="*")
def prod():
     prods = []
     page = 0
     if ("page" in request.args): page = request.args["page"]
     cur.execute('SELECT id, name, description, price, discount, discount_type, stock, date_added, brand FROM products limit 5 offset 5*{0}'.format(page))
     res = cur.fetchall()
     for prod in res:
         prods.append({
             "id": prod[0],
             "name": prod[1],
             "description": prod[2],
             "price": prod[3],
             "discount": prod[4],
             "discount_type": prod[5],
             "stock": prod[6],
             "date_added": prod[7],
             "brand": prod[8]
             })
     print(prods)    
     return jsonify(prods), 200
 
@app.route('/products/get', methods=['GET'])
@cross_origin(origin="*")
def prod_get():
     id = 0
     if ("id" in request.args): id = request.args["id"]
     else: return jsonify({"detail": "No id"}), 400
     cur.execute('SELECT id, name, description, price, discount, discount_type, stock, date_added, brand FROM products WHERE id = {0}'.format(id))
     res = cur.fetchall()
     return jsonify({
             "id": res[0][0],
             "name": res[0][1],
             "description": res[0][2],
             "price": res[0][3],
             "discount": res[0][4],
             "discount_type": res[0][5],
             "stock": res[0][6],
             "date_added": res[0][7],
             "brand": res[0][8]
             }), 200
     
@app.route('/users/cart/add', methods=['POST'])
@cross_origin(origin="*")
def cart_add():
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
    if not requestVerify(['id'], request):
        return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('SELECT id FROM carts WHERE userid = {0} AND paid = \'N\''.format(getUserId(token)))
    res = cur.fetchall()
    currentCart = res[0][0]
    cur.execute('SELECT id FROM cart_entries WHERE cartid = {0} AND productid = {1}'.format(currentCart, request.json["id"]))
    res = cur.fetchall()
    if (len(res) == 0):
        cur.execute('INSERT INTO cart_entries (cartId, productId) VALUES ({0}, {1})'.format(currentCart, request.json["id"]))
    else:
        cur.execute('UPDATE cart_entries SET quantity = quantity + 1 WHERE id = {0}'.format(res[0][0]))
    conn.commit()
    cur.execute('SELECT id, cartid, productid, quantity FROM cart_entries WHERE cartid = {0} AND productid = {1}'.format(currentCart, request.json["id"]))
    res = cur.fetchall()
    return jsonify({
        "id": res[0][0],
        "cartid": res[0][1],
        "productid": res[0][2],
        "quantity": res[0][3]
        }), 200

@app.route('/users/cart', methods=['GET'])
@cross_origin(origin="*")
def cart():
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
    cur.execute('SELECT id FROM carts WHERE userid = {0}'.format(getUserId(token)))
    res = cur.fetchall()
    currentCart = res[0][0]
    cur.execute('SELECT id, cartid, productid, quantity FROM cart_entries WHERE cartid = {0}'.format(currentCart))
    res = cur.fetchall()
    items = []
    for item in res:
        items.append({
        "id": item[0],
        "cartid": item[1],
        "productid": item[2],
        "quantity": item[3]
        })
    return jsonify(items), 200


@app.route('/users/cart', methods=['DELETE'])
@cross_origin(origin="*")
def cart_delete():
    cur = conn.cursor()
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
    cur.execute('SELECT id FROM carts WHERE userid = {0}'.format(getUserId(token)))
    res = cur.fetchall()
    currentCart = res[0][0]
    cur.execute('DELETE FROM cart_entries WHERE cartid = {0}'.format(currentCart))
    conn.commit()
    return jsonify({"id": currentCart}), 200

    
    

if __name__ == '__main__':
    app.run(host='192.168.0.18', debug=True)