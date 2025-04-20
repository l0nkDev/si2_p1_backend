from flask import Flask, request, jsonify, send_from_directory, redirect, render_template, make_response # type: ignore
from flask_cors import CORS, cross_origin # type: ignore
from secrets import token_urlsafe
import psycopg2 # type: ignore
from pathlib import Path
from stripe import StripeClient # type: ignore
import htmlhelper
import reportehelper
import pdfkit # type: ignore

client = StripeClient("")

UPLOAD_FOLDER = str(Path(__file__).parent / 'assets')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg'}

conn = psycopg2.connect(
        host="localhost",
        database="flask_db",
        user="sammy",
        password="password"
        )


app = Flask(__name__)
cors = CORS(app)
app.config['DEBUG'] = True
app.config['CORS_HEADERS'] = 'application/json'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def requestVerify(contents: list, request):
    if not request: return False
    for cont in contents: 
        if cont not in request.json: return False
    return True
        
def authVerify(token):
    cur = conn.cursor() 
    if (token == None): return False
    cur.execute('SELECT id, email, name, lname FROM users WHERE token = \'{0}\' AND deleted = \'N\''.format(token))
    res = cur.fetchall()
    if (len(res) == 0): return False
    return True

def getUserId(token):
    cur = conn.cursor() 
    cur.execute('SELECT id, email, name, lname FROM users WHERE token = \'{0}\' AND deleted = \'N\''.format(token))
    res = cur.fetchall()
    return res[0][0]

def adminVerify(token):
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE token = \'{0}\' AND deleted = \'N\''.format(token))
    res = cur.fetchall()
    return res[0][0] in ['admin', 'owner']

def delivVerify(token):
    cur = conn.cursor()
    cur.execute('SELECT role FROM users WHERE token = \'{0}\' AND deleted = \'N\''.format(token))
    res = cur.fetchall()
    return res[0][0] in ['delivery', 'owner']

def isVip(token):
    cur = conn.cursor()
    cur.execute('select coalesce(sum(total_paid), 0) from purchases, carts where cartid = carts.id and purchases.paid_on > (NOW() - interval \' 1 week\') and carts.userid = {0}'.format(getUserId(token)))
    res = cur.fetchall()
    return res[0][0] >= 1000

def insertBitacora(id, action, ip):
    cur = conn.cursor()
    cur.execute('select name, lname, email, role from users where id = {0}'.format(id))
    res = cur.fetchall()
    cur.execute('Insert into bitacora (username, email, role, ip, action) values (%s, %s, %s, %s, %s)',
                (
                    "{0} {1}".format(res[0][0], res[0][1]),
                    res[0][2],
                    res[0][3],
                    ip,
                    action
                ))
    conn.commit()

@app.route('/auth/login/email', methods=['POST', 'OPTIONS'])
@cross_origin(origin="*")
def email_login():
    cur = conn.cursor() 
    if not requestVerify(['email', 'password'], request):
        return jsonify({"detail": "Insufficient arguments"}), 400
    json = request.json
    print(json)
    cur.execute('SELECT id, token FROM users WHERE email = %s AND password = %s AND deleted = \'N\'', (json["email"], json["password"]))
    res = cur.fetchall()
    print(res)
    if (len(res) == 0): return jsonify({"detail": "Incorrect email and/or password."}), 400
    insertBitacora(res[0][0], "Ingresó al sistema", request.remote_addr)
    return jsonify({
        "access_token": res[0][1],
        "id": res[0][0]
        }), 200

@app.route('/auth/register', methods=['POST', 'OPTIONS'])
@cross_origin(origin="*")
def register():
    cur = conn.cursor() 
    token = token_urlsafe()
    json = request.json
    print(request.json)
    if not requestVerify(['email', 'password', 'name', 'lname', 'country', 'state', 'address'], request):
        return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('SELECT email FROM users WHERE email = \'{0}\' AND deleted = \'N\''.format(request.json["email"]))
    res = cur.fetchall()
    if (len(res) != 0): return jsonify({"detail": "Email exists"}), 400
    cur.execute('INSERT INTO users (email, password, name, lname, role, token, country, state, address)'
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (
            json["email"],
            json["password"],
            json["name"],
            json["lname"],
            "guest",
            token,
            json["country"],
            json["state"],
            json["address"],
            )
        )
    conn.commit()
    cur.execute('SELECT id FROM users WHERE email = \'{0}\' AND deleted = \'N\''.format(json["email"]))
    res = cur.fetchall()
    insertBitacora(res[0][0], "Se registró en el sistema", request.remote_addr)
    cur.execute('INSERT INTO carts (userid) VALUES ({0})'.format(res[0][0]))
    conn.commit()
    return jsonify({"access_token": token, "id": res[0][0]}), 200 

@app.route('/users/self', methods=['GET', 'OPTIONS'])
@cross_origin(origin="*")
def self():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
    cur.execute('SELECT id, email, name, lname, role, country, state, address, password FROM users WHERE token = \'{0}\' AND deleted = \'N\''.format(token))
    res = cur.fetchall()
    return jsonify({
        "email": res[0][1],
        "id": res[0][0],
        "name": res[0][2],
        "lname": res[0][3],
        "role": res[0][4],
        "country": res[0][5],
        "state": res[0][6],
        "address": res[0][7],
        "password": res[0][8],
        "token": token,
        'vip': 'Y' if isVip(token) else 'N'
        }), 200 

@app.route('/users/self', methods=['PATCH'])
@cross_origin(origin="*")
def update_self():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not requestVerify(['email', 'password', 'name', 'lname', 'country', 'state', 'address'], request): return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('update users set email = %s, password = %s, name = %s, lname = %s, country = %s, state = %s, address = %s where id = %s', (
        request.json["email"],
        request.json["password"],
        request.json["name"],
        request.json["lname"],
        request.json["country"],
        request.json["state"],
        request.json["address"],
        getUserId(token)
    ))
    insertBitacora(getUserId(token), "Actualizó sus datos personales.", request.remote_addr)
    conn.commit()
    return jsonify({"detail": "updated"}), 200




@app.route('/products', methods=['GET'])
@cross_origin(origin="*")
def prod():
    cur = conn.cursor() 
    prods = []
    page = 0
    if ("page" in request.args): page = request.args["page"]
    cur.execute('SELECT products.*, cast(coalesce(avg(rating) filter (where productid = products.id), 0) AS DECIMAL(2,1)) FROM products, productrating WHERE deleted = \'N\' group by products.id ORDER BY products.id DESC limit 20 offset 20*{0}'.format(page))
    res = cur.fetchall()
    for prod in res:
        prods.append({
            "id": prod[0],
            "name": prod[1],
            "description": prod[3],
            "price": prod[4],
            "discount": prod[5],
            "discount_type": prod[6],
            "stock": prod[7],
            "brand": prod[2],
            "rating": prod[11]
            })
    print(prods)    
    return jsonify(prods), 200

@app.route('/products/search', methods=['GET'])
@cross_origin(origin="*")
def prod_search():
    cur = conn.cursor() 
    prods = []
    page = 0
    if ("page" in request.args): page = request.args["page"]
    cur.execute('''SELECT products.*, cast(coalesce(avg(rating) filter (where productid = products.id), 0) AS DECIMAL(2,1)), ts_rank(to_tsvector('spanish', name || ' ' || coalesce(description, '')), websearch_to_tsquery('spanish', '{1}')) as rank
                   FROM products, productrating WHERE deleted = 'N' AND to_tsvector('spanish', name || ' ' || coalesce(description, '')) @@ websearch_to_tsquery('spanish', '{1}') group by products.id ORDER BY rank DESC limit 20 offset 20*{0}'''.format(page, request.args["q"]))
    res = cur.fetchall()
    for prod in res:
        prods.append({
            "id": prod[0],
            "name": prod[1],
            "description": prod[3],
            "price": prod[4],
            "discount": prod[5],
            "discount_type": prod[6],
            "stock": prod[7],
            "brand": prod[2],
            "rating": prod[11]
            })
    print(prods)    
    return jsonify(prods), 200
 
@app.route('/products/get', methods=['GET'])
@cross_origin(origin="*")
def prod_get():
    cur = conn.cursor() 
    id = 0
    if ("id" in request.args): id = request.args["id"]
    else: return jsonify({"detail": "No id"}), 400
    cur.execute(
        '''
        select products.*, count(purchased.productid), cast(coalesce(avg(rating) filter (where productrating.productid = products.id), 0) AS DECIMAL(2,1)) from purchased, products, productrating 
        where products.id = purchased.productid and purchased.productid != {0} and products.deleted = 'N'
        and purchaseid in (select purchaseid from purchased, purchases 
                        where purchaseid = purchases.id and productid = {0} 
                        and purchases.paid_on > (NOW() - interval ' 6 months')) 
        group by products.id order by count desc limit 5;
        '''.format(id)
        )
    res = cur.fetchall()
    recs = []
    for item in res:
        recs.append(
            {
            "id": item[0],
            "name": item[1],
            "brand": item[2],
            "description": item[3],
            "price": item[4],
            "discount": item[5],
            "discount_type": item[6],
            "stock": item[7],
            "date_added": item[9],
            "rating": item[12],
            }
        )
    cur.execute('SELECT products.id, name, description, price, discount, discount_type, stock, date_added, brand, cast(coalesce(avg(rating) filter (where productid = products.id), 0) as decimal(2,1)) FROM products, productrating WHERE products.id = {0} group by products.id'.format(id))
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
            "brand": res[0][8],
            "rating": res[0][9],
            "recommendations": recs
            }), 200
     
@app.route('/users/cart/add', methods=['POST'])
@cross_origin(origin="*")
def cart_add():
    cur = conn.cursor() 
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
    cur.execute('select name from products where id = {0}'.format(request.json["id"]))
    res = cur.fetchall()
    insertBitacora(getUserId(token), "Añadió \"{0}\" a su carrito.".format(res[0][0]).replace("'", "''"), request.remote_addr)    
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
    cur = conn.cursor() 
    cur2 = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
    cur.execute('SELECT id FROM carts WHERE userid = {0} AND paid = \'N\''.format(getUserId(token)))
    res = cur.fetchall()
    currentCart = res[0][0]
    cur.execute('SELECT id, cartid, productid, quantity FROM cart_entries WHERE cartid = {0} ORDER BY id DESC'.format(currentCart))
    res = cur.fetchall()
    items = []
    for item in res:
        cur2.execute('SELECT products.id, name, description, price, discount, discount_type, stock, date_added, brand, cast(coalesce(avg(rating) filter (where productid = products.id), 0) as decimal(2,1)) FROM products, productrating WHERE products.id = {0} AND deleted = \'N\' group by products.id'.format(item[2]))
        res2 = cur2.fetchall()
        items.append({
        "id": item[0],
        "cartid": item[1],
        "productid": item[2],
        "quantity": item[3],
        "product": {
            "id": res2[0][0],
            "name": res2[0][1],
            "description": res2[0][2],
            "price": res2[0][3],
            "discount": res2[0][4],
            "discount_type": res2[0][5],
            "stock": res2[0][6],
            "date_added": res2[0][7],
            "brand": res2[0][8],
            "rating": res2[0][9]
            }
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
    cur.execute('SELECT id FROM carts WHERE userid = {0} AND paid = \'N\''.format(getUserId(token)))
    res = cur.fetchall()
    currentCart = res[0][0]
    cur.execute('DELETE FROM cart_entries WHERE cartid = {0}'.format(currentCart))
    conn.commit()
    insertBitacora(getUserId(token), "Vació su carrito.", request.remote_addr)    
    return jsonify({"id": currentCart}), 200

  

    
@app.route('/users/cart/add', methods=['PATCH'])
@cross_origin(origin="*")
def cart_update():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
    if not requestVerify(['id', 'quantity'], request):
        return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('UPDATE cart_entries SET quantity = {0} WHERE id = {1}'.format(request.json["quantity"], request.json["id"]))
    cur.execute('select products.name from products, cart_entries where cart_entries.id = {0} and productid = products.id'.format(request.json["id"]))
    res = cur.fetchall()
    insertBitacora(getUserId(token), "Actualizó \"{0}\" en su carrito.".format(res[0][0]).replace("'", "''"), request.remote_addr)    
    cur.execute('SELECT * FROM cart_entries WHERE id = {0}'.format(request.json["id"]))
    res = cur.fetchall()
    return jsonify({
        "id": res[0][0],
        "cartid": res[0][1],
        "productid": res[0][2],
        "quantity": res[0][3]
        }), 200

@app.route('/admin/product/add', methods=['PATCH'])
@cross_origin(origin="*")
def product_update():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
    if not adminVerify(token):
        return jsonify({"detail": "Unauthorized"}), 400
    if not requestVerify(['id', 'name', 'brand', 'description', 'price', 'discount', 'discount_type', 'stock'], request):
        return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('UPDATE products SET name = \'{1}\', brand = \'{2}\', description = \'{3}\', price = {4}, discount = {5}, discount_type = \'{6}\', stock = {7} WHERE id = {0}'
                .format(request.json["id"], request.json["name"].replace("'", "''"), request.json["brand"].replace("'", "''"), request.json["description"].replace("'", "''"), request.json["price"], request.json["discount"], request.json["discount_type"].replace("'", "''"), request.json["stock"]))
    insertBitacora(getUserId(token), "Actualizó el producto: \"{0}\"".format(request.json["name"]).replace("'", "''"), request.remote_addr)    
    conn.commit()
    return jsonify({"detail": "Updated"}), 200


@app.route('/admin/product/add', methods=['POST'])
@cross_origin(origin="*")
def product_add():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
    if not adminVerify(token):
        return jsonify({"detail": "Unauthorized"}), 400
    if not requestVerify(['name', 'brand', 'description', 'price', 'discount', 'discount_type', 'stock'], request):
        return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('INSERT INTO products (name, brand, description, price, discount, discount_type, stock) VALUES (\'{0}\', \'{1}\', \'{2}\', {3}, {4}, \'{5}\', {6})'
                .format(request.json["name"].replace("'", "''"), request.json["brand"].replace("'", "''"), request.json["description"].replace("'", "''"), request.json["price"], request.json["discount"], request.json["discount_type"].replace("'", "''"), request.json["stock"]))
    conn.commit()
    insertBitacora(getUserId(token), "Insertó el producto: \"{0}\"".format(request.json["name"]).replace("'", "''"), request.remote_addr)    
    return jsonify({"detail": "Inserted"}), 200

@app.route('/users/cart/remove', methods=['DELETE'])
@cross_origin(origin="*")
def cart_entry_delete():
    cur = conn.cursor()
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
    cur.execute('select products.name from products, cart_entries where cart_entries.id = {0} and productid = products.id'.format(request.args["id"]))
    res = cur.fetchall()
    insertBitacora(getUserId(token), "Eliminó \"{0}\" de su carrito.".format(res[0][0]).replace("'", "''"), request.remote_addr)   
    cur.execute('DELETE FROM cart_entries WHERE id = {0}'.format(request.args["id"]))
    conn.commit()
    return jsonify({"detail": "Entry removed"}), 200

@app.route('/admin/product/remove', methods=['DELETE'])
@cross_origin(origin="*")
def product_delete():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not adminVerify(token): return jsonify({"detail": "Unauthorized"}), 400
    cur.execute('select name from products where id = {0}'.format(request.args["id"]))
    res = cur.fetchall()
    insertBitacora(getUserId(token), "Eliminó el producto: \"{0}\"".format(res[0][0]).replace("'", "''"), request.remote_addr)  
    cur.execute('UPDATE products SET deleted = \'Y\' WHERE id = {0}'.format(request.args["id"]))
    conn.commit()
    return jsonify({"detail": "Product deleted"}), 200

@app.route('/admin/users/add', methods=['POST'])
@cross_origin(origin="*")
def users_add():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not adminVerify(token): return jsonify({"detail": "Unauthorized"}), 400
    if not requestVerify(['email', 'password', 'name', 'lname', 'address', 'state', 'country', 'role'], request): return jsonify({"detail": "Insufficient arguments"}), 400
    token = token_urlsafe()
    cur.execute('SELECT email FROM users WHERE email = \'{0}\' AND deleted = \'N\''.format(request.json["email"]))
    res = cur.fetchall()
    if (len(res) != 0): return jsonify({"detail": "Email exists"}), 400
    insertBitacora(getUserId(request.headers.get('Authorization').split()[1]), "Insertó el usuario: \"{0}\"".format("{0} {1}".format(request.json["name"], request.json["lname"])).replace("'", "''"), request.remote_addr)  
    cur.execute('INSERT INTO users (email, password, name, lname, role, address, state, country, token)'
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (
            request.json["email"],
            request.json["password"],
            request.json["name"],
            request.json["lname"],
            request.json["role"],
            request.json["address"],
            request.json["state"],
            request.json["country"],
            token
            )
        )
    conn.commit()
    cur.execute('SELECT id FROM users WHERE email = \'{0}\' and deleted = \'N\''.format(request.json["email"]))
    res = cur.fetchall()
    cur.execute('INSERT INTO carts (userid) VALUES ({0})'.format(res[0][0]))
    conn.commit()
    return jsonify({"access_token": token, "id": res[0][0]}), 200 

@app.route('/admin/users', methods=['GET'])
@cross_origin(origin="*")
def users():
    token = token_urlsafe()
    cur = conn.cursor() 
    users = []
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not adminVerify(token): return jsonify({"detail": "Unauthorized"}), 400
    cur.execute('SELECT * FROM users WHERE deleted = \'N\' ORDER BY id DESC')
    res = cur.fetchall()
    for user in res:
        users.append(
            {
                'id': user[0],
                'email': user[1],
                'password': user[2],
                'name': user[3],
                'lname': user[4],
                'role': user[5],
                'country': user[8],
                'state': user[9],
                'address': user[10],
            }
        )
    return jsonify(users), 200

@app.route('/admin/users/add', methods=['PATCH'])
@cross_origin(origin="*")
def users_update():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not adminVerify(token): return jsonify({"detail": "Unauthorized"}), 400
    if not requestVerify(['id', 'name', 'lname', 'email', 'role', 'country', 'address', 'state', 'password'], request): return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('UPDATE users SET name = \'{0}\', lname = \'{1}\', email = \'{2}\', role = \'{3}\', country = \'{4}\', address = \'{5}\', state = \'{6}\', password = \'{8}\' WHERE id = {7}'
                .format(request.json["name"].replace("'", "''"), request.json["lname"].replace("'", "''"), request.json["email"].replace("'", "''"), request.json["role"].replace("'", "''"), request.json["country"].replace("'", "''"), request.json["address"].replace("'", "''"), request.json["state"].replace("'", "''"), request.json["id"], request.json["password"].replace("'", "''")))
    conn.commit()
    insertBitacora(getUserId(token), "Actualizó al usuario: \"{0}\"".format("{0} {1}".format(request.json["name"], request.json["lname"])).replace("'", "''"), request.remote_addr) 
    return jsonify({"detail": "User updated"}), 200 

@app.route('/admin/users/remove', methods=['DELETE'])
@cross_origin(origin="*")
def users_delete():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not adminVerify(token): return jsonify({"detail": "Unauthorized"}), 400
    cur.execute('UPDATE users SET deleted = \'Y\' WHERE id = {0}'.format(request.args["id"]))
    conn.commit()
    cur.execute('select name, lname from users where id = {0}'.format(request.args["id"]))
    res = cur.fetchall()
    insertBitacora(getUserId(token), "Eliminó al usuario: \"{0}\"".format("{0} {1}".format(res[0][0], res[0][1])).replace("'", "''"), request.remote_addr) 
    return jsonify({"detail": "Product deleted"}), 200

@app.route('/users/cart/checkout', methods=['POST'])
@cross_origin(origin="*")
def cart_checkout():
    cur = conn.cursor()
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
    cur.execute('SELECT id FROM carts WHERE userid = {0} AND paid = \'N\''.format(getUserId(token)))
    res = cur.fetchall()
    currentCart = res[0][0]
    cur.execute('''
                insert into purchases (cartid, total_paid, vip) 
                SELECT carts.id, 
                sum(
                    case 
                        when discount = 0 then CAST(price*quantity AS decimal(12,2)) 
                        when discount_type = 'P' then CAST((price*(1-(discount*0.01)))*quantity AS decimal(12,2)) 
                        else CAST((price-discount)*quantity AS decimal(12,2)) 
                    end) as tprice, '{1}' 
                from products, cart_entries, carts where 
                    products.id = productid and 
                    deleted = 'N' and 
                    cartid = carts.id and 
                    carts.id = {0} group by carts.id;
        '''.format(currentCart, "Y" if isVip(token) else "N"))
    cur.execute('''
                insert into purchased (purchaseid, productid, name, brand, price, dprice, quantity, fprice) 
                    select 
                        (select id from purchases where cartid = {0} group by id) as purchaseid, 
                        products.id, name, brand, price, 
                        case 
                            when discount = 0 then CAST(price AS decimal(12,2)) 
                            when discount_type = 'P' then CAST(price*(1-(discount*0.01)) AS decimal(12,2)) 
                            else CAST(price-discount AS decimal(12,2)) 
                        end as dprice, quantity,
                        case 
                            when discount = 0 then CAST(price*quantity AS decimal(12,2)) 
                            when discount_type = 'P' then CAST((price*(1-(discount*0.01)))*quantity AS decimal(12,2)) 
                            else CAST((price-discount)*quantity AS decimal(12,2)) 
                        end as fprice 
                        from products, cart_entries where 
                        products.id = cart_entries.productid and 
                        products.deleted = 'N' and cart_entries.cartid = {0};
        '''.format(currentCart))
    cur.execute('update carts set paid = \'Y\' where id = {0};'.format(currentCart))
    cur.execute('insert into carts (userid) values ({0});'.format(getUserId(token)))
    conn.commit()
    return jsonify({"detail": "done"}), 200

@app.route('/users/purchases', methods=['GET'])
@cross_origin(origin="*")
def purchases():
    cur = conn.cursor()
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    cur.execute('SELECT purchases.*, purchased.*, cast(coalesce(avg(productrating.rating) filter (where productrating.productid = purchased.productid), 0) as decimal(2,1)), cast(coalesce((select rating from deliveryrating where purchaseid = purchases.id), 0) as decimal(2,1)) from purchased, purchases, carts, productrating where purchased.purchaseid = purchases.id and cartid = carts.id and carts.userid = {0} group by (purchases.id, purchased.id) order by purchases.id desc'.format(getUserId(token)))
    res = cur.fetchall()
    if len(res) == 0: return jsonify({"detail": "No purchases"}), 400
    purchases = []
    id = res[0][0]
    paid_on: str = res[0][2]
    total_paid = res[0][3]
    payment_method = res[0][4]
    delivery_status = res[0][5]
    vip = res[0][6]
    rating = res[0][17]
    purchase = []
    for entry in res:
        if entry[0] != id:
            purchases.append(
                {
                    "id": id,
                    "paid_on": paid_on,
                    "total_paid": total_paid,
                    "payment_method": payment_method,
                    "delivery_status": delivery_status,
                    "vip": vip,
                    "rating": rating,
                    "items": purchase
                }
            )
            id = entry[0]
            paid_on = entry[2]
            total_paid = entry[3]
            payment_method = entry[4]
            delivery_status = entry[5] 
            vip = entry[6] 
            rating = entry[17] 
            purchase = []
        purchase.append(
            {
                "id": entry[7],
                "productid": entry[9],
                "name": entry[10],
                "brand": entry[11],
                "price": entry[12],
                "dprice": entry[13],
                "quantity": entry[14],
                "fprice": entry[15],
                "rating": entry[16]
            }
        )
    purchases.append(
        {
            "id": id,
            "paid_on": paid_on,
            "total_paid": total_paid,
            "payment_method": payment_method,
            "delivery_status": delivery_status,
            "rating": rating,
            "items": purchase
        }
    )
    return jsonify(purchases), 200

@app.route('/admin/delivery', methods=['GET'])
@cross_origin(origin="*")
def delivery():
    cur = conn.cursor()
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not delivVerify(token): return jsonify({"detail": "Unauthorized"}), 400
    cur.execute('SELECT purchases.id, users.name, users.lname, users.country, users.state, users.address, purchases.paid_on, purchases.delivery_status, purchased.name, purchased.brand, purchased.quantity from purchased, purchases, carts, users where purchaseid = purchases.id and cartid = carts.id and carts.userid = users.id and purchases.id not in (select purchaseid from deliveryassignment) order by purchases.id desc')
    res = cur.fetchall()
    if len(res) == 0: return jsonify({"detail": "No purchases"}), 400
    purchases = []
    id = res[0][0]
    name = res[0][1]
    lname = res[0][2]
    country = res[0][3]
    state = res[0][4]
    address = res[0][5]
    paid_on = res[0][6]
    delivery_status = res[0][7]
    purchase = []
    for entry in res:
        if entry[0] != id:
            purchases.append(
                {
                    "id": id,
                    "name": name,
                    "lname": lname,
                    "country": country,
                    "state": state,
                    "address": address,
                    "paid_on": paid_on,
                    "delivery_status": delivery_status,
                    "items": purchase
                }
            )
            id = entry[0]
            name = entry[1]
            lname = entry[2]
            country = entry[3]
            state = entry[4]
            address = entry[5]
            paid_on = entry[6]
            delivery_status = entry[7]
            purchase = []
        purchase.append(
            {
                "name": entry[8],
                "brand": entry[9],
                "quantity": entry[10],
            }
        )
    purchases.append(
        {
            "id": id,
            "name": name,
            "lname": lname,
            "country": country,
            "state": state,
            "address": address,
            "paid_on": paid_on,
            "delivery_status": delivery_status,
            "items": purchase
        }
    )
    return jsonify(purchases), 200

@app.route('/admin/delivery', methods=['PATCH'])
@cross_origin(origin="*")
def update_delivery():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not delivVerify(token): return jsonify({"detail": "Unauthorized"}), 400
    if not requestVerify(['id'], request): return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('UPDATE purchases SET delivery_status = \'En delivery\' WHERE id = {0}'.format(request.json["id"]))
    cur.execute('insert into deliveryassignment (userid, purchaseid) values ({0}, {1})'.format(getUserId(token), request.json["id"]))
    insertBitacora(getUserId(token), "Tomó el pedido {0}.".format(request.json["id"]), request.remote_addr) 
    conn.commit()
    return jsonify({"detail": "Updated"}), 200 

@app.route('/admin/delivery/me', methods=['GET'])
@cross_origin(origin="*")
def deliveryown():
    cur = conn.cursor()
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not delivVerify(token): return jsonify({"detail": "Unauthorized"}), 400
    cur.execute('SELECT purchases.id, users.name, users.lname, users.country, users.state, users.address, purchases.paid_on, purchases.delivery_status, purchased.name, purchased.brand, purchased.quantity from purchased, purchases, carts, users where purchaseid = purchases.id and cartid = carts.id and carts.userid = users.id and purchases.id in (select purchaseid from deliveryassignment where userid = {0}) order by purchases.id desc'.format(getUserId(token)))
    res = cur.fetchall()
    if len(res) == 0: return jsonify({"detail": "No purchases"}), 400
    purchases = []
    id = res[0][0]
    name = res[0][1]
    lname = res[0][2]
    country = res[0][3]
    state = res[0][4]
    address = res[0][5]
    paid_on = res[0][6]
    delivery_status = res[0][7]
    purchase = []
    for entry in res:
        if entry[0] != id:
            purchases.append(
                {
                    "id": id,
                    "name": name,
                    "lname": lname,
                    "country": country,
                    "state": state,
                    "address": address,
                    "paid_on": paid_on,
                    "delivery_status": delivery_status,
                    "items": purchase
                }
            )
            id = entry[0]
            name = entry[1]
            lname = entry[2]
            country = entry[3]
            state = entry[4]
            address = entry[5]
            paid_on = entry[6]
            delivery_status = entry[7]
            purchase = []
        purchase.append(
            {
                "name": entry[8],
                "brand": entry[9],
                "quantity": entry[10],
            }
        )
    purchases.append(
        {
            "id": id,
            "name": name,
            "lname": lname,
            "country": country,
            "state": state,
            "address": address,
            "paid_on": paid_on,
            "delivery_status": delivery_status,
            "items": purchase
        }
    )
    return jsonify(purchases), 200

@app.route('/admin/delivery/me', methods=['PATCH'])
@cross_origin(origin="*")
def update_delivery_assigned():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not delivVerify(token): return jsonify({"detail": "Unauthorized"}), 400
    if not requestVerify(['id'], request): return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('UPDATE purchases SET delivery_status = \'Entregado\' WHERE id = {0}'.format(request.json["id"]))
    cur.execute('insert into deliveryassignment (userid, purchaseid) values ({0}, {1})'.format(getUserId(token), request.json["id"]))
    conn.commit()
    insertBitacora(getUserId(token), "Entregó el pedido {0}.".format(request.json["id"]), request.remote_addr) 
    return jsonify({"detail": "Updated"}), 200 

@app.route('/users/purchases/rate', methods=['POST'])
@cross_origin(origin="*")
def rate_delivery():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not requestVerify(['id', 'rating'], request): return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('select id from deliveryrating where userid = {0} and purchaseid = {1}'.format(getUserId(token), request.json["id"]))
    res = cur.fetchall()
    if len(res) > 0: cur.execute('update deliveryrating set rating = {2} where userid = {0} and purchaseid = {1}'.format(getUserId(token), request.json["id"], request.json["rating"]))
    else: cur.execute('insert into deliveryrating (userid, purchaseid, rating) values ({0}, {1}, {2})'.format(getUserId(token), request.json["id"], request.json["rating"]))
    conn.commit()
    insertBitacora(getUserId(token), "Calificó el pedido {0} con {1}.".format(request.json["id"], request.json["rating"]), request.remote_addr) 
    return jsonify({"detail": "Rated"}), 200

@app.route('/users/products/rate', methods=['POST'])
@cross_origin(origin="*")
def rate_product():
    cur = conn.cursor() 
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not requestVerify(['id', 'rating'], request): return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('select id from productrating where userid = {0} and productid = {1}'.format(getUserId(token), request.json["id"]))
    res = cur.fetchall()
    if len(res) > 0: cur.execute('update productrating set rating = {2} where userid = {0} and productid = {1}'.format(getUserId(token), request.json["id"], request.json["rating"]))
    else: cur.execute('insert into productrating (userid, productid, rating) values ({0}, {1}, {2})'.format(getUserId(token), request.json["id"], request.json["rating"]))
    conn.commit()
    cur.execute('select name from products where id = {0}'.format(request.json["id"]))
    res = cur.fetchall()
    insertBitacora(getUserId(token), "Calificó el producto \"{0}\" con {1}".format(res[0][0], request.json["rating"]).replace("'", "''"), request.remote_addr) 
    return jsonify({"detail": "Rated"}), 200

@app.route('/products/img/<id>', methods=['GET'])
@cross_origin(origin="*")
def download_img(id):
    try: res = send_from_directory(app.config["UPLOAD_FOLDER"], id)
    except: return send_from_directory(app.config["UPLOAD_FOLDER"], "default.png")
    return res

@app.route('/products/img', methods=['POST'])
@cross_origin(origin="*")
def upload_file():
    if "id" not in request.args: return jsonify({"detail": "Insufficient arguments"})
    if 'file' not in request.files:
        return jsonify({"detail": "No image arg"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"detail": "No image"}), 400
    if file:
        filename: str = request.args["id"] + '.png'
        file.save(str(Path(app.config['UPLOAD_FOLDER']) / filename))
        return jsonify({"detail": "Uploaded"}), 200
  
@app.route('/stripe/checkout', methods=['GET'])
@cross_origin(origin='*')
def stripe_checkout_create():
    cur = conn.cursor()
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    cur.execute('SELECT id FROM carts WHERE userid = {0} AND paid = \'N\''.format(getUserId(token)))
    res = cur.fetchall()
    currentCart = res[0][0]
    cur.execute('SELECT products.id, name, description, quantity, case when discount = 0 then CAST(price AS decimal(12,2)) when discount_type = \'P\' then CAST(price*(1-(discount*0.01)) AS decimal(12,2)) else CAST(price-discount AS decimal(12,2)) end as fprice FROM cart_entries, products WHERE products.id = productid and cartid = {0} ORDER BY cart_entries.id DESC'.format(currentCart))
    res = cur.fetchall()
    line_items = []
    for item in res:
        line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": item[1],
                        "description": item[2],
                        "images": ["http://l0nk5erver.duckdns.org:5000/products/img/{0}.png".format(item[0])]
                    },
                    "unit_amount": ("%.2f" % item[4]).replace('.', '')
                }, 
                "quantity": item[3]
            }
        )
    print(line_items)
    vip = isVip(token)
    userid = getUserId(token)
    token = token_urlsafe()
    cur.execute('INSERT INTO purchase_confirmations (token, cartid, vip, userid, confirmed) VALUES (\'{0}\', {1}, \'{2}\', {3}, \'N\')'.format(token, currentCart, 'Y' if vip else 'N', userid))
    conn.commit()
    if vip:
        checkout = client.checkout.sessions.create(params = 
                                        {
                                            "success_url":"http://l0nk5erver.duckdns.org:5000/stripe/confirm?t={0}".format(token),
                                            "line_items": line_items,
                                            "mode":"payment",
                                            "locale": "es",
                                            "discounts": [{"coupon": "68wVLueJ"}]
                                        })
    else: 
        checkout = client.checkout.sessions.create(params = 
                                        {
                                            "success_url":"http://l0nk5erver.duckdns.org:5000/stripe/confirm?t={0}".format(token),
                                            "line_items": line_items,
                                            "mode":"payment",
                                            "locale": "es",
                                        })
    cur.close()
    insertBitacora(getUserId(request.headers.get('Authorization').split()[1]), "Inició el pago de su carrito.", request.remote_addr) 
    return jsonify({"url": checkout["url"]})

@app.route('/stripe/confirm', methods=['GET'])
@cross_origin(origin='*')
def stripe_checkout_confirm():
    if "t" not in request.args: return jsonify({"detail": "Insufficient arguments"})
    cur = conn.cursor()
    cur.execute('SELECT cartid, vip, userid, confirmed FROM purchase_confirmations WHERE token = \'{0}\''.format(request.args["t"]))
    res = cur.fetchall()
    if res[0][3] == 'Y': 
        print("Already confirmed")
        return redirect("http://l0nk5erver.duckdns.org/purchases")
    currentCart = res[0][0]
    vip = res[0][1]
    userid = res[0][2]
    cur.execute('''
                insert into purchases (cartid, total_paid, vip) 
                SELECT carts.id, 
                sum(
                    case 
                        when discount = 0 then CAST(price*quantity AS decimal(12,2)) 
                        when discount_type = 'P' then CAST((price*(1-(discount*0.01)))*quantity AS decimal(12,2)) 
                        else CAST((price-discount)*quantity AS decimal(12,2)) 
                    end) as tprice, '{1}' 
                from products, cart_entries, carts where 
                    products.id = productid and 
                    deleted = 'N' and 
                    cartid = carts.id and 
                    carts.id = {0} group by carts.id;
        '''.format(currentCart, vip))
    cur.execute('''
                insert into purchased (purchaseid, productid, name, brand, price, dprice, quantity, fprice) 
                    select 
                        (select id from purchases where cartid = {0} group by id) as purchaseid, 
                        products.id, name, brand, price, 
                        case 
                            when discount = 0 then CAST(price AS decimal(12,2)) 
                            when discount_type = 'P' then CAST(price*(1-(discount*0.01)) AS decimal(12,2)) 
                            else CAST(price-discount AS decimal(12,2)) 
                        end as dprice, quantity,
                        case 
                            when discount = 0 then CAST(price*quantity AS decimal(12,2)) 
                            when discount_type = 'P' then CAST((price*(1-(discount*0.01)))*quantity AS decimal(12,2)) 
                            else CAST((price-discount)*quantity AS decimal(12,2)) 
                        end as fprice 
                        from products, cart_entries where 
                        products.id = cart_entries.productid and 
                        products.deleted = 'N' and cart_entries.cartid = {0};
        '''.format(currentCart))
    cur.execute('select userid from carts where id = {0}'.format(currentCart))
    res = cur.fetchall()
    userid = res[0][0]
    cur.execute('update purchase_confirmations set confirmed = \'Y\' where token = \'{0}\''.format(request.args["t"]))
    cur.execute('update carts set paid = \'Y\' where id = {0};'.format(currentCart))
    cur.execute('insert into carts (userid) values ({0});'.format(userid))
    conn.commit()
    insertBitacora(userid, "Finalizó el pago de su carrito.", request.remote_addr) 
    return redirect("http://l0nk5erver.duckdns.org/purchases")

@app.route('/admin/bitacora', methods=['GET'])
@cross_origin(origin="*")
def bitacora():
    cur = conn.cursor()
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token): return jsonify({"detail": "Invalid token"}), 400
    if not adminVerify(token): return jsonify({"detail": "Unauthorized"}), 400
    bitacora = []
    cur.execute('select * from bitacora order by id desc')
    res = cur.fetchall()
    for item in res:
        bitacora.append({
            "username": item[1],
            "role": item[2],
            "email": item[3],
            "action": item[4],
            "ip": item[5],
            "datetime": item[6],
        })
    return jsonify(bitacora), 200
    
@app.route('/facturas/<n>', methods=['GET'])
@cross_origin(origin="*")
def facturas(n): 
    pdf = pdfkit.from_string(htmlhelper.factura(n), False)
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename=output.pdf"
    return response
    
@app.route('/reportes/<base>/<criteria>/<order>/<since>/<until>/<format>', methods=['GET'])
@cross_origin(origin="*")
def reportes(base, criteria, order, since, until, format): 
    if base == 'products':
        query = '''
                select products.id, products.name, products.brand, products.price, 
                case 
                    when products.discount = 0 then products.discount 
                    when products.discount_type = 'P' then CAST(products.price*(products.discount*0.01) AS decimal(12,2)) 
                    else CAST(products.discount AS decimal(12,2)) 
                end as discounted, 
                case 
                    when products.discount = 0 then CAST(products.price AS decimal(12,2)) 
                    when products.discount_type = 'P' then CAST(products.price*(1-(products.discount*0.01)) AS decimal(12,2)) 
                    else CAST(products.price-products.discount AS decimal(12,2)) 
                end as final, products.stock, sum(quantity) as units_sold,
                cast(sum( case when purchases.vip = 'N' then fprice else fprice*0.85 end) as decimal(12,2)) as earnings
                from products, purchased, purchases 
                where deleted = 'N' and purchased.productid = products.id and purchases.id = purchaseid 
                and paid_on >= '{1}' and paid_on <= '{2}' group by products.id order by {0} {3};
                '''.format(criteria, since, until, order)
        return reportehelper.reportes('PRODUCTOS', query, ['ID', 'Nombre', 'Marca', 'Precio', 'Descuento', 'Precio final', 'stock', 'Ventas', 'Ganancias'], format)
    if base == 'users':
        query = '''
                select users.id, users.name, users.lname, users.email, users.role, users.country, users.state, users.address, 
                (select count(*) from (select userid from deliveryassignment, purchases where userid = users.id and purchaseid = purchases.id and paid_on >= '{1}' and paid_on <= '{2}' group by userid, purchaseid)) as deliveries_taken,
                (select count(*) from (select userid from deliveryassignment, purchases where userid = users.id and purchaseid = purchases.id and purchases.delivery_status = 'Entregado' and paid_on >= '{1}' and paid_on <= '{2}' group by userid, purchaseid)) as deliveries_completed,
                (select count(*) from (select userid from purchases, carts where carts.id = cartid and userid = users.id and purchases.paid_on >= '{1}' and purchases.paid_on <= '{2}')) as orders_made,
                (select coalesce(sum(quantity), 0) from (select quantity from purchased, purchases, carts where carts.id = cartid and purchaseid = purchases.id and userid = users.id and purchases.paid_on >= '{1}' and purchases.paid_on <= '{2}')) as products_purchased,
                (select cast(coalesce(sum(spent), 0) as decimal(12,2)) from (select case when purchases.vip = 'N' then purchases.total_paid else purchases.total_paid*0.85 end as spent from purchased, purchases, carts where carts.id = cartid and purchaseid = purchases.id and userid = users.id and purchases.paid_on >= '{1}' and purchases.paid_on <= '{2}')) as money_spent
                from users where users.deleted = 'N' group by users.id order by {0} {3};
                '''.format(criteria, since, until, order)
        return reportehelper.reportes('USUARIOS', query, ['ID', 'Nombre', 'Apellido', 'e-mail', 'Rol', 'Pais', 'Estado/departamento', 'Direccion', 'Ordenes tomadas', 'Ordenes completadas', 'Pedidos', 'Compras', 'Monto gastado'], format)


if __name__ == '__main__':
    app.run(host='192.168.0.18', debug=True)