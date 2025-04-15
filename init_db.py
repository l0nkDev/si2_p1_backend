import psycopg2
import secrets

conn = psycopg2.connect(
        host="localhost",
        database="flask_db",
        user="sammy",
        password="password"
        )

cur = conn.cursor()

# Execute a command: this creates a new table
cur.execute('DROP TABLE IF EXISTS users;')
cur.execute('CREATE TABLE users (id serial PRIMARY KEY,'
                                 'email varchar (50) NOT NULL,'
                                 'password varchar (50) NOT NULL,'
                                 'name varchar (50) NOT NULL,'
                                 'lname varchar (50) NOT NULL,'
                                 'role varchar(10) NOT NULL,'
                                 'token varchar(50) NOT NULL,'
                                 'date_added date DEFAULT CURRENT_TIMESTAMP);'
                                 )

# Insert data into the table
token: str = secrets.token_urlsafe()
print(token)

cur.execute('INSERT INTO users (email, password, name, lname, role, token)'
            'VALUES (%s, %s, %s, %s, %s, %s)',
            ('raul@gmail.com',
             '123',
             'Raúl',
             'Farell',
             'admin',
             token)
            )


conn.commit()

cur.close()
conn.close()