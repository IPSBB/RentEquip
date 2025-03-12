from flask import Blueprint, request
from connection import connect_to_qbd,close_connection_to_qbd
import logging
import json
logging.basicConfig(level=logging.DEBUG)
from datetime import datetime
purchase_order = Blueprint('purchase_order', __name__, template_folder='templates')

'''
TPA - Third Party Application
'''
@purchase_order.route('/QBD/import_purchase_order')
def import_QBD_Purchase_Order_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        to_execute_account = int(request.args.get('to_execute_account'))
        limit = int(request.args.get('limit'))

        if to_execute_account == 1:
            purchase_order = "SELECT TOP {} TxnID, VendorRefListId, isManuallyClosed, TxnDate, RefNumber, Memo, Timemodified FROM PurchaseOrder order by timemodified asc".format(limit)
            cursor.execute(purchase_order)

        elif to_execute_account == 2:
            time_modified = "{ts'"+str(request.args.get('last_qbd_id'))+"'}" 
            # print (time_modified)
            purchase_order = "SELECT TOP {} TxnID, VendorRefListId, isManuallyClosed, TxnDate, RefNumber, Memo, Timemodified FROM PurchaseOrder where timemodified >={} order by timemodified asc".format(limit, time_modified)
            cursor.execute(purchase_order)


        # if request.args['fetch_record'] == 'all':
        #     cursor.execute("SELECT TOP 10 TxnID, VendorRefListId, isManuallyClosed, TxnDate, RefNumber, Memo FROM PurchaseOrder")  
# 0 TxnId
# 1 VendorRefListId
# 2 isManuallyClosed
# 3 TxnDate 
# 4 RefNumber
# 5 Memo

        # elif request.args['fetch_record'] == 'one':
        #     ListId = request.args['quickbooks_id']
        #     cursor.execute("SELECT ListId, ParentRefListId, FullName, Email, Phone, AltPhone, Fax, Notes, BillAddressAddr1, BillAddressAddr2, BillAddressCountry, BillAddressState, BillAddressCity, BillAddressPostalCode FROM Customer Where ListID='"+ListId+"' Order by ListId ASC")

        odoo_purchase_order_list = []
        
        for row in cursor.fetchall():
            odoo_purchase_order_dict = {}
            row_as_list = [x for x in row]

            odoo_purchase_order_dict['quickbooks_id'] = row_as_list[0] #TxnID
            odoo_purchase_order_dict['partner_name'] = row_as_list[1] #VendorRefListID
            #Search 'parnter_id' from 'partner_name' where 'VendorRefListId' is 'quickbooks_id' in 'res.partner'

            # if row_as_list[2]:
            #     odoo_sales_order_dict['state'] = 'sale'
            #     odoo_sales_order_dict['confirmation_date'] = str(row_as_list[3])
            # else:
            odoo_purchase_order_dict['state'] = 'draft'
            odoo_purchase_order_dict['confirmation_date'] = str(row_as_list[3])

            odoo_purchase_order_dict['date_order'] = str(row_as_list[3])
            odoo_purchase_order_dict['qbd_purchase_order_number'] = row_as_list[4]
            odoo_purchase_order_dict['qbd_memo'] = row_as_list[5]
            
            cursor.execute("SELECT TxnID, PurchaseOrderLineItemRefListID, PurchaseOrderLineSeqNo, PurchaseOrderLineQuantity, PurchaseOrderLineRate, isManuallyClosed, PurchaseOrderLineAmount, PurchaseOrderLinedesc, ExpectedDate  FROM PurchaseOrderLine WHERE TxnID = '"+row_as_list[0]+"'")

            # 0 TxnID, 
            # 1 PurchaseOrderLineItemRefListID, 
            # 2 PurchaseOrderLineSeqNo,    
            # 3 PurchaseOrderLineQuantity, 
            # 4 PurchaseOrderLineRate, 
            # 5 isManuallyClosed, 
            # 6 PurchaseOrderLineAmount, 
            # 7 PurchaseOrderLinedesc              
            # 8 ExpectedDate
            odoo_purchase_order_line_list = []
            
            for row in cursor.fetchall(): 
                odoo_purchase_order_line_dict = {}
            
                row_as_list_poline = [x for x in row]
                # Use this to search product in 'product.product' we are passing quickbooks_id in product_name
                odoo_purchase_order_line_dict['product_name'] = row_as_list_poline[1]

                if row_as_list_poline[3] == 0:
                    odoo_purchase_order_line_dict['product_qty'] = str(0.0)
                elif row_as_list_poline[3] is None:
                    odoo_purchase_order_line_dict['product_qty'] = str(1.0)
                else:
                    odoo_purchase_order_line_dict['product_qty'] = str(row_as_list_poline[3])
                
                if row_as_list_poline[4]:
                    odoo_purchase_order_line_dict['price_unit'] = str(row_as_list_poline[4])
                else:
                    odoo_purchase_order_line_dict['price_unit'] = '0.00'
                odoo_purchase_order_line_dict['price_subtotal'] = str(row_as_list_poline[6])
                odoo_purchase_order_line_dict['name'] = row_as_list_poline[7]
                # odoo_sales_order_line_dict['qty_invoiced'] = 0
                # if row_as_list_oline[5]:
                #     odoo_sales_order_line_dict['qty_invoiced'] = row_as_list_oline[5]
                odoo_purchase_order_line_dict['date_planned'] = str(row_as_list_poline[8])
				
                odoo_purchase_order_line_list.append(odoo_purchase_order_line_dict)
                
            # print (odoo_purchase_order_line_list)
            odoo_purchase_order_dict['purchase_order_lines'] = odoo_purchase_order_line_list
            odoo_purchase_order_dict['last_time_modified'] = str(row_as_list[6])
            
            # Last_QBD_id = str(row_as_list[6])
            
            odoo_purchase_order_list.append(odoo_purchase_order_dict)
            
        #print (odoo_sales_order_list)

        cursor.close()
        return (json.dumps(odoo_purchase_order_list))
        
    except Exception as e:
        # print (e)
        data = 0
        return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])

@purchase_order.route('/QBD/export_purchase_orders', methods=['POST'])
def export_TPA_purchase_orders_to_QBD():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        req = request.get_json(force=True)
        # print (len(req.get('purchase_orders_list')))
        if 'purchase_orders_list' in req:

            tpa_purchase_orders_list = []
            for rec in req.get('purchase_orders_list'):
                # print (rec)

                tpa_purchase_orders_dict={}
                count = 0
                success = 0
                success_update = 0
                line_error = 0
                line_update_error = 0
                is_update = 0
                
                qbd_memo = rec.get('qbd_memo')
                ref_number = rec.get('odoo_purchase_order_number')

                if rec.get('qbd_purchase_order_id'):
                    quickbooks_id = rec.get('qbd_purchase_order_id')
                    is_update = 1

                check_record = False
                is_present = False

                if ref_number:
                    check_record ="Select Top 1 TxnId,RefNumber,TimeModified from PurchaseOrder where RefNumber='{}'".format(ref_number)
                    cursor.execute(check_record)
                    is_present = cursor.fetchone()

                for lines in rec.get('order_lines'):
                    count+=1
                    product_quickbooks_id = lines.get('product_name')

                    if lines.get('product_qty'):
                        purchase_order_line_quantity = float(lines.get('product_qty'))
                    else:
                        purchase_order_line_quantity = 0.0

                    if lines.get('price_unit'):
                        purchase_order_line_rate = float(lines.get('price_unit'))
                    else:
                        purchase_order_line_rate = 0.0

                    if lines.get('price_subtotal'):
                        purchase_order_line_amount = float(lines.get('price_subtotal'))
                    else:
                        purchase_order_line_amount = 0.0

                    purchase_order_line_desc = lines.get('name')
                    customer_quickbooks_id = rec.get('partner_name')
                    purchase_order_line_txn_date = "{d'"+rec.get('date_order')+"'}"
                    if count == len(rec.get('order_lines')):
                        save_to_cache = str(False)
                    else:
                        save_to_cache = str(True)
                    # print ("ssssssssssss ",purchase_order_line_txn_date)

                    if not is_update:
                        if not is_present:
                            insertQuery = "Insert into PurchaseOrderLine (PurchaseOrderLineItemRefListID, PurchaseOrderLineQuantity, PurchaseOrderLineRate, PurchaseOrderLineAmount, PurchaseOrderLineDesc, VendorRefListID, TxnDate, FQSaveToCache, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}', '{}')".format(product_quickbooks_id, purchase_order_line_quantity, purchase_order_line_rate, purchase_order_line_amount, purchase_order_line_desc, customer_quickbooks_id, purchase_order_line_txn_date, save_to_cache, qbd_memo, ref_number)

                            try:
                                logging.info("Insert Query ----------------------------- ")
                                logging.info(insertQuery)

                                # print (insertQuery)
                                cursor.execute(insertQuery)
                                success = 1
                        
                            except Exception as e:
                                logging.info("1")
                                logging.warning(e)                            
                                line_error = 1
                                # print(e)
                                pass

                        elif is_present:
                            logging.info("Record Already Present in Quickbboks so updating id in Odoo ----------------------------- ")
                            logging.info(check_record)
                            logging.info(is_present[0])

                            tpa_purchase_orders_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_purchase_orders_dict['quickbooks_id'] = is_present[0]
                            tpa_purchase_orders_dict['message'] = 'Quickbooks Id Successfully Added'
                            tpa_purchase_orders_dict['qbd_purchase_order_no'] = is_present[1]
                            tpa_purchase_orders_dict['last_modified_date'] = str(is_present[2])


                    else:
                        chk_bool=''
                        check_line_present = "SELECT PurchaseOrderLineItemRefListID FROM PurchaseOrderLine where TxnId='{}' and PurchaseOrderLineItemRefListID='{}'".format(quickbooks_id, product_quickbooks_id)
                        cursor.execute(check_line_present)  
                        
                        # print ("=================")
                        # print (cursor)
                        # print (cursor.fetchone())
                        # print ("=================")
                        if cursor.fetchone():
                            chk_bool = cursor.fetchone()[0]

                        # print ("Check PO Line")
                        # print (chk_bool)
                        if chk_bool:
                            updateQuery = "Update PurchaseOrderLine Set PurchaseOrderLineQuantity={}, PurchaseOrderLineRate={}, PurchaseOrderLineAmount={} where PurchaseOrderLineItemRefListID='{}' and VendorRefListID='{}' and TxnDate={}".format(purchase_order_line_quantity, purchase_order_line_rate, purchase_order_line_amount, product_quickbooks_id, customer_quickbooks_id, purchase_order_line_txn_date)
                        else:
                            # Insert New Line
                            # print ("sddfgdfgdf")
                            updateQuery = "Insert into PurchaseOrderLine (PurchaseOrderLineItemRefListID, PurchaseOrderLineQuantity, PurchaseOrderLineRate, PurchaseOrderLineAmount, PurchaseOrderLineDesc, VendorRefListID, TxnDate, FQSaveToCache, Memo) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}')".format(product_quickbooks_id, purchase_order_line_quantity, purchase_order_line_rate, purchase_order_line_amount, purchase_order_line_desc, customer_quickbooks_id, purchase_order_line_txn_date, save_to_cache, qbd_memo)

                        try:
                            # print (updateQuery)
                            cursor.execute(updateQuery)
                            success_update = 1
                        
                        except Exception as e:
                            logging.info("2")
                            logging.warning(e)                            
                            line_update_error = 1
                            # print(e)
                            pass
                        

                if success == 1:
                    lastInserted ="Select Top 1 TxnId,RefNumber from PurchaseOrder where RefNumber='{}'".format(ref_number)
                    # lastInserted ="Select Top 1 TxnId,RefNumber from PurchaseOrder order by timecreated desc"
                    cursor.execute(lastInserted)
                    tuple_data = cursor.fetchone()
                    tpa_purchase_orders_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_purchase_orders_dict['quickbooks_id'] = tuple_data[0]
                    tpa_purchase_orders_dict['message'] = 'Successfully Created'
                    tpa_purchase_orders_dict['qbd_purchase_order_no'] = tuple_data[1]
                    now = datetime.now()
                    tpa_purchase_orders_dict['last_modified_date'] = str(now.strftime("%d-%m-%Y %H:%M:%S"))
                    # tpa_purchase_orders_list.append(tpa_purchase_orders_dict)
                    cursor.commit()

                elif success_update == 1:
                    tpa_purchase_orders_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_purchase_orders_dict['quickbooks_id'] = rec.get('qbd_purchase_order_id')
                    tpa_purchase_orders_dict['message'] = 'Successfully Updated'
                    tpa_purchase_orders_dict['qbd_purchase_order_no'] = ''
                    # tpa_purchase_orders_list.append(tpa_purchase_orders_dict)
                    cursor.commit()
                
                if line_error == 1:
                    tpa_purchase_orders_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_purchase_orders_dict['quickbooks_id'] = ''
                    tpa_purchase_orders_dict['qbd_purchase_order_no'] = ''
                    tpa_purchase_orders_dict['message'] = 'Error while Creating Some Order lines'
                    # tpa_purchase_orders_list.append(tpa_purchase_orders_dict)
                    cursor.commit()

                    
                elif line_update_error == 1:
                    tpa_purchase_orders_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_purchase_orders_dict['quickbooks_id'] = rec.get('qbd_purchase_order_id')
                    tpa_purchase_orders_dict['message'] = 'Error while Updating Some Order Lines'
                    # tpa_purchase_orders_list.append(tpa_purchase_orders_dict)
                    tpa_purchase_orders_dict['qbd_purchase_order_no'] = ''
            
                tpa_purchase_orders_list.append(tpa_purchase_orders_dict)
            # print(tpa_purchase_orders_list)
            logging.info("Data List")
            logging.info(tpa_purchase_orders_list)
            cursor.close()
            
            return {"Data":tpa_purchase_orders_list}
        
        return {"Data":[], "Message":'No PurchaseOrder Exported'}

    except Exception as e:
        logging.info("3")
        logging.warning(e)        
        # print (e)
        data = 0
        return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])
