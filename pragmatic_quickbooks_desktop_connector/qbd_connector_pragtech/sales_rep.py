from flask import Blueprint, request
from connection import connect_to_qbd,close_connection_to_qbd
# from string import Template
import logging
logging.basicConfig(level=logging.DEBUG)

sales_rep = Blueprint('sales_rep', __name__, template_folder='templates')


'''
TPA - Third Party Application
'''

@sales_rep.route('/QBD/import_salesrep')
def import_QBD_Salesrep_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        to_execute_account = int(request.args.get('to_execute_account'))
        limit = int(request.args.get('limit'))
        
        #0 Initial (5 varchar) login
        #1 SalesRepEntityRefFullName (209 varchar) name
        #2 TimeModified last_time_modified
        
        if to_execute_account == 1:
            salesrep_query = "SELECT TOP {} Initial, SalesRepEntityRefFullName, TimeModified FROM SalesRep Order by TimeModified ASC".format(limit)

        elif to_execute_account == 2:
            time_modified = "{ts'"+str(request.args.get('last_qbd_id'))+"'}" 
            salesrep_query = "SELECT TOP {} Initial, SalesRepEntityRefFullName, TimeModified FROM SalesRep where timemodified >={}".format(limit,time_modified)

        cursor.execute(salesrep_query)            
        odoo_salesrep_list = []

        for row in cursor.fetchall():
            odoo_salesrep_dict = {}
            row_as_list = [x for x in row]

            odoo_salesrep_dict['login'] = row_as_list[0] #0 Initial login
            odoo_salesrep_dict['name'] = row_as_list[1] #1 SalesRepEntityRefFullName name
            odoo_salesrep_dict['last_time_modified'] = str(row_as_list[2]) #2 TimeModified  last_time_modified
        
            odoo_salesrep_list.append(odoo_salesrep_dict)
        
        cursor.close()
        return (str(odoo_salesrep_list))
        
    except Exception as e:
        logging.info("1")
        logging.warning(e)
        data = 0
        return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])

'''
TPA - Third Party Application
'''
@sales_rep.route('/QBD/export_salesrep', methods = ['POST'])
def export_TPA_SalesRep_to_QBD():
    
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()
                
        req = request.get_json(force=True)
    
        if 'salesrep_list' in req:
            
            tpa_salesrep_list = []
            for rec in req.get('salesrep_list'):
                tpa_salesrep_dict={}

                name = rec.get('name')
                initial = rec.get('initial')
                full_name = name.split(' ',1)
                try:
                    if name:
                        check_employee ="Select Top 1 ListId from Employee where Name='{}'".format(name)
                        cursor.execute(check_employee)
                        is_employee = cursor.fetchone()   

                        if is_employee:
                            check_sales_rep ="Select Top 1 ListId from SalesRep where SalesRepEntityRefFullName='{}'".format(name)
                            cursor.execute(check_sales_rep)
                            is_sales_rep = cursor.fetchone()

                            logging.info(is_employee[0])
                            logging.info("1.1 Employee Already Present in Quickbooks----------------------------- ")
                            
                            if is_sales_rep:
                                logging.info("2.1 Sales Rep Already Present in Quickbooks----------------------------- ")
                                continue
                            else:
                                sales_rep_query = "Insert into SalesRep(Initial, SalesRepEntityRefListId) Values ('{}','{}')".format(initial, is_employee[0])
                                cursor.execute(sales_rep_query)
                                logging.info("2.1 Sales Rep Created in Quickbooks----------------------------- ")

                        else:
                            if len(full_name) == 2:
                                first_name = full_name[0]
                                last_name = full_name[1]
                            else:
                                first_name = full_name[0]
                                last_name = ''

                            employee_query = "Insert into Employee(FirstName, LastName) Values ('{}','{}')".format(first_name, last_name)
                            cursor.execute(employee_query)
                                
                            check_employee ="Select Top 1 ListId from Employee where Name='{}'".format(name)
                            cursor.execute(check_employee)
                            is_employee = cursor.fetchone()
                            logging.info("1.2 Employee Created in Quickbooks----------------------------- ")
                    
                            sales_rep_query = "Insert into SalesRep(Initial, SalesRepEntityRefListId) Values ('{}','{}')".format(initial, is_employee[0])
                            cursor.execute(sales_rep_query)
                            logging.info("2.2 SalesRep Created in Quickbooks----------------------------- ")

                except Exception as e:
                    logging.info("1")
                    logging.warning(e)
                    # print(e)
                    pass

        return ({})

    except Exception as e:
        logging.info("3")
        logging.warning(e)
        # print (e)
        # data = 0
        return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])