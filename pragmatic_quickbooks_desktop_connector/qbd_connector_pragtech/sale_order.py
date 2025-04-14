from flask import Blueprint, request
from connection import connect_to_qbd,close_connection_to_qbd
import logging
import json
logging.basicConfig(level=logging.DEBUG)

from datetime import datetime
sale_order = Blueprint('sale_order', __name__, template_folder='templates')

'''
TPA - Third Party Application
'''

@sale_order.route('/QBD/import_sales_order')
def import_QBD_Sales_Order_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        to_execute_account = int(request.args.get('to_execute_account'))
        # limit = int(request.args.get('limit'))
        limit = request.args.get('limit')
        if limit:
            limit = int(limit)
        if to_execute_account == 1:
            # sale_order = "SELECT TOP {} TxnID, CustomerRefListID, IsFullyInvoiced, TxnDate, RefNumber, Memo, Timemodified FROM SalesOrder where IsFullyInvoiced = False order by Timemodified ASC".format(limit)
            sale_order = "SELECT TOP {} TxnID, CustomerRefListID, IsFullyInvoiced, TxnDate, RefNumber, Memo, Timemodified FROM SalesOrder order by Timemodified ASC".format(limit)

            cursor.execute(sale_order)

        elif to_execute_account == 2:
            time_modified = "{ts'"+str(request.args.get('last_qbd_id'))+"'}" 
            # print (time_modified)
            sale_order = "SELECT TOP {} TxnID, CustomerRefListID, IsFullyInvoiced, TxnDate, RefNumber, Memo, Timemodified FROM SalesOrder where timemodified >={} order by Timemodified ASC".format(limit, time_modified)
            cursor.execute(sale_order)
        elif to_execute_account == 3:
            ref_number = request.args.get('qbd_sale_order_id')
            sale_order = "SELECT TxnID, CustomerRefListID, IsFullyInvoiced, TxnDate, RefNumber, Memo, Timemodified FROM SalesOrder WHERE RefNumber = '{}'".format(ref_number)
            

            cursor.execute(sale_order)
            

        # if request.args['fetch_record'] == 'all':
        #     cursor.execute("SELECT TxnID, CustomerRefListID, IsFullyInvoiced, TxnDate, RefNumber, Memo, Timemodified FROM SalesOrder")  

        # elif request.args['fetch_record'] == 'one':
        #     ListId = request.args['quickbooks_id']
        #     cursor.execute("SELECT ListId, ParentRefListId, FullName, Email, Phone, AltPhone, Fax, Notes, BillAddressAddr1, BillAddressAddr2, BillAddressCountry, BillAddressState, BillAddressCity, BillAddressPostalCode FROM Customer Where ListID='"+ListId+"' Order by ListId ASC")

        odoo_sales_order_list = []
        
        for row in cursor.fetchall():
            odoo_sales_order_dict = {}
            row_as_list = [x for x in row]

            odoo_sales_order_dict['quickbooks_id'] = row_as_list[0] #TxnID
            odoo_sales_order_dict['partner_name'] = row_as_list[1] #CustomerRefListID
            odoo_sales_order_dict['state'] = 'draft'
            #Search 'parnter_id' from 'partner_name' where 'CustomerRefListId' is 'quickbooks_id' in 'res.partner'

            ######### Code is commented as it raise confusion while importing sale order
            ######### sale order going to state done also delivery is created but invoice is not imported
            # if row_as_list[2]:
            #     odoo_sales_order_dict['state'] = 'sale'
            #     odoo_sales_order_dict['confirmation_date'] = str(row_as_list[3])
            # else:
            #     odoo_sales_order_dict['state'] = 'sale'
            #     odoo_sales_order_dict['confirmation_date'] = str(row_as_list[3])

            odoo_sales_order_dict['date_order'] = str(row_as_list[3])
            odoo_sales_order_dict['qbd_sale_order_number'] = row_as_list[4]
            odoo_sales_order_dict['qbd_memo'] = row_as_list[5]
            
            # cursor.execute("SELECT TxnID, SalesOrderLineItemRefListID, SalesOrderLineSeqNo, SalesOrderLineQuantity, SalesOrderLineRate, IsFullyInvoiced, SalesOrderLineAmount, SalesOrderLinedesc FROM SalesOrderLine WHERE TxnID = '"+row_as_list[0]+"'")
            cursor.execute("SELECT TxnID, SalesOrderLineItemRefListID, SalesOrderLineSeqNo, SalesOrderLineQuantity, SalesOrderLineRate, IsFullyInvoiced, SalesOrderLineAmount, SalesOrderLinedesc, ItemSalesTaxRefListID, SalesOrderLineTaxCodeRefFullName, SalesOrderLineItemRefFullName FROM SalesOrderLine WHERE TxnID = '"+row_as_list[0]+"'")
            
            odoo_sales_order_line_list = []
            
            for row in cursor.fetchall(): 
                odoo_sales_order_line_dict = {}
            
                row_as_list_oline = [x for x in row]
                # Use this to search product in 'product.product' we are passing quickbooks_id in product_name
                odoo_sales_order_line_dict['product_name'] = row_as_list_oline[1]

                # print ("QTY -----------------")
                # print (row_as_list_oline[3])

                if row_as_list_oline[3] == 0:
                    odoo_sales_order_line_dict['product_uom_qty'] = str(0.0)
                elif row_as_list_oline[3] is None:
                    odoo_sales_order_line_dict['product_uom_qty'] = str(1.0)
                else:
                    odoo_sales_order_line_dict['product_uom_qty'] = str(row_as_list_oline[3])
                    
                
                if row_as_list_oline[4]:
                    odoo_sales_order_line_dict['price_unit'] = str(row_as_list_oline[4])
                else:
                    odoo_sales_order_line_dict['price_unit'] = str(0.0)
                
                if row_as_list_oline[6]:
                    odoo_sales_order_line_dict['price_subtotal'] = str(row_as_list_oline[6])
                else:
                    odoo_sales_order_line_dict['price_subtotal'] = str(0.0)
                
                odoo_sales_order_line_dict['product_template_id'] = row_as_list_oline[10]
                odoo_sales_order_line_dict['name'] = row_as_list_oline[7]
                odoo_sales_order_line_dict['qbd_tax_code'] = row_as_list_oline[9]

                odoo_sales_order_line_dict['qty_invoiced'] = 0
                if row_as_list_oline[5]:
                    odoo_sales_order_line_dict['qty_invoiced'] = row_as_list_oline[5]
    
                odoo_sales_order_line_dict['tax_qbd_id'] = row_as_list_oline[8]
                odoo_sales_order_line_dict['tax_code'] = row_as_list_oline[9]


                odoo_sales_order_line_list.append(odoo_sales_order_line_dict)
                
            # print ("-------",odoo_sales_order_line_list)
            odoo_sales_order_dict['order_lines'] = odoo_sales_order_line_list
            odoo_sales_order_dict['last_time_modified'] = str(row_as_list[6])
            

            odoo_sales_order_list.append(odoo_sales_order_dict)

        print ("===========odoo_sales_order_list=========",odoo_sales_order_list)

        cursor.close()
        return (json.dumps(odoo_sales_order_list))
        
    except Exception as e:
        # print (e)
        data = 0
        return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])

'''
TPA - Third Party Application
'''
@sale_order.route('/QBD/export_sale_orders', methods=['POST'])
def export_TPA_sale_orders_to_QBD():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()
        is_update = 0 


        req = request.get_json(force=True)
        print (req)
        if 'sale_orders_list' in req:

            tpa_sale_orders_list = []
            for rec in req.get('sale_orders_list'):
                tpa_sale_orders_dict={}
                count = 0
                success = 0
                success_update = 0
                line_error = 0
                line_update_error = 0
                is_update = 0

                qbd_memo = rec.get('qbd_memo')
                if rec.get('sale_order_qbd_id'):
                    quickbooks_id = rec.get('sale_order_qbd_id')
                    is_update = 1

                ref_number = rec.get('odoo_order_number')
                default_tax_on_order = rec.get('default_tax_on_order')

                check_record = False
                is_present = False

                if ref_number:
                    check_record ="Select Top 1 TxnId,RefNumber,TimeModified from SalesOrder where Memo='{}'".format(ref_number)
                    cursor.execute(check_record)
                    is_present = cursor.fetchone()

                
                for lines in rec.get('order_lines'):
                    # print (lines)
                    count+=1
                    product_quickbooks_id = lines.get('product_name')

                    if lines.get('product_uom_qty'):
                        order_line_quantity = float(lines.get('product_uom_qty'))
                    else:
                        order_line_quantity = 0.0

                    if lines.get('price_unit'):
                        order_line_rate = float(lines.get('price_unit'))
                    else:
                        order_line_rate = 0.0

                    if lines.get('price_subtotal'):
                        order_line_amount = float(lines.get('price_subtotal'))
                    else:
                        order_line_amount = 0.0

                    order_line_desc = lines.get('name')
                    customer_quickbooks_id = rec.get('partner_name')
                    order_line_txn_date = "{d'"+rec.get('confirmation_date')+"'}"
                    if count == len(rec.get('order_lines')):
                        save_to_cache = str(False)
                    else:
                        save_to_cache = str(True)

                    if lines.get('tax_id'):
                        tax_id = lines.get('tax_id')
                    else:
                        tax_id=''

                    if lines.get('qbd_tax_code'):
                        qbd_tax_code = lines.get('qbd_tax_code')
                    else:
                        qbd_tax_code = ''

                    # print ("ssssssssssss ",order_line_txn_date)
                    
                    if not is_update:
                        if not is_present:
                            if tax_id:
                                insertQuery = "Insert into salesorderline(SalesOrderLineItemRefListID, SalesOrderLineQuantity, SalesOrderLineRate, SalesOrderLineAmount, SalesOrderLinedesc, CustomerRefListID, TxnDate, FQSaveToCache, ItemSalesTaxRefListID, SalesOrderLineTaxCodeRefFullName, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}','{}', '{}', '{}')".format(product_quickbooks_id, order_line_quantity, order_line_rate, order_line_amount, order_line_desc, customer_quickbooks_id, order_line_txn_date, save_to_cache, tax_id, qbd_tax_code, qbd_memo, ref_number)
                            else:
                                insertQuery = "Insert into salesorderline(SalesOrderLineItemRefListID, SalesOrderLineQuantity, SalesOrderLineRate, SalesOrderLineAmount, SalesOrderLinedesc, CustomerRefListID, TxnDate, FQSaveToCache, SalesOrderLineTaxCodeRefFullName, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}', '{}', '{}')".format(product_quickbooks_id, order_line_quantity, order_line_rate, order_line_amount, order_line_desc, customer_quickbooks_id, order_line_txn_date, save_to_cache, qbd_tax_code, qbd_memo, ref_number)

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

                            tpa_sale_orders_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_sale_orders_dict['quickbooks_id'] = is_present[0]
                            tpa_sale_orders_dict['message'] = 'Quickbooks Id Successfully Added'
                            tpa_sale_orders_dict['qbd_sale_order_no'] = is_present[1]
                            tpa_sale_orders_dict['last_modified_date'] = str(is_present[2])

                    else:
                        chk_bool=''
                        check_line_present = "SELECT SalesOrderLineItemRefListID FROM SalesOrderLine where TxnId='{}'".format(quickbooks_id)
                        cursor.execute(check_line_present)  
                        
                        # print ("=================",check_line_present)
                        # print (cursor)
                        # print (cursor.fetchone())
                        # print ("=================")
                        record = cursor.fetchone()
                        if record:
                            chk_bool = record[0]

                        # print ("Check SO Line")
                        # print (chk_bool)
                        if chk_bool:
                            updateQuery = "Update salesorderline Set SalesOrderLineQuantity= {}, SalesOrderLineRate={}, SalesOrderLineAmount={} where SalesOrderLineItemRefListID='{}' and CustomerRefListID='{}' and TxnDate={}".format(order_line_quantity, order_line_rate, order_line_amount, product_quickbooks_id, customer_quickbooks_id, order_line_txn_date)
                        else:
                            # Insert New Line
                            # print ("sddfgdfgdf")
                            if tax_id:
                                updateQuery = "Insert into salesorderline(SalesOrderLineItemRefListID, SalesOrderLineQuantity, SalesOrderLineRate, SalesOrderLineAmount, SalesOrderLinedesc, CustomerRefListID, TxnDate, FQSaveToCache, ItemSalesTaxRefListID, SalesOrderLineTaxCodeRefFullName, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}','{}', '{}', '{}')".format(product_quickbooks_id, order_line_quantity, order_line_rate, order_line_amount, order_line_desc, customer_quickbooks_id, order_line_txn_date, save_to_cache, tax_id, qbd_tax_code, qbd_memo, ref_number)
                            else:
                                updateQuery = "Insert into salesorderline(SalesOrderLineItemRefListID, SalesOrderLineQuantity, SalesOrderLineRate, SalesOrderLineAmount, SalesOrderLinedesc, CustomerRefListID, TxnDate, FQSaveToCache, SalesOrderLineTaxCodeRefFullName, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}', '{}', '{}')".format(product_quickbooks_id, order_line_quantity, order_line_rate, order_line_amount, order_line_desc, customer_quickbooks_id, order_line_txn_date, save_to_cache, qbd_tax_code, qbd_memo, ref_number)
                            # updateQuery = "Insert into salesorderline (SalesOrderLineItemRefListID, SalesOrderLineQuantity, SalesOrderLineRate, SalesOrderLineAmount, SalesOrderLinedesc, CustomerRefListID, TxnDate, FQSaveToCache, ItemSalesTaxRefListID, SalesOrderLineTaxCodeRefFullName) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}' ,'{}')".format(product_quickbooks_id, order_line_quantity, order_line_rate, order_line_amount, order_line_desc, customer_quickbooks_id, order_line_txn_date, save_to_cache, qbd_tax_code, tax_id)

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
                    lastInserted ="Select Top 1 TxnId,RefNumber from SalesOrder where RefNumber='{}'".format(ref_number)
                    # lastInserted ="Select Top 1 TxnId,RefNumber from SalesOrder order by timecreated desc"
                    cursor.execute(lastInserted)
                    tuple_data = cursor.fetchone()
                    tpa_sale_orders_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_sale_orders_dict['quickbooks_id'] = tuple_data[0]
                    tpa_sale_orders_dict['message'] = 'Successfully Created'
                    tpa_sale_orders_dict['qbd_sale_order_no'] = tuple_data[1]
                    now = datetime.now()
                    tpa_sale_orders_dict['last_modified_date'] = str(now.strftime("%d-%m-%Y %H:%M:%S"))
                    
                    
                    # tpa_sale_orders_list.append(tpa_sale_orders_dict)

                    insertTax = "Update SalesOrder Set ItemSalesTaxRefFullName = '{}' where TxnId = '{}'".format(default_tax_on_order,tuple_data[0])
                    logging.info("Query for Default Tax On SalesOrder----------------------------- ")
                    logging.info(insertTax)
                    cursor.execute(insertTax)

                    cursor.commit()

                elif success_update == 1:
                    tpa_sale_orders_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_sale_orders_dict['quickbooks_id'] = rec.get('sale_order_qbd_id')
                    tpa_sale_orders_dict['message'] = 'Successfully Updated'
                    tpa_sale_orders_dict['qbd_sale_order_no'] = ''
                    # tpa_sale_orders_list.append(tpa_sale_orders_dict)
                    cursor.commit()
                
                if line_error == 1:
                    tpa_sale_orders_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_sale_orders_dict['quickbooks_id'] = ''
                    tpa_sale_orders_dict['qbd_sale_order_no'] = ''
                    tpa_sale_orders_dict['message'] = 'Error while Creating Some Order Lines'
                    # tpa_sale_orders_list.append(tpa_sale_orders_dict)

                elif line_update_error == 1:
                    tpa_sale_orders_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_sale_orders_dict['quickbooks_id'] = rec.get('sale_order_qbd_id')
                    tpa_sale_orders_dict['message'] = 'Error while Updating Some Order Lines'
                    # tpa_sale_orders_list.append(tpa_sale_orders_dict)
                    tpa_sale_orders_dict['qbd_sale_order_no'] = ''

                tpa_sale_orders_list.append(tpa_sale_orders_dict)
                
            print(tpa_sale_orders_list)
            cursor.close()
            logging.info("Data List")
            logging.info(tpa_sale_orders_list)
            
            return {"Data":tpa_sale_orders_list}
        
        return {"Data":[], "Message":'No SaleOrder Exported'}

    except Exception as e:
        logging.info("3")
        logging.warning(e)
        # print (e)
        data = 0
        return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])
