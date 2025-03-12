from flask import Blueprint, request
from connection import connect_to_qbd, close_connection_to_qbd
import logging
import json
logging.basicConfig(level=logging.DEBUG)

products = Blueprint('products', __name__, template_folder='templates')

'''
TPA - Third Party Application
'''


@products.route('/QBD/import_product_quantities', methods=['POST'])
def import_QBD_product_quantities():
    '''
        Create Inventory adjustment lines against product for
        updating product quantities
    '''
    try:

        data = connect_to_qbd()
        con = data[0]

        cursor = con.cursor()
        count = 0
        product_ids = request.get_json(force=True)

        for product_id in product_ids:
            count += 1
            if count == len(product_ids):
                save_to_cache = 0
            else:
                save_to_cache = 1

            # PREPARE QUERY
            formatted_date = "{d '" + product_id.get('TxnDate') + "'}"
            insert_query = "INSERT INTO InventoryAdjustmentLine (AccountRefListID, TxnDate, RefNumber, Memo, InventoryAdjustmentLineItemRefListID, InventoryAdjustmentLineQuantityAdjustmentNewQuantity, FQSaveToCache) VALUES ('{}', {}, '{}', '{}', '{}', {}, {})".format(
                product_id.get('AccountRefListID'),
                formatted_date,
                product_id.get('RefNumber'),
                product_id.get('Memo'),
                product_id.get('InventoryAdjustmentLineItemRefListID'),
                product_id.get(
                    'InventoryAdjustmentLineQuantityAdjustmentNewQuantity'),
                0)
            logging.info("INSERT QUERY IS {}".format(insert_query))
            try:
                cursor.execute(insert_query)
                logging.info("QTY UPDATED !!!")
            except Exception as ex:
                print("EXCEPTION !!!!{}".format(str(ex)))
                continue

        # IF ALL GOES GOOD THEN RETURN SUCCESS RESPONSE
        cursor.close()
        return ({"status": 200, "message": "Inventory Adjustment created"})

    except Exception as ex:
        logging.error(
            "ERROR IN import_qbd_product_quantities {}".format(str(ex)))
        return ({"status": 201, "message": "Inventory Adjustment not created, {}".format(str(ex))})
    finally:
        if data != 0:
            close_connection_to_qbd(data[0])


@products.route('/QBD/import_products')
def import_QBD_Products_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        to_execute_account = int(request.args.get('to_execute_account'))
        limit = request.args.get('limit')
        if limit:
            limit = int(limit)
        list_id = request.args.get('list_id')

        if request.args.get('inventory_adjustment'):
            if to_execute_account == 1:
                products = "SELECT TOP {} ListId, Type, Description, Name, IsActive, SalesOrPurchaseDesc, SalesDesc, PurchaseDesc, ManufacturerPartNumber, PurchaseCost, SalesOrPurchasePrice, SalesPrice, IncomeAccountRefListID, SalesTaxCodeRefFullName, SalesOrPurchaseAccountRefListID, IncomeAccountRefListID ,TimeModified, QuantityOnHand FROM item where Type in ('ItemNonInventory','ItemInventory') Order by TimeModified ASC".format(
                    limit)
                cursor.execute(products)
            elif to_execute_account == 2:
                products = "SELECT TOP {} ListId, Type, Description, Name, IsActive, SalesOrPurchaseDesc, SalesDesc, PurchaseDesc, ManufacturerPartNumber, PurchaseCost, SalesOrPurchasePrice, SalesPrice, IncomeAccountRefListID, SalesTaxCodeRefFullName, SalesOrPurchaseAccountRefListID, IncomeAccountRefListID ,TimeModified, QuantityOnHand  FROM item where Type in ('ItemNonInventory','ItemInventory')".format(
                    limit)
                cursor.execute(products)
            elif to_execute_account == 3:
                if request.args.get('list_id'):
                    products = f"SELECT ListId, Type, Description, Name, IsActive, SalesOrPurchaseDesc, SalesDesc, PurchaseDesc, ManufacturerPartNumber, PurchaseCost, SalesOrPurchasePrice, SalesPrice, IncomeAccountRefListID, SalesTaxCodeRefFullName, SalesOrPurchaseAccountRefListID, IncomeAccountRefListID ,TimeModified FROM item where ListID='{list_id}'"
                    cursor.execute(products)
        else:
            if to_execute_account == 1:
                products = "SELECT TOP {} ListId, Type, Description, Name, IsActive, SalesOrPurchaseDesc, SalesDesc, PurchaseDesc, ManufacturerPartNumber, PurchaseCost, SalesOrPurchasePrice, SalesPrice, IncomeAccountRefListID, SalesTaxCodeRefFullName, SalesOrPurchaseAccountRefListID, IncomeAccountRefListID ,TimeModified FROM item where Type in ('ItemNonInventory','ItemInventory','ItemService','ItemGroup','ItemInventoryAssembly','ItemFixedAsset') Order by TimeModified ASC".format(
                    limit)
                cursor.execute(products)
            elif to_execute_account == 2:
                time_modified = "{ts'" + \
                    str(request.args.get('last_qbd_id'))+"'}"
                # print (time_modified)
                products = "SELECT TOP {} ListId, Type, Description, Name, IsActive, SalesOrPurchaseDesc, SalesDesc, PurchaseDesc, ManufacturerPartNumber, PurchaseCost, SalesOrPurchasePrice, SalesPrice, IncomeAccountRefListID, SalesTaxCodeRefFullName, SalesOrPurchaseAccountRefListID, IncomeAccountRefListID ,TimeModified FROM item where Type in ('ItemNonInventory','ItemInventory','ItemService','ItemGroup','ItemInventoryAssembly','ItemFixedAsset') and timemodified >={}".format(
                    limit, time_modified)
                cursor.execute(products)
            elif to_execute_account == 3:
                if request.args.get('list_id'):
                    products = f"SELECT ListId, Type, Description, Name, IsActive, SalesOrPurchaseDesc, SalesDesc, PurchaseDesc, ManufacturerPartNumber, PurchaseCost, SalesOrPurchasePrice, SalesPrice, IncomeAccountRefListID, SalesTaxCodeRefFullName, SalesOrPurchaseAccountRefListID, IncomeAccountRefListID ,TimeModified FROM item where ListID='{list_id}'"
                    cursor.execute(products)

        print("PRODUCTS=======================",products)
# 0ListId
# 1Type
# 2Description
# 3Name
# 4IsActive
# 5SalesOrPurchaseDesc
# 6SalesDesc
# 7PurchaseDesc
# 8ManufacturerPartNumber
# 9PurchaseCost
# 10SalesOrPurchasePrice
# 11SalesPrice
# QuantityOnHand ## Removed Becoz of HY111 Error
# 12IncomeAccountRefListID
# 13SalesTaxCodeRefFullName
# 14SalesOrPurchaseAccountRefListID
# 15IncomeAccountRefListID
# 16TimeModified
        odoo_product_list = []
        for row in cursor.fetchall():

            odoo_product_dict = {}
            row_as_list = [x for x in row]
            if row_as_list[1] == 'ItemInventoryAssembly':
                if row_as_list[3]:
                    odoo_product_dict['name'] = row_as_list[3]
                else:
                    odoo_product_dict['name'] = row_as_list[2]

                odoo_product_dict['full_name'] = row_as_list[6]
                odoo_product_dict['quickbooks_id'] = row_as_list[0]
                odoo_product_dict['default_code'] = row_as_list[8]
                odoo_product_dict['active'] = row_as_list[4]
                odoo_product_dict['tax_code'] = row_as_list[13]
                if (row_as_list[9]):
                        odoo_product_dict['standard_price'] = float(row_as_list[9])
                else:
                    odoo_product_dict['standard_price'] = 0.0
                if (row_as_list[11]):
                    odoo_product_dict['list_price'] = float(row_as_list[11])
                else:
                    odoo_product_dict['list_price'] = 0.0
                odoo_product_dict['description'] = row_as_list[2]
                odoo_product_dict['income_account_id'] = row_as_list[14]
                odoo_product_dict['barcode'] = ''
                odoo_product_dict['qty_available'] = 0.0
                odoo_product_dict['description_purchase'] = ''
                odoo_product_dict['last_time_modified'] = str(row_as_list[16])
                odoo_product_dict['type'] = 'service'
                odoo_product_dict['qbd_product_type'] = 'ItemInventoryAssembly'

            if row_as_list[1] == 'ItemGroup':
                if row_as_list[3]:
                    odoo_product_dict['name'] = row_as_list[3]
                else:
                    odoo_product_dict['name'] = row_as_list[2]

                odoo_product_dict['full_name'] = row_as_list[6]
                odoo_product_dict['quickbooks_id'] = row_as_list[0]
                odoo_product_dict['default_code'] = row_as_list[8]
                odoo_product_dict['active'] = row_as_list[4]
                odoo_product_dict['tax_code'] = row_as_list[13]
                odoo_product_dict['standard_price'] = 0.0
                if (row_as_list[5]):
                    odoo_product_dict['list_price'] = float(row_as_list[10])
                else:
                    odoo_product_dict['list_price'] = 0.0
                odoo_product_dict['description'] = row_as_list[2]
                odoo_product_dict['income_account_id'] = row_as_list[14]
                odoo_product_dict['barcode'] = ''
                odoo_product_dict['qty_available'] = 0.0
                odoo_product_dict['description_purchase'] = ''
                odoo_product_dict['last_time_modified'] = str(row_as_list[16])
                odoo_product_dict['type'] = 'service'
                odoo_product_dict['qbd_product_type'] = 'ItemGroup'

            if row_as_list[1] == 'ItemService':
                if row_as_list[3]:
                    odoo_product_dict['name'] = row_as_list[3]
                else:
                    odoo_product_dict['name'] = row_as_list[2]

                odoo_product_dict['full_name'] = row_as_list[6]
                odoo_product_dict['quickbooks_id'] = row_as_list[0]
                odoo_product_dict['default_code'] = row_as_list[8]
                odoo_product_dict['active'] = row_as_list[4]
                odoo_product_dict['tax_code'] = row_as_list[13]
                odoo_product_dict['standard_price'] = 0.0
                if (row_as_list[5]):
                    odoo_product_dict['list_price'] = float(row_as_list[10])
                else:
                    odoo_product_dict['list_price'] = 0.0
                odoo_product_dict['description'] = row_as_list[2]
                odoo_product_dict['income_account_id'] = row_as_list[14]
                odoo_product_dict['barcode'] = ''
                odoo_product_dict['qty_available'] = 0.0
                odoo_product_dict['description_purchase'] = ''
                odoo_product_dict['last_time_modified'] = str(row_as_list[16])
                odoo_product_dict['type'] = 'service'
                odoo_product_dict['qbd_product_type'] = 'ItemService'
            if row_as_list[1] == 'ItemFixedAsset':
                if row_as_list[3]:
                    odoo_product_dict['name'] = row_as_list[3]
                else:
                    odoo_product_dict['name'] = row_as_list[2]

                odoo_product_dict['full_name'] = row_as_list[6]
                odoo_product_dict['quickbooks_id'] = row_as_list[0]
                odoo_product_dict['barcode'] = ''
                odoo_product_dict['active'] = row_as_list[4]
                odoo_product_dict['tax_code'] = row_as_list[13]
                odoo_product_dict['standard_price'] = 0.0
                if (row_as_list[10]):
                    odoo_product_dict['list_price'] = float(row_as_list[10])
                else:
                    odoo_product_dict['list_price'] = 0.0
                odoo_product_dict['description'] = row_as_list[2]
                odoo_product_dict['income_account_id'] = row_as_list[14]
                odoo_product_dict['default_code'] = row_as_list[8]
                odoo_product_dict['qty_available'] = 0.0
                odoo_product_dict['description_purchase'] = ''
                odoo_product_dict['last_time_modified'] = str(row_as_list[16])
                odoo_product_dict['type'] = 'consu'
                odoo_product_dict['qbd_product_type'] = 'ItemFixedAsset'

            if row_as_list[1] == 'ItemNonInventory':
                # if row_as_list[17]:
                if len(row_as_list) >= 18:
                    odoo_product_dict['qty_available'] = float(row_as_list[17])
                if row_as_list[3]:
                    odoo_product_dict['name'] = row_as_list[3]
                else:
                    odoo_product_dict['name'] = row_as_list[2]

                odoo_product_dict['full_name'] = row_as_list[6]
                odoo_product_dict['quickbooks_id'] = row_as_list[0]
                odoo_product_dict['barcode'] = ''
                odoo_product_dict['active'] = row_as_list[4]
                odoo_product_dict['tax_code'] = row_as_list[13]
                odoo_product_dict['standard_price'] = 0.0
                if (row_as_list[10]):
                    odoo_product_dict['list_price'] = float(row_as_list[10])
                else:
                    odoo_product_dict['list_price'] = 0.0
                odoo_product_dict['description'] = row_as_list[2]
                odoo_product_dict['income_account_id'] = row_as_list[14]
                odoo_product_dict['default_code'] = row_as_list[8]
                # odoo_product_dict['qty_available'] = 0.0
                odoo_product_dict['description_purchase'] = ''
                odoo_product_dict['last_time_modified'] = str(row_as_list[16])
                odoo_product_dict['type'] = 'consu'
                odoo_product_dict['qbd_product_type'] = 'ItemNonInventory'

            if row_as_list[1] == 'ItemInventory':
                    # if row_as_list[17]:
                    if len(row_as_list) >= 18:
                        odoo_product_dict['qty_available'] = float(row_as_list[17])
                    if row_as_list[3]:
                        odoo_product_dict['name'] = row_as_list[3]
                    else:
                        odoo_product_dict['name'] = row_as_list[2]

                    odoo_product_dict['full_name'] = row_as_list[6]
                    odoo_product_dict['quickbooks_id'] = row_as_list[0]
                    odoo_product_dict['barcode'] = ''
                    odoo_product_dict['active'] = row_as_list[4]
                    odoo_product_dict['tax_code'] = row_as_list[13]
                    if (row_as_list[9]):
                        odoo_product_dict['standard_price'] = float(row_as_list[9])
                    else:
                        odoo_product_dict['standard_price'] = 0.0
                    if (row_as_list[11]):
                        odoo_product_dict['list_price'] = float(row_as_list[11])
                    else:
                        odoo_product_dict['list_price'] = 0.0
                    odoo_product_dict['description'] = row_as_list[2]
                    odoo_product_dict['income_account_id'] = row_as_list[15]
                    odoo_product_dict['default_code'] = row_as_list[8]
                    ### Commented this code becoz of HY111 Error ######
                    # if (row_as_list[12]):
                    #     odoo_product_dict['qty_available'] = float(row_as_list[12])
                    # else:
                    # odoo_product_dict['qty_available'] = 0.0
                    odoo_product_dict['description_purchase'] = row_as_list[7]
                    odoo_product_dict['last_time_modified'] = str(row_as_list[16])
                    odoo_product_dict['type'] = 'product'
                    odoo_product_dict['qbd_product_type'] = 'ItemInventory'
            if row_as_list[1] == 'ItemOtherCharge':

                    if row_as_list[3]:
                        odoo_product_dict['name'] = row_as_list[3]
                    else:
                        odoo_product_dict['name'] = row_as_list[2]

                    odoo_product_dict['full_name'] = row_as_list[6]
                    odoo_product_dict['quickbooks_id'] = row_as_list[0]
                    odoo_product_dict['barcode'] = ''
                    odoo_product_dict['active'] = row_as_list[4]
                    odoo_product_dict['tax_code'] = row_as_list[13]
                    if (row_as_list[9]):
                        odoo_product_dict['standard_price'] = float(row_as_list[9])
                    else:
                        odoo_product_dict['standard_price'] = 0.0
                    if (row_as_list[11]):
                        odoo_product_dict['list_price'] = float(row_as_list[11])
                    else:
                        odoo_product_dict['list_price'] = 0.0
                    odoo_product_dict['description'] = row_as_list[2]
                    odoo_product_dict['income_account_id'] = row_as_list[15]
                    odoo_product_dict['default_code'] = row_as_list[8]
                    ### Commented this code becoz of HY111 Error ######
                    # if (row_as_list[12]):
                    #     odoo_product_dict['qty_available'] = float(row_as_list[12])
                    # else:
                    odoo_product_dict['qty_available'] = 0.0
                    odoo_product_dict['description_purchase'] = row_as_list[7]
                    odoo_product_dict['last_time_modified'] = str(row_as_list[16])
                    odoo_product_dict['type'] = 'product'
                    odoo_product_dict['qbd_product_type'] = 'ItemOtherCharge'


            odoo_product_list.append(odoo_product_dict)

        print ("-------------odoo_product_list---------------",odoo_product_list)

        cursor.close()
        return (json.dumps(odoo_product_list))

    except Exception as e:
        logging.info("1")
        logging.warning(e)
        # print (e)
        data = 0
        return ({"Status": 404, "Message": "Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])


'''
TPA - Third Party Application
'''


@products.route('/QBD/export_products', methods=['POST'])
def export_TPA_products_to_QBD():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        req = request.get_json(force=True)
        logging.info("Request data is {}".format(req))
        # print (req)
        if 'products_list' in req:

            tpa_product_list = []
            for rec in req.get('products_list'):
                tpa_product_dict = {}
                # print (rec)

                # description_sale = rec.get('description_sale') # SalesAndPurchaseSalesDesc description_sale (varchar 4095)

                if rec.get('name'):
                    name = rec.get('name')  # Name name (varchar 31)
                else:
                    name = rec.get('description')  # Name name (varchar 31)

                # SalesOrPurchaseDesc,SalesDesc description
                description = rec.get('description')

                active = str(rec.get('active'))  # IsActive active (bit 1)

                if rec.get('barcode'):  # ManufacturerPartNumber barcode (varchar 31)
                    barcode = rec.get('barcode')
                else:
                    barcode = ''

                # PurchaseCost,SalesOrPurchasePrice sales_pruchase_price_and_purchase_cost
                if rec.get('sales_purchase_price_and_purchase_cost'):
                    sales_purchase_price_and_purchase_cost = float(
                        rec.get('sales_purchase_price_and_purchase_cost'))
                else:
                    sales_purchase_price_and_purchase_cost = 0.0

                if rec.get('sales_price'):  # SalesPrice sales_price
                    sales_price = rec.get('sales_price')
                else:
                    sales_price = 0.0

                # PurchaseDesc description_purchase
                description_purchase = rec.get('description_purchase')

                if rec.get('qty_available'):  # QuantityOnHand qty_available
                    qty_available = rec.get('qty_available')
                else:
                    qty_available = 0.0

                # IncomeAccountRefListID,SalesOrPurchaseAccountRefListID income_account_id
                income_account_id = rec.get(
                    'property_account_income_quickbook_id')

                # SalesTaxCodeRefFullName tax_code
                tax_code = rec.get('tax_code')

                is_update = 0

                if rec.get('product_qbd_id'):
                    quickbooks_id = rec.get('product_qbd_id')
                    is_update = 1

                qbAssetAccountId = ''  # qbAssetAccountId = varchar 36
                qbCOGSAccountId = ''  # qbCOGSAccountId = varchar 36

                if rec.get('type') == 'consu':
                    check_record = "Select Top 1 ListId from ItemNonInventory where Name='{}'".format(
                        name)
                elif rec.get('type') == 'product':
                    check_record = "Select Top 1 ListId from ItemInventory where Name='{}'".format(
                        name)
                elif rec.get('type') == 'service':
                    check_record = "Select Top 1 ListId from ItemService where Name='{}'".format(
                        name)

                cursor.execute(check_record)
                is_present = cursor.fetchone()

                if not is_present:

                    if rec.get('type') == 'consu':
                        if not is_update:
                            insertQuery = "Insert into ItemNonInventory (Name, IsActive, ManufacturerPartNumber, SalesTaxCodeRefFullName, SalesOrPurchasePrice, SalesOrPurchaseDesc, SalesOrPurchaseAccountRefListID) VALUES('{}', {}, '{}', '{}', {}, '{}', '{}')".format(
                                name, active, barcode, tax_code, sales_price, description, income_account_id)
                        # else:
                        #     updateQuery = "Update ItemNonInventory Set Name='{}', IsActive={}, ManufacturerPartNumber='{}', SalesTaxCodeRefFullName='{}', SalesOrPurchasePrice={}, SalesOrPurchaseDesc='{}', SalesOrPurchaseAccountRefListID='{}' Where ListId='{}'".format(name, active, barcode, tax_code, sales_price, description, income_account_id, quickbooks_id)

                    elif rec.get('type') == 'product':
                        # print ("Recccc",rec)
                        if 'asset_account_quickbook_id' in rec:
                            qbAssetAccountId = rec.get(
                                'asset_account_quickbook_id')
                        if 'cogs_account_quickbook_id' in rec:
                            qbCOGSAccountId = rec.get(
                                'cogs_account_quickbook_id')

                        # qbAssetAccountQuery = "SELECT ListID FROM Account WHERE Name = 'Inventory Asset'"
                        # cursor.execute(qbAssetAccountQuery)
                        # qbAssetAccountId = cursor.fetchone()[0]

                        # qbCOGSAccountQuery =  "SELECT ListID FROM Account WHERE Name = 'Cost of Goods Sold'"
                        # cursor.execute(qbCOGSAccountQuery)
                        # qbCOGSAccountId = cursor.fetchone()[0]

                        if qbAssetAccountId and qbCOGSAccountId:
                            if not is_update:
                                insertQuery = "INSERT INTO ItemInventory (Name, IsActive, ManufacturerPartNumber, SalesTaxCodeRefFullName, SalesPrice, SalesDesc, PurchaseCost, PurchaseDesc, IncomeAccountRefListID, AssetAccountRefListID, COGSAccountRefListID) VALUES ('{}', {}, '{}', '{}', {}, '{}', {}, '{}', '{}', '{}','{}')".format(
                                    name, active, barcode, tax_code, sales_price, description, sales_purchase_price_and_purchase_cost, description_purchase, income_account_id, qbAssetAccountId, qbCOGSAccountId)
                            # else:
                            #     updateQuery = "Update ItemInventory Set Name='{}', IsActive={}, ManufacturerPartNumber='{}', SalesTaxCodeRefFullName='{}', SalesPrice={}, SalesDesc='{}', PurchaseCost={}, PurchaseDesc='{}', IncomeAccountRefListID='{}', AssetAccountRefListID='{}', COGSAccountRefListID='{}' Where ListId='{}'".format(name, active, barcode, tax_code, sales_price, description, sales_purchase_price_and_purchase_cost, description_purchase, income_account_id, qbAssetAccountId, qbCOGSAccountId, quickbooks_id)

                    elif rec.get('type') == 'service':
                        if not is_update:
                            insertQuery = "INSERT INTO ItemService (Name, IsActive, SalesTaxCodeRefFullName, SalesOrPurchasePrice, SalesOrPurchaseDesc, SalesOrPurchaseAccountRefListID) VALUES ('{}', {}, '{}', {}, '{}', '{}')".format(
                                name, active, tax_code, sales_price, description, income_account_id)
                            
                        # else:
                        #     updateQuery = "Update ItemService Set Name='{}', IsActive={}, SalesTaxCodeRefFullName='{}', SalesOrPurchasePrice={}, SalesOrPurchaseDesc='{}', SalesOrPurchaseAccountRefListID='{}' Where ListId='{}'".format(name, active, tax_code, sales_price, description, income_account_id, quickbooks_id)

                try:
                    if not is_update:
                        if not is_present:
                            logging.info(
                                "Insert Query ----------------------------- ")
                            logging.info(insertQuery)
                            cursor.execute(insertQuery)
                            # print ("Recorddddddddddddd")

                            if rec.get('type') == 'consu':
                                # lastInserted ="Select Top 1 ListId from ItemNonInventory order by timecreated desc"
                                lastInserted = "Select Top 1 ListId from ItemNonInventory where Name='{}'".format(
                                    name)
                            elif rec.get('type') == 'product':
                                # lastInserted ="Select Top 1 ListId from ItemInventory order by timecreated desc"
                                lastInserted = "Select Top 1 ListId from ItemInventory where Name='{}'".format(
                                    name)
                            elif rec.get('type') == 'service':
                                # lastInserted ="Select Top 1 ListId from ItemService order by timecreated desc"
                                lastInserted = "Select Top 1 ListId from ItemService where Name='{}'".format(
                                    name)
                            cursor.execute(lastInserted)

                            record_id = cursor.fetchone()
                            logging.info(
                                "Last Inserted ----------------------------- ")
                            logging.info(lastInserted)
                            logging.info(record_id[0])

                            tpa_product_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_product_dict['quickbooks_id'] = record_id[0]
                            tpa_product_dict['message'] = 'Successfully Created'
                            tpa_product_list.append(tpa_product_dict)
                            cursor.commit()
                        else:
                            logging.info(
                                "Record Already Present in Quickbboks so updating id in Odoo ----------------------------- ")
                            logging.info(check_record)
                            logging.info(is_present[0])

                            tpa_product_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_product_dict['quickbooks_id'] = is_present[0]
                            tpa_product_dict['message'] = 'Quickbooks Id Successfully Added'
                            tpa_product_list.append(tpa_product_dict)
                            cursor.commit()
                    else:
                        # print ("Updateeeeeeeeeeeee -------------------------")
                        # print (updateQuery)
                        # cursor.execute(updateQuery)
                        tpa_product_dict['odoo_id'] = rec.get('odoo_id')
                        tpa_product_dict['quickbooks_id'] = rec.get(
                            'product_qbd_id')
                        tpa_product_dict['message'] = 'Successfully Updated'
                        tpa_product_list.append(tpa_product_dict)
                        cursor.commit()

                except Exception as e:
                    logging.info("1")
                    logging.warning(e)

                    if not is_update:
                        tpa_product_dict['odoo_id'] = rec.get('odoo_id')
                        tpa_product_dict['quickbooks_id'] = ''
                        tpa_product_dict['message'] = 'Error While Creating'
                        tpa_product_list.append(tpa_product_dict)
                    else:
                        tpa_product_dict['odoo_id'] = rec.get('odoo_id')
                        tpa_product_dict['quickbooks_id'] = rec.get(
                            'product_qbd_id')
                        tpa_product_dict['message'] = 'Error While Updating'
                        tpa_product_list.append(tpa_product_dict)

                    # print ("------------------")
                    # print (tpa_product_dict)
                    # print(e)
                    # print ("------------------")
                    pass

            # print(tpa_product_list)
            # return (str([{"Data":"Success"}]))
            cursor.close()
            return {"Data": tpa_product_list}
            

        return {"Data": [],"Message":"No Product Exported"}

    except Exception as e:
        logging.info("2")
        logging.warning(e)

        # print (e)
        data = 0
        return ({"Status": 404, "Message": "Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])


@products.route('/QBD/synchronize_qbd_ids', methods=['POST'])
def synchronize_qbd():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()
        req = request.get_json(force=True)
        data_list = []
        # print("1",req)
        for rec in req:
            query = "Select* FROM ItemInventory where name='{}'".format(
                rec['name'])
            cursor.execute(query)
            records = cursor.fetchall()
            # print(records)
            for row in records:
                data_dict = {}
                row_as_list = [x for x in row]
                if len(records) == 1:
                    data_dict['quickbook_id'] = row_as_list[0]
                    data_dict['id'] = rec['id']
                    data_list.append(data_dict)
                    # print(data_list)
        return json.dumps(data_list)
    except Exception as e:
        logging.info("3")
        logging.warning(e)

        print(e)
        data = 0
        return ({"Status": 404, "Message": "Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])
