from flask import Blueprint, request
from connection import connect_to_qbd, close_connection_to_qbd
import logging
import json
logging.basicConfig(level=logging.DEBUG)

bom = Blueprint('bom', __name__, template_folder='templates')

@bom.route('/QBD/import/BOM')
def import_QBD_Bom():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        qbd_id = request.args.get('qbd_id')

        query = "SELECT ListID, Name, IsActive, ItemDesc, ItemGroupLineItemRefListID, ItemGroupLineItemRefFullName,ItemGroupLineQuantity  from ItemGroupLine where ListID='{}'".format(qbd_id)
        cursor.execute(query)

        bom_data = {'bom_id': qbd_id, 'bom_lines': []}

        for row in cursor.fetchall():
            data_dict = {}
            data_dict['ListID'] = row[0]
            data_dict['Name'] = row[1]
            data_dict['IsActive'] = row[2]
            data_dict['ItemDesc'] = row[3]
            data_dict['ItemGroupLineItemRefListID'] = row[4]
            data_dict['ItemGroupLineItemRefFullName'] = row[5]
            data_dict['ItemGroupLineQuantity'] = str(row[6])

            bom_data['bom_lines'].append(data_dict)
        
        cursor.close()
        close_connection_to_qbd(con)
        return json.dumps(bom_data)
    except Exception as ex:
        return json.dumps({'error': str(ex)})