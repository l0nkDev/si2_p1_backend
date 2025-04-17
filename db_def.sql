DROP TABLE IF EXISTS users cascade;



CREATE TABLE users (id serial PRIMARY KEY,
                    email varchar (50) NOT NULL,
					password varchar (50) NOT NULL,
					name varchar (50) NOT NULL,
					lname varchar (50) NOT NULL,
					role varchar(10) NOT NULL,
					token varchar(50) NOT NULL,
					date_added date DEFAULT CURRENT_TIMESTAMP,
					country varchar(50) DEFAULT '',
					state varchar(50) DEFAULT '',
					address text DEFAULT '',
					deleted varchar(1) DEFAULT 'N'
					);
drop table users cascade;
select * from users;

CREATE TABLE products (id serial PRIMARY KEY,
                       name varchar(100) NOT NULL,
                       brand varchar(100) NOT NULL,
					   description text DEFAULT '',
					   price decimal(12,2) NOT NULL,
					   discount decimal(12,2) NOT NULL DEFAULT 0,
					   discount_type char(1) NOT NULL DEFAULT 'P',
					   stock integer DEFAULT 0,
					   deleted varchar(1) DEFAULT 'N',
					   date_added date DEFAULT CURRENT_TIMESTAMP);
drop table products cascade;
select * from products;

update products set name = 'Nintendo Switch', brand = 'Nintendo' WHERE id = 1;
					   
CREATE TABLE carts (id serial PRIMARY KEY,
                    userid serial REFERENCES users(id) NOT NULL,
				    paid char(1) DEFAULT 'N',
				    paid_on date,
				    price_paid decimal(12,2),
				    payment_method varchar(30)
				    );
drop table carts cascade;
select * from carts;

CREATE TABLE cart_entries (id serial PRIMARY KEY,
                         cartid serial REFERENCES carts(id) NOT NULL,
						 productid serial REFERENCES products(id) NOT NULL,
						 quantity integer DEFAULT 1
						 );
drop table cart_entries cascade;
select * from cart_entries;

CREATE TABLE purchases (id serial PRIMARY KEY,
                        cartid serial REFERENCES carts(id) NOT NULL,
				        paid_on timestamp DEFAULT CURRENT_TIMESTAMP,
				        total_paid decimal(12,2),
				        payment_method varchar(30) DEFAULT 'Stripe',
				    	delivery_status varchar(30) DEFAULT 'Procesando...'
				        );
drop table purchases cascade;
select * from purchases;

CREATE TABLE purchased (id serial PRIMARY KEY,
                        purchaseid serial REFERENCES purchases(id),
						productid serial REFERENCES products(id),
                        name varchar(100) NOT NULL,
                        brand varchar(100) NOT NULL,
					    price decimal(12,2) NOT NULL,
					    dprice decimal(12,2) NOT NULL,
						quantity integer NOT NULL,
					    fprice decimal(12,2) NOT NULL);
drop table purchased cascade;
select * from purchased;

SELECT *, ts_rank(to_tsvector('spanish', name || ' ' || coalesce(description, '')), websearch_to_tsquery('spanish', 'Consola')) as rank
FROM products WHERE deleted = 'N' AND to_tsvector('spanish', name || ' ' || coalesce(description, '')) @@ websearch_to_tsquery('spanish', 'Consola') ORDER BY rank DESC limit 20 offset 0;

SELECT purchases.*, purchased.* from purchased, purchases, carts where purchaseid = purchases.id and cartid = carts.id and userid = 1 order by purchases.id desc;

insert into products (name, brand, description, price) VALUES ('Nintendo Switch', 'Nintendo', 'Consola de videojuegos', 300);
insert into products (name, brand, description, price) VALUES ('Nintendo Switch Lite', 'Nintendo', 'Consola de videojuegos', 250);
insert into products (name, brand, description, price) VALUES ('Nintendo Switch OLED', 'Nintendo', 'Consola de videojuegos', 350);
insert into products (name, brand, description, price) VALUES ('Nintendo Switch 2', 'Nintendo', 'Consola de videojuegos', 450);
insert into products (name, brand, description, price) VALUES ('Nintendo Switch 2 + Mario Kart World', 'Nintendo', 'Consola de videojuegos', 500);
insert into products (name, brand, description, price) VALUES ('Mario Kart World (S2)', 'Nintendo', 'Videojuegos', 80);
insert into products (name, brand, description, price) VALUES ('Donkey Kong Bananza (S2)', 'Nintendo', 'Videojuegos', 70);
insert into products (name, brand, description, price) VALUES ('The Legend of Zelda: Tears of the Kingdom (Switch)', 'Nintendo', 'Videojuegos', 70);
insert into products (name, brand, description, price) VALUES ('The Legend of Zelda: Breath of the Wild (Switch)', 'Nintendo', 'Videojuegos', 60);
insert into products (name, brand, description, price) VALUES ('Super Smash Bros. Ultimate (Switch)', 'Nintendo', 'Videojuegos', 300);