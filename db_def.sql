DROP TABLE IF EXISTS users cascade;



CREATE TABLE users (id serial PRIMARY KEY,
                    email varchar (50) NOT NULL,
					password varchar (50) NOT NULL,
					name varchar (50) NOT NULL,
					lname varchar (50) NOT NULL,
					role varchar(10) NOT NULL,
					token varchar(50) NOT NULL,
					date_added date DEFAULT CURRENT_TIMESTAMP);
drop table users cascade;
select * from users;

CREATE TABLE products (id serial PRIMARY KEY,
                       name varchar(50) NOT NULL,
					   description text DEFAULT '',
					   price decimal(12,2) NOT NULL,
					   discount decimal(12,2) NOT NULL DEFAULT 0,
					   discount_type char(1) NOT NULL DEFAULT 'P',
					   stock integer DEFAULT 0,
					   date_added date DEFAULT CURRENT_TIMESTAMP);
drop table products cascade;
select * from products;
					   
CREATE TABLE carts (id serial PRIMARY KEY,
                    userid serial REFERENCES users(id) NOT NULL,
				    paid char(1) DEFAULT 'N',
				    paid_on date,
				    price_paid decimal(12,2),
				    payment_method varchar(30)
				    );
drop table carts cascade;
select * from carts;

CREATE TABLE cart_entry (id serial PRIMARY KEY,
                         cartid serial REFERENCES carts(id) NOT NULL,
						 productid serial REFERENCES products(id) NOT NULL,
						 quantity integer DEFAULT 0
						 );
select * from products;
insert into products ()