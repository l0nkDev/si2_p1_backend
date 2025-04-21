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
select * from deliveryassignment;

CREATE TABLE bitacora (id serial PRIMARY KEY,
						username text NOT NULL,
						role varchar(50) not null,
						email text not null,
						action text NOT NULL,
						ip text NOT NULL,
						datetime timestamp DEFAULT CURRENT_TIMESTAMP);
drop table bitacora;
select * from bitacora;

CREATE TABLE purchase_confirmations(id serial PRIMARY KEY,
					                token varchar(50) NOT NULL,
									 cartid serial REFERENCES carts(id) NOT NULL,
									 userid serial REFERENCES users(id) NOT NULL,
									 vip varchar(1) NOT NULL,
									 confirmed varchar(1) NOT NULL);
drop table purchase_confirmations;
select * from purchase_confirmations;

create table fcm(id serial primary key,
			     userid serial references users(id) not null,
				 token varchar(255) not null);
drop table fcm;
select * from fcm;

select * from logs;


select users.id, users.name, users.lname, users.email, users.role, users.country, users.state, users.address, 
                (select count(*) from (select userid from deliveryassignment, purchases where userid = users.id and purchaseid = purchases.id group by userid, purchaseid)) as deliveries_taken,
                (select count(*) from (select userid from deliveryassignment, purchases where userid = users.id and purchaseid = purchases.id and purchases.delivery_status = 'Entregado' group by userid, purchaseid)) as deliveries_completed,
                (select count(*) from (select userid from purchases, carts where carts.id = cartid and userid = users.id)) as orders_made,
                (select coalesce(sum(quantity), 0) from (select quantity from purchased, purchases, carts where carts.id = cartid and purchaseid = purchases.id and userid = users.id )) as products_purchased,
                (select cast(coalesce(sum(spent), 0) as decimal(12,2)) from (select case when purchases.vip = 'N' then purchases.total_paid else purchases.total_paid*0.85 end as spent from purchased, purchases, carts where carts.id = cartid and purchaseid = purchases.id and userid = users.id)) as money_spent
                from users where users.deleted = 'N' group by users.id order by money_spent;

select userid, purchaseid from deliveryassignment where userid = 1 group by userid, purchaseid;
