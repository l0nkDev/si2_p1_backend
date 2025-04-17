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
    if not requestVerify(['email', 'password', 'name', 'lname'], request):
        return jsonify({"detail": "Insufficient arguments"}), 400
    cur.execute('SELECT email FROM users WHERE email = \'{0}\' AND deleted = \'N\''.format(request.json["email"]))
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
    cur.execute('SELECT id FROM users WHERE email = \'{0}\' AND deleted = \'N\''.format(json["email"]))
    res = cur.fetchall()
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
    cur.execute('SELECT id, email, name, lname, role FROM users WHERE token = \'{0}\' AND deleted = \'N\''.format(token))
    res = cur.fetchall()
    return jsonify({
        "email": res[0][1],
        "id": res[0][0],
        "name": res[0][2],
        "lname": res[0][3],
        "role": res[0][4],
        }), 200 

@app.route('/products', methods=['GET'])
@cross_origin(origin="*")
def prod():
    cur = conn.cursor() 
    prods = []
    page = 0
    if ("page" in request.args): page = request.args["page"]
    cur.execute('SELECT * FROM products WHERE deleted = \'N\' ORDER BY id DESC limit 20 offset 20*{0}'.format(page))
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
            "brand": prod[2]
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
    cur.execute('''SELECT *, ts_rank(to_tsvector('spanish', name || ' ' || coalesce(description, '')), websearch_to_tsquery('spanish', '{1}')) as rank
                   FROM products WHERE deleted = 'N' AND to_tsvector('spanish', name || ' ' || coalesce(description, '')) @@ websearch_to_tsquery('spanish', '{1}') ORDER BY rank DESC limit 20 offset 20*{0}'''.format(page, request.args["q"]))
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
            "brand": prod[2]
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
        cur2.execute('SELECT id, name, description, price, discount, discount_type, stock, date_added, brand FROM products WHERE id = {0} AND deleted = \'N\''.format(item[2]))
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
            "brand": res2[0][8]
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
    cur.execute('UPDATE products SET name = \'{1}\', brand = \'{2}\', description = \'{3}\', price = {4}, discount = {5}, discount_type = \'{6}\', stock = {7} WHERE id = {0}'.format(request.json["id"], request.json["name"], request.json["brand"], request.json["description"], request.json["price"], request.json["discount"], request.json["discount_type"], request.json["stock"]))
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
    cur.execute('INSERT INTO products (name, brand, description, price, discount, discount_type, stock) VALUES (\'{0}\', \'{1}\', \'{2}\', {3}, {4}, \'{5}\', {6})'.format(request.json["name"], request.json["brand"], request.json["description"], request.json["price"], request.json["discount"], request.json["discount_type"], request.json["stock"]))
    conn.commit()
    return jsonify({"detail": "Inserted"}), 200

@app.route('/users/cart/remove', methods=['DELETE'])
@cross_origin(origin="*")
def cart_entry_delete():
    cur = conn.cursor()
    try: token: str = request.headers.get('Authorization').split()[1]
    except: return jsonify({"detail": "No token"}), 400
    if not authVerify(token):
        return jsonify({"detail": "Invalid token"}), 400
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
    cur.execute('SELECT id FROM users WHERE email = \'{0}\''.format(request.json["email"]))
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
                .format(request.json["name"], request.json["lname"], request.json["email"], request.json["role"], request.json["country"], request.json["address"], request.json["state"], request.json["id"], request.json["password"]))
    conn.commit()
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
                insert into purchases (cartid, total_paid) 
                SELECT carts.id, 
                sum(
                    case 
                        when discount = 0 then CAST(price*quantity AS decimal(12,2)) 
                        when discount_type = 'P' then CAST((price*(1-(discount*0.01)))*quantity AS decimal(12,2)) 
                        else CAST((price-discount)*quantity AS decimal(12,2)) 
                    end) as tprice 
                from products, cart_entries, carts where 
                    products.id = productid and 
                    deleted = 'N' and 
                    cartid = carts.id and 
                    carts.id = {0} group by carts.id;
        '''.format(currentCart))
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
    cur.execute('SELECT purchases.*, purchased.* from purchased, purchases, carts where purchaseid = purchases.id and cartid = carts.id and userid = {0} order by purchases.id desc'.format(getUserId(token)))
    res = cur.fetchall()
    if len(res) == 0: return jsonify({"detail": "No purchases"}), 400
    purchases = []
    id = res[0][0]
    paid_on: str = res[0][2]
    total_paid = res[0][3]
    payment_method = res[0][4]
    delivery_status = res[0][5]
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
                    "items": purchase
                }
            )
            id = entry[0]
            paid_on = entry[2]
            total_paid = entry[3]
            payment_method = entry[4]
            delivery_status = entry[5] 
            purchase = []
        purchase.append(
            {
                "id": entry[6],
                "productid": entry[8],
                "name": entry[9],
                "brand": entry[10],
                "price": entry[11],
                "dprice": entry[12],
                "quantity": entry[13],
                "fprice": entry[14]
            }
        )
    purchases.append(
        {
            "id": id,
            "paid_on": paid_on,
            "total_paid": total_paid,
            "payment_method": payment_method,
            "delivery_status": delivery_status,
            "items": purchase
        }
    )
    return jsonify(purchases), 200


if __name__ == '__main__':
    app.run(host='192.168.0.18', debug=True)