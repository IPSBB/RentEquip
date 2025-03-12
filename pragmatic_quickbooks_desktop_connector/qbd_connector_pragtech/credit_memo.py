from flask import Blueprint, request
from connection import connect_to_qbd,close_connection_to_qbd
from datetime import datetime
import logging
logging.basicConfig(level=logging.DEBUG)

credit_memo = Blueprint('credit_memo', __name__, template_folder='templates')

'''
# TPA - Third Party Application
# '''
@credit_memo.route('/QBD/import_credit_memo')
def import_QBD_CreditMemo_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        to_execute_account = int(request.args.get('to_execute_account'))
        limit = int(request.args.get('limit'))
        if to_execute_account == 1:
            credit_memo_order = "SELECT TOP {} CustomerRefListID, TermsRefFullName, ARAccountRefListID, TxnDate, TimeCreated, DueDate, IsPending, RefNumber, TxnId, Timemodified FROM CreditMemo order by timemodified asc".format(limit)
            cursor.execute(credit_memo_order)

        elif to_execute_account == 2:
            time_modified = "{ts'"+str(request.args.get('last_qbd_id'))+"'}" 
            # print (time_modified)
            credit_memo_order = "SELECT TOP {} CustomerRefListID, TermsRefFullName, ARAccountRefListID, TxnDate, TimeCreated, DueDate, IsPending, RefNumber, TxnId, Timemodified FROM CreditMemo where timemodified >={}".format(limit, time_modified)
            cursor.execute(credit_memo_order)

        # if request.args['fetch_record'] == 'all':
            # cursor.execute("SELECT TOP 2 CustomerRefListID, TermsRefFullName, ARAccountRefListID, TxnDate, TimeCreated, DueDate, IsPaid, RefNumber, TxnId FROM CreditMemo")  

        # elif request.args['fetch_record'] == 'one':
        #     ListId = request.args['quickbooks_id']
        #     cursor.execute("SELECT ListId, ParentRefListId, FullName, Email, Phone, AltPhone, Fax, Notes, BillAddressAddr1, BillAddressAddr2, BillAddressCountry, BillAddressState, BillAddressCity, BillAddressPostalCode FROM Customer Where ListID='"+ListId+"' Order by ListId ASC")

        odoo_credit_memo_list = []
        for row in cursor.fetchall():
            odoo_credit_memo_dict = {}
            row_as_list = [x for x in row]


            odoo_credit_memo_dict['quickbooks_id'] = row_as_list[8]
            odoo_credit_memo_dict['partner_name'] = row_as_list[0]
            #Search partner_id in odoo from res.partner where partner_name is quicbooks_id in res.partner
            odoo_credit_memo_dict['number'] = row_as_list[7]

            if row_as_list[5]:
                odoo_credit_memo_dict['date_due'] = str(row_as_list[3])
            
            
            if row_as_list[1] == 'Net 30':
                odoo_credit_memo_dict['term_name'] = '30 Net Days'
            elif row_as_list[1] == 'Net 15':
                odoo_credit_memo_dict['term_name'] = '15 Days'
            else:
                odoo_credit_memo_dict['term_name'] = None
            #Search term_id in account.payment.term from term_name
            # if term_id found set credit_memo_dict[payment_term_id] = that term

            if row_as_list[6]:
                odoo_credit_memo_dict['state'] = 'paid'
                odoo_credit_memo_dict['date_invoice'] = str(row_as_list[3])

            cursor.execute("SELECT TxnID, CreditMemoLineItemRefListID, CreditmemoLineSeqNo, ARAccountRefListID, CreditMemoLineQuantity, CreditMemoLineRate, IsPending, CreditMemoLineAmount, CreditmemoLineDesc, ItemSalesTaxRefListID, CreditMemoLineTaxCodeRefFullName FROM CreditMemoLine WHERE TxnID = '"+row_as_list[8]+"'")
            
            odoo_credit_memo_line_list = []
            
            for row in cursor.fetchall(): 
                odoo_credit_memo_line_dict ={}
                row_as_inv_line = [x for x in row]

                odoo_credit_memo_line_dict['product_name'] = row_as_inv_line[1]
                # Find this product in product.product where product_name is quickbooks_id and store in product_id field
                odoo_credit_memo_line_dict['account_name'] = row_as_inv_line[3]
                # Find this account in account.account where account_name is quickbooks_id and store in account_id field
                if row_as_inv_line[4] == 0:
                    odoo_credit_memo_line_dict['quantity'] = str(0.0)
                elif row_as_inv_line[4] is None:
                    odoo_credit_memo_line_dict['quantity'] = str(1.0)
                else:
                    odoo_credit_memo_line_dict['quantity'] = str(row_as_inv_line[4])

                odoo_credit_memo_line_dict['price_unit'] = str(row_as_inv_line[5])
                odoo_credit_memo_line_dict['price_subtotal'] = str(row_as_inv_line[7])
                odoo_credit_memo_line_dict['name'] = row_as_inv_line[8]
                odoo_credit_memo_line_dict['tax_qbd_id'] = row_as_inv_line[9]
                odoo_credit_memo_line_dict['tax_code'] = row_as_inv_line[10]

                odoo_credit_memo_line_list.append(odoo_credit_memo_line_dict)

                # print ("Quantity -----------------------------------")
                # print (row_as_inv_line[4])
                # print ("--------------------------------------------")
                
                # print ("----")
                # print (odoo_credit_memo_line_list)
            odoo_credit_memo_dict['invoice_lines'] = odoo_credit_memo_line_list
            odoo_credit_memo_dict['last_time_modified'] = str(row_as_list[9])
            # Last_QBD_id = str(row_as_list[9])
            odoo_credit_memo_list.append(odoo_credit_memo_dict)
            
        # print (odoo_credit_memo_list)

        cursor.close()
        return (str(odoo_credit_memo_list))
        
    except Exception as e:
        # print (e)
        data = 0
        return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])

@credit_memo.route('/QBD/export_credit_memo', methods=['POST'])
def export_TPA_credit_memo_to_QBD():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        req = request.get_json(force=True)
        # print (req)
        if 'invoices_list' in req:

            tpa_credit_memo_list = []
            for rec in req.get('invoices_list'):
                # print (rec)
                tpa_credit_memo_dict={}
                count = 0
                success = 0
                success_update = 0
                line_error = 0
                line_update_error = 0
                is_update = 0

                qbd_memo = rec.get('qbd_memo')
                
                if rec.get('invoice_order_qbd_id'):
                    quickbooks_id = rec.get('invoice_order_qbd_id')   
                    is_update = 1
                
                ref_number = rec.get('odoo_invoice_number')
                default_tax_on_credit_memo = rec.get('default_tax_on_invoice')

                check_record = False
                is_present = False

                if ref_number:
                    check_record ="Select Top 1 TxnId,RefNumber from CreditMemo where RefNumber='{}'".format(ref_number)
                    cursor.execute(check_record)
                    is_present = cursor.fetchone()

                for lines in rec.get('invoice_lines'):
                    count+=1
                    product_quickbooks_id = lines.get('product_name')

                    # print ("--------------",lines.get('quantity'))
                    if lines.get('quantity'):
                        credit_memo_line_quantity = float(lines.get('quantity'))
                    else:
                        credit_memo_line_quantity = 0.0

                    if lines.get('price_unit'):
                        credit_memo_line_rate = float(lines.get('price_unit'))
                    else:
                        credit_memo_line_rate = 0.0

                    if lines.get('price_subtotal'):
                        credit_memo_line_amount = float(lines.get('price_subtotal'))
                    else:
                        credit_memo_line_amount = 0.0

                    credit_memo_line_desc = lines.get('name')
                    customer_quickbooks_id = rec.get('partner_name')
                    credit_memo_line_txn_date = "{d'"+rec.get('invoice_date')+"'}"
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

                    if not is_update:
                        if not is_present:
                            if tax_id:
                                if payment_terms:
                                    insertQuery = "Insert into CreditmemoLine (CreditMemoLineItemRefListID, CreditMemoLineQuantity, CreditMemoLineRate, CreditMemoLineAmount, CreditmemoLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, ItemSalesTaxRefListID, CreditMemoLineTaxCodeRefFullName, Memo, RefNumber, TermsRefFullName) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}','{}','{}', '{}', '{}')".format(product_quickbooks_id, credit_memo_line_quantity, credit_memo_line_rate, credit_memo_line_amount, credit_memo_line_desc, customer_quickbooks_id, credit_memo_line_txn_date, save_to_cache, tax_id, qbd_tax_code, qbd_memo, ref_number, payment_terms)
                                else:
                                    insertQuery = "Insert into CreditmemoLine (CreditMemoLineItemRefListID, CreditMemoLineQuantity, CreditMemoLineRate, CreditMemoLineAmount, CreditmemoLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, ItemSalesTaxRefListID, CreditMemoLineTaxCodeRefFullName, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}','{}','{}', '{}')".format(product_quickbooks_id, credit_memo_line_quantity, credit_memo_line_rate, credit_memo_line_amount, credit_memo_line_desc, customer_quickbooks_id, credit_memo_line_txn_date, save_to_cache, tax_id, qbd_tax_code, qbd_memo, ref_number)
                            else:
                                if payment_terms:
                                    insertQuery = "Insert into CreditmemoLine (CreditMemoLineItemRefListID, CreditMemoLineQuantity, CreditMemoLineRate, CreditMemoLineAmount, CreditmemoLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, Memo, RefNumber, TermsRefFullName) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}', '{}', '{}')".format(product_quickbooks_id, credit_memo_line_quantity, credit_memo_line_rate, credit_memo_line_amount, credit_memo_line_desc, customer_quickbooks_id, credit_memo_line_txn_date, save_to_cache, qbd_memo, ref_number, payment_terms)
                                else:
                                    insertQuery = "Insert into CreditmemoLine (CreditMemoLineItemRefListID, CreditMemoLineQuantity, CreditMemoLineRate, CreditMemoLineAmount, CreditmemoLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}', '{}')".format(product_quickbooks_id, credit_memo_line_quantity, credit_memo_line_rate, credit_memo_line_amount, credit_memo_line_desc, customer_quickbooks_id, credit_memo_line_txn_date, save_to_cache, qbd_memo, ref_number)

                            try:
                                logging.info("Insert Query ----------------------------- ")
                                logging.info(insertQuery)

                                # print (insertQuery)
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

                            tpa_credit_memo_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_credit_memo_dict['quickbooks_id'] = is_present[0]
                            tpa_credit_memo_dict['message'] = 'Quickbooks Id Successfully Added'
                            tpa_credit_memo_dict['qbd_invoice_ref_no'] = is_present[1]
                            tpa_credit_memo_dict['last_modified_date'] = str(is_present[2])

                    else:
                        # print ("kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk")
                        chk_bool=''
                        check_line_present = "SELECT CreditMemoLineItemRefListID FROM CreditmemoLine where TxnId='{}' and CreditMemoLineItemRefListID='{}'".format(quickbooks_id, product_quickbooks_id)
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
                            updateQuery = "Update CreditmemoLine Set CreditMemoLineQuantity= {}, CreditMemoLineRate={}, CreditMemoLineAmount={} where CreditMemoLineItemRefListID='{}' and CustomerRefListID='{}' and TxnDate={} and TxnId='{}'".format(credit_memo_line_quantity, credit_memo_line_rate, credit_memo_line_amount, product_quickbooks_id, customer_quickbooks_id, credit_memo_line_txn_date, quickbooks_id)
                            # print (updateQuery)
                        else:
                            # Insert New Line
                            if tax_id:
                                if payment_terms:
                                    updateQuery = "Insert into CreditmemoLine (CreditMemoLineItemRefListID, CreditMemoLineQuantity, CreditMemoLineRate, CreditMemoLineAmount, CreditmemoLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, ItemSalesTaxRefListID, CreditMemoLineTaxCodeRefFullName, Memo, RefNumber, TermsRefFullName) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}','{}','{}', '{}', '{}')".format(product_quickbooks_id, credit_memo_line_quantity, credit_memo_line_rate, credit_memo_line_amount, credit_memo_line_desc, customer_quickbooks_id, credit_memo_line_txn_date, save_to_cache, tax_id, qbd_tax_code, qbd_memo, ref_number, payment_terms)
                                else:
                                    updateQuery = "Insert into CreditmemoLine (CreditMemoLineItemRefListID, CreditMemoLineQuantity, CreditMemoLineRate, CreditMemoLineAmount, CreditmemoLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, ItemSalesTaxRefListID, CreditMemoLineTaxCodeRefFullName, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}','{}','{}', '{}')".format(product_quickbooks_id, credit_memo_line_quantity, credit_memo_line_rate, credit_memo_line_amount, credit_memo_line_desc, customer_quickbooks_id, credit_memo_line_txn_date, save_to_cache, tax_id, qbd_tax_code, qbd_memo, ref_number)
                            else:
                                if payment_terms:
                                    updateQuery = "Insert into CreditmemoLine (CreditMemoLineItemRefListID, CreditMemoLineQuantity, CreditMemoLineRate, CreditMemoLineAmount, CreditmemoLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, Memo, RefNumber, TermsRefFullName) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}', '{}', '{}')".format(product_quickbooks_id, credit_memo_line_quantity, credit_memo_line_rate, credit_memo_line_amount, credit_memo_line_desc, customer_quickbooks_id, credit_memo_line_txn_date, save_to_cache, qbd_memo, ref_number, payment_terms)
                                else:
                                    updateQuery = "Insert into CreditmemoLine (CreditMemoLineItemRefListID, CreditMemoLineQuantity, CreditMemoLineRate, CreditMemoLineAmount, CreditmemoLineDesc, CustomerRefListID, TxnDate, FQSaveToCache, Memo, RefNumber) VALUES ('{}' ,{} ,{} ,{} ,'{}' ,'{}' ,{} ,{}, '{}', '{}')".format(product_quickbooks_id, credit_memo_line_quantity, credit_memo_line_rate, credit_memo_line_amount, credit_memo_line_desc, customer_quickbooks_id, credit_memo_line_txn_date, save_to_cache, qbd_memo, ref_number)

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
                    lastInserted = "Select Top 1 TxnId,RefNumber from CreditMemo where RefNumber='{}'".format(ref_number)
                    # lastInserted ="Select Top 1 TxnId,RefNumber from CreditMemo order by timecreated desc"
                    cursor.execute(lastInserted)
                    tuple_data = cursor.fetchone()
                    
                    tpa_credit_memo_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_credit_memo_dict['quickbooks_id'] = tuple_data[0]
                    tpa_credit_memo_dict['qbd_invoice_ref_no'] = tuple_data[1]
                    tpa_credit_memo_dict['message'] = 'Successfully Created'
                    now = datetime.now()
                    tpa_credit_memo_dict['last_modified_date'] = str(now.strftime("%d-%m-%Y %H:%M:%S"))
                    # tpa_credit_memo_list.append(tpa_credit_memo_dict)
                    # cursor.commit()

                    insertTax = "Update CreditMemo Set ItemSalesTaxRefFullName = '{}' where TxnId = '{}'".format(default_tax_on_credit_memo,tuple_data[0])
                    logging.info("Query for Default Tax On CreditMemo----------------------------- ")
                    logging.info(insertTax)
                    cursor.execute(insertTax)
                    
                elif success_update == 1:
                    tpa_credit_memo_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_credit_memo_dict['quickbooks_id'] = rec.get('invoice_order_qbd_id')
                    tpa_credit_memo_dict['message'] = 'Successfully Updated'
                    tpa_credit_memo_dict['qbd_invoice_ref_no'] = ''
                    # tpa_credit_memo_list.append(tpa_credit_memo_dict)
                    # cursor.commit()
                
                if line_error == 1:
                    tpa_credit_memo_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_credit_memo_dict['quickbooks_id'] = ''
                    tpa_credit_memo_dict['qbd_invoice_ref_no'] = ''
                    tpa_credit_memo_dict['message'] = 'Error while Creating Some Order Lines'
                    # tpa_credit_memo_list.append(tpa_credit_memo_dict)

                elif line_update_error == 1:
                    tpa_credit_memo_dict['odoo_id'] = rec.get('odoo_id')
                    tpa_credit_memo_dict['quickbooks_id'] = rec.get('invoice_order_qbd_id')
                    tpa_credit_memo_dict['message'] = 'Error while Updating Some Order Lines'
                    # tpa_credit_memo_list.append(tpa_credit_memo_dict)
                    tpa_credit_memo_dict['qbd_invoice_ref_no'] = ''
            
                tpa_credit_memo_list.append(tpa_credit_memo_dict)
            # print(tpa_credit_memo_list)
            cursor.close()
            logging.info("Data List")
            logging.info(tpa_credit_memo_list)

            return (str([{"Data":tpa_credit_memo_list}]))
        
        return (str([{"Data":[]}]))

    except Exception as e:
        logging.info("3")
        logging.warning(e)        
        # print (e)
        data = 0
        return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])
