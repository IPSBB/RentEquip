from flask import Blueprint, request
from connection import connect_to_qbd,close_connection_to_qbd
import logging
import json
logging.basicConfig(level=logging.DEBUG)

essential = Blueprint('essential', __name__, template_folder='templates')

'''
TPA - Third Party Application
'''

@essential.route('/QBD/import_uom')
def import_QBD_Unit_of_Measures_to_TPA():
    try:
        # Step 1: Connect to QuickBooks
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        # Step 2: Query the QuickBooks database for Units of Measure
        uom_query = "SELECT ListId, Name, UnitOfMeasureType , TimeModified FROM UnitOfMeasureSet ORDER by TimeModified ASC"

        cursor.execute(uom_query)

        # Step 3: Prepare the result list to send to Odoo
        odoo_uom_list = []

        for row in cursor.fetchall():
            odoo_uom_dict = {}
            row_as_list = [x for x in row]

            # Map the fetched data to Odoo format
            odoo_uom_dict['quickbooks_id'] = row_as_list[0]
            odoo_uom_dict['name'] = row_as_list[1]
            odoo_uom_dict['category_id'] = row_as_list[2]
            odoo_uom_dict['last_time_modified'] = str(row_as_list[3])

            # Append to the final list
            odoo_uom_list.append(odoo_uom_dict)

        cursor.close()
        print('odoo_uom_list:       ', odoo_uom_list)
        # Step 4: Return the UOM data as a response
        return (str(odoo_uom_list))


    except Exception as e:
        # Handle any exceptions
        print(e)
        data = 0
        return ({"Status": 404,
                 "Message": "Please wait for sometime and check whether QuickBooks Desktop and Command Prompt are running as administrator."})

    finally:
        # Step 5: Ensure the connection is properly closed
        if data != 0:
            close_connection_to_qbd(data[0])

            
@essential.route('/QBD/import_vendor_category')
def import_QBD_Vendor_Categories_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        vendor_category = "SELECT ListId, Name, TimeModified FROM VendorType Order by TimeModified ASC"

        cursor.execute(vendor_category)            
        odoo_vendor_category_list = []

        for row in cursor.fetchall():
            odoo_vendor_category_dict = {}
            row_as_list = [x for x in row]

            odoo_vendor_category_dict['quickbooks_id'] = row_as_list[0]
            odoo_vendor_category_dict['name'] = row_as_list[1]
            odoo_vendor_category_dict['last_time_modified'] = str(row_as_list[2])

            odoo_vendor_category_list.append(odoo_vendor_category_dict)
                
        # print (odoo_vendor_category_list)
        
        cursor.close()
        return (json.dumps(odoo_vendor_category_list))
        
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
@essential.route('/QBD/import_partner_category')
def import_QBD_Partner_Categories_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        partner_category = "SELECT ListId, Name, TimeModified FROM CustomerType Order by TimeModified ASC"

        cursor.execute(partner_category)            
        odoo_partner_category_list = []

        for row in cursor.fetchall():
            odoo_partner_category_dict = {}
            row_as_list = [x for x in row]

            odoo_partner_category_dict['quickbooks_id'] = row_as_list[0]
            odoo_partner_category_dict['name'] = row_as_list[1]
            odoo_partner_category_dict['last_time_modified'] = str(row_as_list[2])

            odoo_partner_category_list.append(odoo_partner_category_dict)
                
        # print (odoo_partner_category_list)
        
        cursor.close()
        return (json.dumps(odoo_partner_category_list))
        
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
@essential.route('/QBD/import_payment_terms')
def import_QBD_Payment_Terms_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        payment_term = "SELECT ListId, Name, TimeModified FROM terms Order by TimeModified ASC"
        # payment_term = "SELECT ListId, Name, TimeModified FROM terms Order by TimeModified ASC where timemodified >={}".format(time_modified)

        cursor.execute(payment_term)            
        odoo_payment_term_list = []

        for row in cursor.fetchall():
            odoo_payment_term_dict = {}
            row_as_list = [x for x in row]

            odoo_payment_term_dict['quickbooks_id'] = row_as_list[0]
            odoo_payment_term_dict['name'] = row_as_list[1]
            odoo_payment_term_dict['last_time_modified'] = str(row_as_list[2])

            odoo_payment_term_list.append(odoo_payment_term_dict)
                
        # print (odoo_payment_term_list)
        
        cursor.close()
        return (json.dumps(odoo_payment_term_list))
        
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
@essential.route('/QBD/import_partner_title')
def import_QBD_Partner_Title_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        partner_title = "Select Distinct(Salutation) from customer"
        
        cursor.execute(partner_title)            
        odoo_partner_title_list = []

        for row in cursor.fetchall():
            odoo_partner_title_dict = {}
            row_as_list = [x for x in row]
            if row_as_list[0]:
                odoo_partner_title_dict['name'] = row_as_list[0]

                odoo_partner_title_list.append(odoo_partner_title_dict)
                
        # print (odoo_partner_title_list)
        
        cursor.close()
        return (json.dumps(odoo_partner_title_list))
        
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
@essential.route('/QBD/import_sales_tax')
def import_QBD_Sales_Tax_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        sales_tax = "Select ListId, Name, ItemDesc, TaxRate from ItemSalesTax"
        
        cursor.execute(sales_tax)            
        odoo_sales_tax_list = []

        for row in cursor.fetchall():
            odoo_sales_tax_dict = {}
            row_as_list = [x for x in row]
            if row_as_list[0]:
                odoo_sales_tax_dict['quickbooks_id'] = row_as_list[0]
                odoo_sales_tax_dict['name'] = row_as_list[1]
                if row_as_list[2]:
                    odoo_sales_tax_dict['desc'] = row_as_list[2]
                else:
                    odoo_sales_tax_dict['desc'] = ''
                odoo_sales_tax_dict['amount'] = float(row_as_list[3])

                odoo_sales_tax_list.append(odoo_sales_tax_dict)
                
        print (odoo_sales_tax_list)
        
        cursor.close()
        return (json.dumps(odoo_sales_tax_list))
        
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
@essential.route('/QBD/import_tax_code')
def import_QBD_Tax_Code_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        tax_code = "Select ListId, Name, IsTaxable from SalesTaxCode"
  
        # print ("Taxeeeeeeeeeeeeeeeeeeeeee")    
        # print (tax_code)    
        cursor.execute(tax_code)            
        odoo_tax_code_list = []
        # print("hhhhhhhhhhhhhhhh")
        for row in cursor.fetchall():
            odoo_tax_code_dict = {}
            row_as_list = [x for x in row]
            if row_as_list[0]:
                odoo_tax_code_dict['quickbooks_id'] = row_as_list[0]
                odoo_tax_code_dict['name'] = row_as_list[1]
                # print ("RRRRRRRRRRRRRRRRRRRRRRRRRRRR")
                # print(row_as_list[2])
                # print(type(row_as_list[2]))

                if row_as_list[2]:
                    odoo_tax_code_dict['taxable'] = True
                else:
                    odoo_tax_code_dict['taxable'] = False

                odoo_tax_code_list.append(odoo_tax_code_dict)
                
        # print (odoo_tax_code_list)
        
        cursor.close()
        return (json.dumps(odoo_tax_code_list))
        
    except Exception as e:
        # print (e)
        data = 0
        return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])

# '''
# TPA - Third Party Application
# '''
# @essential.route('/QBD/export_payment_terms', methods=['POST'])
# def export_TPA_Payment_Terms_to_QBD():
#     try:
#         data = connect_to_qbd()
#         con = data[0]
#         cursor = con.cursor()

#         req = request.get_json(force=True)
#         print (req)
#         if 'payment_term_list' in req:

#             tpa_payment_term_list = []
#             for rec in req.get('payment_term_list'):
#                 tpa_payment_term_dict={}
#                 print (rec)
            
#                 name = rec.get('name')
                
#                 insertQuery = "Insert Into Terms(Name) Values('{}')".format(name)

#                 try:
#                     cursor.execute(insertQuery)
#                     lastInserted ="Select Top 1 ListId from Terms order by timecreated desc"
#                     cursor.commit()
#                     cursor.execute(lastInserted)

#                     tpa_payment_term_dict['odoo_id'] = rec.get('odoo_id')
#                     tpa_payment_term_dict['quickbooks_id'] = cursor.fetchone()[0]
#                     tpa_payment_term_list.append(tpa_payment_term_dict)

#                 except Exception as e:
#                     print(e)
#                     pass
        
#             print(tpa_payment_term_list)
#             # return (str([{"Data":"Success"}]))
#             cursor.close()
#             return (str([{"Data":tpa_payment_method_list}]))
        
#         return (str([{"Data":[]}]))

#     except Exception as e:
#         print (e)
#         data = 0
#         return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

#     finally:
#         if data != 0:
#             close_connection_to_qbd(data[0])
