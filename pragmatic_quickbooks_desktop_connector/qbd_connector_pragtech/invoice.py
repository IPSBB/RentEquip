from flask import Blueprint, request
from connection import connect_to_qbd,close_connection_to_qbd
import logging
import json
logging.basicConfig(level=logging.DEBUG)
from datetime import datetime
invoice = Blueprint('invoice', __name__, template_folder='templates')

'''
TPA - Third Party Application
'''
@invoice.route('/QBD/import_invoice')
def import_QBD_Invoice_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        to_execute_account = int(request.args.get('to_execute_account'))
        # limit = int(request.args.get('limit'))
        limit = request.args.get('limit')
        if limit:
            limit = int(limit)
        is_vendor_bill = request.args.get('is_vendor_bill')
        if to_execute_account == 1:
            if is_vendor_bill:
                invoice_order = "SELECT TOP {} VendorRefListID, TermsRefFullName, APAccountRefListID, TxnDate, TimeCreated, DueDate, IsPaid, RefNumber, TxnId, Timemodified FROM Bill order by timemodified asc".format(limit)
            else:
                invoice_order = "SELECT TOP {} CustomerRefListID, TermsRefFullName, ARAccountRefListID, TxnDate, TimeCreated, DueDate, IsPaid, RefNumber, TxnId, Timemodified , ItemSalesTaxRefListID FROM Invoice order by timemodified asc".format(limit)
            cursor.execute(invoice_order)

        elif to_execute_account == 2:
            time_modified = "{ts'"+str(request.args.get('last_qbd_id'))+"'}" 
            # print (time_modified)
            if is_vendor_bill:
                invoice_order = "SELECT TOP {} VendorRefListID, TermsRefFullName, APAccountRefListID, TxnDate, TimeCreated, DueDate, IsPaid, RefNumber, TxnId, Timemodified FROM Bill where timemodified >={} order by timemodified asc".format(limit, time_modified)
            else:
                invoice_order = "SELECT TOP {} CustomerRefListID, TermsRefFullName, ARAccountRefListID, TxnDate, TimeCreated, DueDate, IsPaid, RefNumber, TxnId, Timemodified, ItemSalesTaxRefListID FROM Invoice where timemodified >={} order by Timemodified ASC".format(limit, time_modified)
            cursor.execute(invoice_order)
        elif to_execute_account == 3:
            invoice_number = request.args.get('qbd_invoice_number')
            if is_vendor_bill:
                invoice_order = "SELECT VendorRefListID, TermsRefFullName, APAccountRefListID, TxnDate, TimeCreated, DueDate, IsPaid, RefNumber, TxnId, Timemodified FROM Bill WHERE RefNumber = '{}'".format(invoice_number)
            else:
                invoice_order = "SELECT CustomerRefListID, TermsRefFullName, ARAccountRefListID, TxnDate, TimeCreated, DueDate, IsPaid, RefNumber, TxnId, Timemodified, ItemSalesTaxRefListID FROM Invoice WHERE RefNumber = '{}'".format(invoice_number)
            cursor.execute(invoice_order)
        # if request.args['fetch_record'] == 'all':
            # cursor.execute("SELECT TOP 2 CustomerRefListID, TermsRefFullName, ARAccountRefListID, TxnDate, TimeCreated, DueDate, IsPaid, RefNumber, TxnId FROM Invoice")  

        # elif request.args['fetch_record'] == 'one':
        #     ListId = request.args['quickbooks_id']
        #     cursor.execute("SELECT ListId, ParentRefListId, FullName, Email, Phone, AltPhone, Fax, Notes, BillAddressAddr1, BillAddressAddr2, BillAddressCountry, BillAddressState, BillAddressCity, BillAddressPostalCode FROM Customer Where ListID='"+ListId+"' Order by ListId ASC")

        odoo_invoice_list = []
        
        for row in cursor.fetchall():
            odoo_invoice_dict = {}
            row_as_list = [x for x in row]
            txn_id = row_as_list[8]
            # Check for linked transactions
            linked_txn_query = "SELECT LinkedTxnRefNumber FROM InvoiceLinkedTxn WHERE TxnID = '{}'".format(txn_id)

            cursor.execute(linked_txn_query)
            linked_txns = cursor.fetchall()
            # Add linked transaction references if found
            
            if linked_txns:
                odoo_invoice_dict['linked_transactions'] = [txn[0] for txn in linked_txns]


            odoo_invoice_dict['quickbooks_id'] = row_as_list[8]
            odoo_invoice_dict['partner_name'] = row_as_list[0]
            #Search partner_id in odoo from res.partner where partner_name is quicbooks_id in res.partner
            odoo_invoice_dict['number'] = row_as_list[7]

            if row_as_list[5]:
                odoo_invoice_dict['date_due'] = str(row_as_list[3])
            
            
            if row_as_list[1] == 'Net 30':
                odoo_invoice_dict['term_name'] = '30 Net Days'
            elif row_as_list[1] == 'Net 15':
                odoo_invoice_dict['term_name'] = '15 Days'
            else:
                odoo_invoice_dict['term_name'] = None
            #Search term_id in account.payment.term from term_name
            # if term_id found set invoice_dict[payment_term_id] = that term

            if row_as_list[6]:
                odoo_invoice_dict['state'] = 'paid'
                odoo_invoice_dict['date_invoice'] = str(row_as_list[3])

            if row_as_list[8]:
                odoo_invoice_dict['qbd_tax'] = row_as_list[8]


            if is_vendor_bill:
                cursor.execute("SELECT TxnID, ItemLineItemRefListID, ItemLineSeqNo, APAccountRefListID, ItemLineQuantity, ItemLineCost, IsPaid, ItemLineAmount, ItemLineDesc FROM BillItemLine WHERE TxnID = '"+row_as_list[8]+"'")
            else:
                cursor.execute("SELECT TxnID, InvoiceLineItemRefListID, InvoiceLineSeqNo, ARAccountRefListID, InvoiceLineQuantity, InvoiceLineRate, IsPaid, InvoiceLineAmount, InvoiceLineDesc, ItemSalesTaxRefListID, InvoiceLineTaxCodeRefFullName FROM InvoiceLine WHERE TxnID = '"+row_as_list[8]+"'")
            
            odoo_invoice_line_list = []
            
            for row in cursor.fetchall(): 
                odoo_invoice_line_dict ={}
                row_as_inv_line = [x for x in row]

                odoo_invoice_line_dict['product_name'] = row_as_inv_line[1]
                # Find this product in product.product where product_name is quickbooks_id and store in product_id field
                odoo_invoice_line_dict['account_name'] = row_as_inv_line[3]
                # Find this account in account.account where account_name is quickbooks_id and store in account_id field
                if row_as_inv_line[4] == 0:
                    odoo_invoice_line_dict['quantity'] = str(0.0)
                elif row_as_inv_line[4] is None:
                    odoo_invoice_line_dict['quantity'] = str(1.0)
                else:
                    odoo_invoice_line_dict['quantity'] = str(row_as_inv_line[4])

                odoo_invoice_line_dict['price_unit'] = str(row_as_inv_line[5])
                odoo_invoice_line_dict['price_subtotal'] = str(row_as_inv_line[7])
                odoo_invoice_line_dict['name'] = row_as_inv_line[8]

                if not is_vendor_bill:
                    odoo_invoice_line_dict['tax_qbd_id'] = row_as_inv_line[9]
                if not is_vendor_bill:
                    odoo_invoice_line_dict['tax_code'] = row_as_inv_line[10]

                odoo_invoice_line_list.append(odoo_invoice_line_dict)

                # print ("Quantity -----------------------------------")
                # print (row_as_inv_line[4])
                # print ("--------------------------------------------")
                
                # print ("----")
                # print (odoo_invoice_line_list)
            odoo_invoice_dict['invoice_lines'] = odoo_invoice_line_list
            odoo_invoice_dict['last_time_modified'] = str(row_as_list[9])
            # Last_QBD_id = str(row_as_list[9])
            odoo_invoice_list.append(odoo_invoice_dict)
            
        print (odoo_invoice_list)

        cursor.close()
        return (json.dumps(odoo_invoice_list))
        
    except Exception as e:
        # print (e)
        data = 0
        return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])
            
@invoice.route('/QBD/export_invoices', methods=['POST'])
def export_TPA_invoice_to_QBD():
#     try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        req = request.get_json(force=True)
        # print (req)
        if 'invoices_list' in req:

            tpa_invoice_list = []
            for rec in req.get('invoices_list'):
                # print (rec)
                tpa_invoice_dict={}
                count = 0
                success = 0
                success_update = 0
                line_error = 0
                line_update_error = 0
                is_update = 0

                qbd_memo = rec.get('qbd_memo')
                is_vendor_bill = rec.get('is_vendor_bill')
                
                if rec.get('invoice_order_qbd_id'):
                    quickbooks_id = rec.get('invoice_order_qbd_id')   
                    is_update = 1
                
                ref_number = rec.get('odoo_invoice_number')
                default_tax_on_invoice = rec.get('default_tax_on_invoice')

                check_record = False
                is_present = False

                if ref_number:
                    if is_vendor_bill:
                        check_record ="Select Top 1 TxnId,RefNumber,TimeModified from Bill where RefNumber='{}'".format(ref_number)
                    else:
                        check_record ="Select Top 1 TxnId,RefNumber,TimeModified from Invoice where RefNumber='{}'".format(ref_number)
                    
                    logging.info("CHECK RECORD {}".format(check_record))
                    cursor.execute(check_record)
                    is_present = cursor.fetchone()

                for lines in rec.get('invoice_lines'):
                    count+=1
                    product_quickbooks_id = lines.get('product_name')

                    # print ("--------------",lines.get('quantity'))
                    if lines.get('quantity'):
                        invoice_line_quantity = float(lines.get('quantity'))
                    else:
                        invoice_line_quantity = 0.0

                    if lines.get('price_unit'):
                        invoice_line_rate = float(lines.get('price_unit'))
                    else:
                        invoice_line_rate = 0.0

                    if lines.get('price_subtotal'):
                        invoice_line_amount = float(lines.get('price_subtotal'))
                    else:
                        invoice_line_amount = 0.0

                    invoice_line_desc = lines.get('name')
                    customer_quickbooks_id = rec.get('partner_name')
                    invoice_line_txn_date = "{d'"+rec.get('invoice_date')+"'}"
                    if count == len(rec.get('invoice_lines')):
                        save_to_cache = str(False)
                    else:
                        save_to_cache = str(True)
                    
                    if lines.get('tax_id'):
                        tax_id = lines.get('tax_id')
                    else:
                        tax_id = ''

                    if lines.get('qbd_tax_code'):
                        qbd_tax_code = lines.get('qbd_tax_code')
                    else:
                        qbd_tax_code = ''

                    if lines.get('payment_terms'):
                        payment_terms = lines.get('payment_terms')
                    else:
                        payment_terms = ''                    

                    # print ("ssssssssssss ",invoice_line_txn_date)

                    if not is_update:
                        if not is_present:
                            if tax_id:
                                if payment_terms:
                                    if is_vendor_bill:
                                        insertQuery = "Insert into BillItemLine (VendorRefListID, RefNumber, ItemLineItemRefListID, ItemLineDesc, ItemLineCost, ItemLineAmount, FQSaveToCache, Memo, TxnDate, ItemLineQuantity, TermsRefFullName) VALUES ('{}','{}','{}','{}',{},{},{},'{}',{}, {}, '{}')".format(customer_quickbooks_id,ref_number,product_quickbooks_id ,invoice_line_desc,invoice_line_rate,invoice_line_amount,save_to_cache,qbd_memo,invoice_line_txn_date,invoice_line_quantity,payment_terms)
                                    else:
                                        insertQuery = "Insert into InvoiceLine (InvoiceLineItemRefListID, InvoiceLineQuantity, InvoiceLineRate, InvoiceLineAmount, InvoiceLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, ItemSalesTaxRefListID, InvoiceLineTaxCodeRefFullName, Memo, RefNumber, TermsRefFullName) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}','{}','{}', '{}', '{}')".format(product_quickbooks_id, invoice_line_quantity, invoice_line_rate, invoice_line_amount, invoice_line_desc, customer_quickbooks_id, invoice_line_txn_date, save_to_cache, tax_id, qbd_tax_code, qbd_memo, ref_number, payment_terms)
                                else:
                                    if is_vendor_bill:
                                        insertQuery = "Insert into BillItemLine (VendorRefListID, RefNumber, ItemLineItemRefListID, ItemLineDesc, ItemLineCost, ItemLineAmount, FQSaveToCache, Memo, TxnDate, ItemLineQuantity) VALUES ('{}','{}','{}','{}',{},{},{},'{}',{}, {})".format(customer_quickbooks_id,ref_number,product_quickbooks_id ,invoice_line_desc,invoice_line_rate,invoice_line_amount,save_to_cache,qbd_memo,invoice_line_txn_date,invoice_line_quantity)
                                    else:
                                        insertQuery = "Insert into InvoiceLine (InvoiceLineItemRefListID, InvoiceLineQuantity, InvoiceLineRate, InvoiceLineAmount, InvoiceLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, ItemSalesTaxRefListID, InvoiceLineTaxCodeRefFullName, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}','{}','{}', '{}')".format(product_quickbooks_id, invoice_line_quantity, invoice_line_rate, invoice_line_amount, invoice_line_desc, customer_quickbooks_id, invoice_line_txn_date, save_to_cache, tax_id, qbd_tax_code, qbd_memo, ref_number)
                            else:
                                if payment_terms:
                                    if is_vendor_bill:
                                        insertQuery = "Insert into BillItemLine (VendorRefListID, RefNumber, ItemLineItemRefListID, ItemLineDesc, ItemLineCost, ItemLineAmount, FQSaveToCache, Memo, TxnDate, ItemLineQuantity, TermsRefFullName) VALUES ('{}','{}','{}','{}',{},{},{},'{}',{}, {}, '{}')".format(customer_quickbooks_id,ref_number,product_quickbooks_id ,invoice_line_desc,invoice_line_rate,invoice_line_amount,save_to_cache,qbd_memo,invoice_line_txn_date,invoice_line_quantity,payment_terms)
                                    else:
                                        insertQuery = "Insert into InvoiceLine (InvoiceLineItemRefListID, InvoiceLineQuantity, InvoiceLineRate, InvoiceLineAmount, InvoiceLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, Memo, RefNumber, TermsRefFullName) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}', '{}', '{}')".format(product_quickbooks_id, invoice_line_quantity, invoice_line_rate, invoice_line_amount, invoice_line_desc, customer_quickbooks_id, invoice_line_txn_date, save_to_cache, qbd_memo, ref_number, payment_terms)
                                else:
                                    if is_vendor_bill:
                                        insertQuery = "Insert into BillItemLine (VendorRefListID, RefNumber, ItemLineItemRefListID, ItemLineDesc, ItemLineCost, ItemLineAmount, FQSaveToCache, Memo, TxnDate, ItemLineQuantity) VALUES ('{}','{}','{}','{}',{},{},{},'{}',{}, {})".format(customer_quickbooks_id,ref_number,product_quickbooks_id ,invoice_line_desc,invoice_line_rate,invoice_line_amount,save_to_cache,qbd_memo,invoice_line_txn_date,invoice_line_quantity)
                                    else:
                                        insertQuery = "Insert into InvoiceLine (InvoiceLineItemRefListID, InvoiceLineQuantity, InvoiceLineRate, InvoiceLineAmount, InvoiceLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}', '{}')".format(product_quickbooks_id, invoice_line_quantity, invoice_line_rate, invoice_line_amount, invoice_line_desc, customer_quickbooks_id, invoice_line_txn_date, save_to_cache, qbd_memo, ref_number)

                            try:
                                logging.info("Insert Query ----------------------------- 22222222222222222")
                                logging.info(insertQuery)

                                #print (insertQuery)
                                cursor.execute(insertQuery)
                                cursor.commit()
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

                                tpa_invoice_dict['odoo_id'] = rec.get('odoo_id')
                                tpa_invoice_dict['quickbooks_id'] = is_present[0]
                                tpa_invoice_dict['message'] = 'Quickbooks Id Successfully Added'
                                tpa_invoice_dict['qbd_invoice_ref_no'] = is_present[1]
                                tpa_invoice_dict['last_modified_date'] = str(is_present[2])

                    else:
                        # print ("kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk")
                        chk_bool=None
                        if is_vendor_bill:
                            check_line_present = "SELECT ItemLineItemRefListID FROM BillItemLine where TxnId='{}' and ItemLineItemRefListID='{}'".format(quickbooks_id, product_quickbooks_id)
                        else:
                            check_line_present = "SELECT InvoiceLineItemRefListID FROM InvoiceLine where TxnId='{}' and InvoiceLineItemRefListID='{}'".format(quickbooks_id, product_quickbooks_id)
                        
                        logging.info(check_line_present)
                        cursor.execute(check_line_present)  
                        
                        # print ("=================")
                        # print (cursor)
                        # print (cursor.fetchone())
                        # print ("=================")
                        record = cursor.fetchone()
                        if record:
                            chk_bool = record[0]

                        # print ("Check Inv Line")
                        # print (chk_bool)
                        if chk_bool:
                            print("CHECK BOOL ",chk_bool)
                            if is_vendor_bill:
                                updateQuery = "Update BillItemLine set ItemLineQuantity={}, ItemLineCost={}, ItemLineAmount={} where ItemLineItemRefListID='{}' and VendorRefListID='{}' and TxnDate={} and TxnId='{}'".\
                                format(invoice_line_quantity, invoice_line_rate, invoice_line_amount, product_quickbooks_id, customer_quickbooks_id, invoice_line_txn_date, quickbooks_id)
                            else:
                                updateQuery = "Update InvoiceLine Set InvoiceLineQuantity= {}, InvoiceLineRate={}, InvoiceLineAmount={} where InvoiceLineItemRefListID='{}' and CustomerRefListID='{}' and TxnDate={} and TxnId='{}'".format(invoice_line_quantity, invoice_line_rate, invoice_line_amount, product_quickbooks_id, customer_quickbooks_id, invoice_line_txn_date, quickbooks_id)
                            logging.info("UPDATE QUERY {}".format(updateQuery))
                        else:
                            # Insert New Line
                            if is_vendor_bill:
                                save_to_cache = 0
                            if tax_id:
                                if payment_terms:
                                    if is_vendor_bill:
                                        updateQuery = "Insert into BillItemLine (VendorRefListID, RefNumber, ItemLineItemRefListID, ItemLineDesc, ItemLineCost, ItemLineAmount, FQSaveToCache, Memo, TxnDate, ItemLineQuantity) VALUES ('{}','{}','{}','{}',{},{},{},'{}',{}, {})".format(customer_quickbooks_id,ref_number,product_quickbooks_id ,invoice_line_desc,invoice_line_rate,invoice_line_amount,save_to_cache,qbd_memo,invoice_line_txn_date,invoice_line_quantity)
                                    else:
                                        updateQuery = "Insert into InvoiceLine (InvoiceLineItemRefListID, InvoiceLineQuantity, InvoiceLineRate, InvoiceLineAmount, InvoiceLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, ItemSalesTaxRefListID, InvoiceLineTaxCodeRefFullName, Memo, RefNumber, TermsRefFullName) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}','{}','{}', '{}', '{}')".format(product_quickbooks_id, invoice_line_quantity, invoice_line_rate, invoice_line_amount, invoice_line_desc, customer_quickbooks_id, invoice_line_txn_date, save_to_cache, tax_id, qbd_tax_code, qbd_memo, ref_number, payment_terms)
                                else:
                                    if is_vendor_bill:
                                        updateQuery = "Insert into BillItemLine (VendorRefListID, RefNumber, ItemLineItemRefListID, ItemLineDesc, ItemLineCost, ItemLineAmount, FQSaveToCache, Memo, TxnDate, ItemLineQuantity) VALUES ('{}','{}','{}','{}',{},{},{},'{}',{}, {})".format(customer_quickbooks_id,ref_number,product_quickbooks_id ,invoice_line_desc,invoice_line_rate,invoice_line_amount,save_to_cache,qbd_memo,invoice_line_txn_date,invoice_line_quantity)
                                    else:
                                        updateQuery = "Insert into InvoiceLine (InvoiceLineItemRefListID, InvoiceLineQuantity, InvoiceLineRate, InvoiceLineAmount, InvoiceLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, ItemSalesTaxRefListID, InvoiceLineTaxCodeRefFullName, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}','{}','{}', '{}')".format(product_quickbooks_id, invoice_line_quantity, invoice_line_rate, invoice_line_amount, invoice_line_desc, customer_quickbooks_id, invoice_line_txn_date, save_to_cache, tax_id, qbd_tax_code, qbd_memo, ref_number)
                            else:
                                if payment_terms:
                                    if is_vendor_bill:
                                        updateQuery = "Insert into BillItemLine (VendorRefListID, RefNumber, ItemLineItemRefListID, ItemLineDesc, ItemLineCost, ItemLineAmount, FQSaveToCache, Memo, TxnDate, ItemLineQuantity) VALUES ('{}','{}','{}','{}',{},{},{},'{}',{}, {})".format(customer_quickbooks_id,ref_number,product_quickbooks_id ,invoice_line_desc,invoice_line_rate,invoice_line_amount,save_to_cache,qbd_memo,invoice_line_txn_date,invoice_line_quantity)
                                    else:
                                        updateQuery = "Insert into InvoiceLine (InvoiceLineItemRefListID, InvoiceLineQuantity, InvoiceLineRate, InvoiceLineAmount, InvoiceLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, Memo, RefNumber, TermsRefFullName) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}', '{}', '{}')".format(product_quickbooks_id, invoice_line_quantity, invoice_line_rate, invoice_line_amount, invoice_line_desc, customer_quickbooks_id, invoice_line_txn_date, save_to_cache, qbd_memo, ref_number, payment_terms)
                                        
                                else:
                                    if is_vendor_bill:
                                        updateQuery = "Insert into BillItemLine (VendorRefListID, RefNumber, ItemLineItemRefListID, ItemLineDesc, ItemLineCost, ItemLineAmount, FQSaveToCache, Memo, TxnDate, ItemLineQuantity) VALUES ('{}','{}','{}','{}',{},{},{},'{}',{}, {})".format(customer_quickbooks_id,ref_number,product_quickbooks_id ,invoice_line_desc,invoice_line_rate,invoice_line_amount,save_to_cache,qbd_memo,invoice_line_txn_date,invoice_line_quantity)
                                    else:
                                        updateQuery = "Insert into InvoiceLine (InvoiceLineItemRefListID, InvoiceLineQuantity, InvoiceLineRate, InvoiceLineAmount, InvoiceLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}', '{}')".format(product_quickbooks_id, invoice_line_quantity, invoice_line_rate, invoice_line_amount, invoice_line_desc, customer_quickbooks_id, invoice_line_txn_date, save_to_cache, qbd_memo, ref_number)

                        try:
                            logging.info(updateQuery)
                            cursor.execute(updateQuery)
                            success_update = 1
                        
                        except Exception as e:
                            logging.info("2")
                            logging.warning(e)                            
                            line_update_error = 1
                            # print(e)
                            pass

                if success == 1:
                    if is_vendor_bill:
                        lastInserted = "Select Top 1 TxnID,RefNumber from Bill where RefNumber='{}'".format(ref_number)
                    else:
                        lastInserted = "Select Top 1 TxnId,RefNumber from Invoice where RefNumber='{}'".format(ref_number)
                    # lastInserted ="Select Top 1 TxnId,RefNumber from Invoice order by timecreated desc"
                    cursor.execute(lastInserted)
                    tuple_data = cursor.fetchone()
                    
                    tpa_invoice_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_invoice_dict['quickbooks_id'] = tuple_data[0]
                    tpa_invoice_dict['qbd_invoice_ref_no'] = tuple_data[1]
                    tpa_invoice_dict['message'] = 'Successfully Created'
                    now = datetime.now()
                    tpa_invoice_dict['last_modified_date'] = str(now.strftime("%d-%m-%Y %H:%M:%S"))
                    
                    # tpa_invoice_list.append(tpa_invoice_dict)
                    # cursor.commit()
                    
                    insertTax = None
                    
                    if not is_vendor_bill:
                        insertTax = "Update Invoice Set ItemSalesTaxRefFullName = '{}' where TxnId = '{}'".format(default_tax_on_invoice,tuple_data[0])
                    
                    if insertTax:
                        logging.info("Query for Default Tax On Invoice----------------------------- ")
                        logging.info(insertTax)
                        cursor.execute(insertTax)
                    
                elif success_update == 1:
                    tpa_invoice_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_invoice_dict['quickbooks_id'] = rec.get('invoice_order_qbd_id')
                    tpa_invoice_dict['message'] = 'Successfully Updated'
                    tpa_invoice_dict['qbd_invoice_ref_no'] = ''
                    # tpa_invoice_list.append(tpa_invoice_dict)
                    # cursor.commit()
                
                if line_error == 1:
                    tpa_invoice_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_invoice_dict['quickbooks_id'] = ''
                    tpa_invoice_dict['qbd_invoice_ref_no'] = ''
                    tpa_invoice_dict['message'] = 'Error while Creating Some Order Lines'
                    # tpa_invoice_list.append(tpa_invoice_dict)

                elif line_update_error == 1:
                    tpa_invoice_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_invoice_dict['quickbooks_id'] = rec.get('invoice_order_qbd_id')
                    tpa_invoice_dict['message'] = 'Error while Updating Some Order Lines'
                    # tpa_invoice_list.append(tpa_invoice_dict)
                    tpa_invoice_dict['qbd_invoice_ref_no'] = ''
            
                tpa_invoice_list.append(tpa_invoice_dict)
            # print(tpa_invoice_list)
            cursor.close()
            logging.info("Data List")
            logging.info(tpa_invoice_list)

            return {"Data":tpa_invoice_list}
        
        return {"Data":[],"Message":"No Invoice Exported"}


        if data != 0:
            close_connection_to_qbd(data[0])