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
					   date_added date DEFAULT CURRENT_TIMESTAMP,
					   stripeid text default '');
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
				    	delivery_status varchar(30) DEFAULT 'Procesando...',
						vip varchar(1) default 'N'
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

CREATE TABLE productrating (id serial PRIMARY KEY,
							 userid serial REFERENCES users(id) NOT NULL,
							 productid serial REFERENCES products(id) NOT NULL,
							 rating decimal(2,1) NOT NULL
                            );

CREATE TABLE deliveryrating (id serial PRIMARY KEY,
							 userid serial REFERENCES users(id) NOT NULL,
							 purchaseid serial REFERENCES purchases(id) NOT NULL,
							 rating decimal(2,1) NOT NULL
                            );

CREATE TABLE deliveryassignment (id serial PRIMARY KEY,
							      userid serial REFERENCES users(id) NOT NULL,
							      purchaseid serial REFERENCES purchases(id) NOT NULL
                                 );

CREATE TABLE bitacora (id serial PRIMARY KEY,
						username text NOT NULL,
						user role varchar(50) not null,
						user email text not null,
						action text NOT NULL,
						ip text NOT NULL,
						datetime timestamp DEFAULT CURRENT_TIMESTAMP);
drop table bitacora;

CREATE TABLE purchase_confirmations(id serial PRIMARY KEY,
					                token varchar(50) NOT NULL,
									 cartid serial REFERENCES carts(id) NOT NULL,
									 userid serial REFERENCES users(id) NOT NULL,
									 vip varchar(1) NOT NULL,
									 confirmed varchar(1) NOT NULL);
drop table purchase_confirmations;
select * from purchase_confirmations;

SELECT products.id, name, description, quantity, case when discount = 0 then CAST(price AS decimal(12,2)) when discount_type = 'P' then CAST(price*(1-(discount*0.01)) AS decimal(12,2)) else CAST(price-discount AS decimal(12,2)) end as fprice FROM cart_entries, products WHERE products.id = productid and cartid = 36 ORDER BY cart_entries.id DESC;

select users.* from users where users.id not in (select userid from carts) and deleted = 'N';

insert into productrating (userid, productid, rating) values (3, 1, 3.5);
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