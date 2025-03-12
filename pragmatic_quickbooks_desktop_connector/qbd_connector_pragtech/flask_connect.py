from flask import Flask, request

from connection import connection,connect_to_qbd,close_connection_to_qbd
from accounts import accounts
from customer import customer
from products import products
from sale_order import sale_order
from invoice import invoice
from payment_methods import payment_methods
from payments import payments
from vendor import vendor
from purchase_order import purchase_order
from essential import essential
from credit_memo import credit_memo
from billofmaterial import bom

from sales_rep import sales_rep

import json

app = Flask(__name__)
app.register_blueprint(connection)
app.register_blueprint(accounts)
app.register_blueprint(customer)
app.register_blueprint(products)
app.register_blueprint(sale_order)
app.register_blueprint(invoice)
app.register_blueprint(payment_methods)
app.register_blueprint(payments)
app.register_blueprint(vendor)
app.register_blueprint(purchase_order)
app.register_blueprint(essential)
app.register_blueprint(credit_memo)

app.register_blueprint(sales_rep)
app.register_blueprint(bom)

@app.route('/')
def home():
    return ("Thanks To Team Pragmatic")

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0',port=6088, threaded=False)    

# cn = pyodbc.connect('DSN=QuickBooks Data;')
# print ("-----------------Data",cn)

# cursor = cn.cursor()
# cursor.execute("Update Customer set Name='Sun Rooom' where Name='Sun Room'")
# cursor.execute("SELECT Name FROM Customer")
# for row in cursor.fetchall():
# 	row_as_list = [x for x in row]
# 	if row_as_list[0] == "Sun Rooom":
# 		print(row_as_list)
# #print (type(row))
# cursor.close()
# cn.close() 
