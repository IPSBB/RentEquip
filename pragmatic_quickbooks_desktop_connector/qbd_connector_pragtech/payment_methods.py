from flask import Blueprint, request
from connection import connect_to_qbd, close_connection_to_qbd
import logging
import json

logging.basicConfig(level=logging.DEBUG)

payment_methods = Blueprint('payment_methods', __name__, template_folder='templates')

'''
TPA - Third Party Application
'''


@payment_methods.route('/QBD/import_payments_method')
def import_QBD_payments_method_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        if request.args['fetch_record'] == 'all':
            cursor.execute("SELECT ListId,Name from PaymentMethod")

        # elif request.args['fetch_record'] == 'one':
        #     ListId = request.args['quickbooks_id']
        #     cursor.execute("SELECT ListId, ParentRefListId, FullName, Email, Phone, AltPhone, Fax, Notes, BillAddressAddr1, BillAddressAddr2, BillAddressCountry, BillAddressState, BillAddressCity, BillAddressPostalCode FROM Customer Where ListID='"+ListId+"' Order by ListId ASC")

        odoo_payment_method_list = []

        for row in cursor.fetchall():
            row_as_list = [x for x in row]
            odoo_payment_method_dict = {}

            odoo_payment_method_dict['payment_type'] = row_as_list[1]
            odoo_payment_method_dict['quickbooks_id'] = row_as_list[0]

            odoo_payment_method_list.append(odoo_payment_method_dict)

        # print (odoo_payment_method_list)

        cursor.close()
        return (json.dumps(odoo_payment_method_list))

    except Exception as e:
        # print (e)
        data = 0
        return ({"Status": 404, "Message": "Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])
