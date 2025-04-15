from flask import Flask, request, jsonify, abort
from flask_cors import CORS, cross_origin
from secrets import token_urlsafe
import psycopg2

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

def jsonVerify(contents: list, json):
    for cont in contents:
        if cont not in json:
            print(cont) 
            print("Missing from arguments") 
            return False
    return True
        
        

@app.route('/auth/login/email', methods=['POST', 'OPTIONS'])
@cross_origin(origin="*")
def email_login():
    json = request.json
    print(json)
    if not request or not jsonVerify(['email', 'password'], json):
        return jsonify({"detail": "Insufficient arguments"}), 400
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
    if not request or not jsonVerify(['email', 'password', 'name', 'lname'], json):
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
    token: str = request.headers.get('Authorization').split()[1]
    if (token == None): return jsonify({"detail": "No token"}), 400
    cur.execute('SELECT id, email, name, lname FROM users WHERE token = \'{0}\''.format(token))
    res = cur.fetchall()
    if (len(res) == 0): return jsonify({"detail": "Invalid token"}), 400
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
     cur.execute('SELECT id, name, description, price, discount, discount_type, stock, date_added FROM products limit 5 offset 5*{0}'.format(page))
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
             "date_added": prod[7]
             })
     print(prods)    
     return jsonify(prods), 200
     

if __name__ == '__main__':
    app.run(host='192.168.0.18', debug=True)