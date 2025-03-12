from flask import Blueprint, request
from connection import connect_to_qbd,close_connection_to_qbd
# from string import Template
import json
import logging
logging.basicConfig(level=logging.DEBUG)

customer = Blueprint('customer', __name__, template_folder='templates')

'''
TPA - Third Party Application
'''
@customer.route('/QBD/import_customer_shipto')
def import_QBD_Customer_Shipto():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()
        to_execute_account = int(request.args.get('to_execute_account'))
        if request.args.get('list_id'):
            ptr_list_id = request.args.get('list_id')
        odoo_cust_list = []
        if to_execute_account == 5:
            customer = "SELECT ListID , Name , FQprimarykey, ISActive, ShipToAddressName, ShipToAddressAddr1 , ShipToAddressAddr2 , ShipToAddressAddr3 , ShipToAddressAddr4 , ShipToAddressCity, ShipToAddressState, ShipToAddressPostalCode FROM CustomerShipToAddress where ListID = '{}' Order by ListID ASC".format(ptr_list_id)
            cursor.execute(customer)
            for row in cursor.fetchall():
                odoo_cust_dict = {}
                row_as_list = [x for x in row]
                odoo_cust_dict['list_id'] = row_as_list[0]
                odoo_cust_dict['name'] = row_as_list[1]
                odoo_cust_dict['fq_primary_key'] = row_as_list[2]
                odoo_cust_dict['is_active'] = row_as_list[3]
                odoo_cust_dict['shipto_name'] = row_as_list[4]
                odoo_cust_dict['shipto_addr1'] = row_as_list[5]
                odoo_cust_dict['shipto_addr2'] = row_as_list[6]
                odoo_cust_dict['shipto_addr3'] = row_as_list[7]
                odoo_cust_dict['shipto_addr4'] = row_as_list[8]
                odoo_cust_dict['shipto_city'] = row_as_list[9]
                odoo_cust_dict['shipto_state'] = row_as_list[10]
                odoo_cust_dict['shipto_zip'] = row_as_list[11]
                odoo_cust_list.append(odoo_cust_dict)
        print(odoo_cust_list,'++++++++++++++++++++++++++++++++++++++13213123123')

        cursor.close()

        # file1=open('/data.txt','w+')

        return (json.dumps(odoo_cust_list))
    except Exception as e:
        # print (e)
        logging.info("1")
        logging.warning(e)
        data = 0
        return (
        {"Status": 404, "Message": "Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])

@customer.route('/QBD/import_customer')
def import_QBD_Customer_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        to_execute_account = int(request.args.get('to_execute_account'))
        if request.args.get('limit'):
            limit = int(request.args.get('limit'))
        if request.args.get('list_id'):
            list_id = request.args.get('list_id')

        #0 ListId (36 varchar) quickbooks_id
        #1 ParentRefListID (36 varchar) parent_qbd_id
        #2 Name (41 varchar) name
        #3 Salutation (15 varchar) title
        #4 JobTitle (41 varchar) function
        #5 Phone (21 varchar) phone
        #6 AltPhone (21 varchar) mobile
        #7 Email (1023 varchar) email
        #8 Notes (4095 varchar) comment
        #9 BillAddressCity (31 varchar) city
        #10 BillAddressPostalCode (13 varchar) zip
        #11 BillAddressState (21 varchar) state_id
        #12 BillAddressCountry (31 varchar) country_id
        #13 BillAddressAddr1 (41 varchar) street
        #14 BillAddressAddr2 (41 varchar)street2
        #15 TermsRefListId (36 varchar) terms_qbd_id
        #16 TimeModified  last_time_modified
        #17 ResaleNumber vat
        #18 AccountNumber ref
        #19 CustomerTypeRefFullName category_name
        #20 TimeCreated timecreated
        #21 IsActive is_active
        #22 SalesRepRefFullName user_name
        
        # ------------ Custom Fields ------------ #
        #23 CustomFieldCustomerType customer_type
        #24 CustomeFieldHowdidyouhearaboutus how_did_you_hear_about_us
        

        if to_execute_account == 1:
            # customer = "SELECT TOP {} ListId, ParentRefListID, Name, Salutation, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, TimeModified, ResaleNumber, AccountNumber, CustomerTypeRefFullName, TimeCreated, IsActive, SalesRepRefFullName FROM Customer Order by TimeModified ASC".format(limit)
            ## With Custom Fields
            customer = "SELECT TOP {} ListId, ParentRefListID, Name, Salutation, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, TimeModified, ResaleNumber, AccountNumber, CustomerTypeRefFullName, TimeCreated, IsActive, SalesRepRefFullName FROM Customer where ParentRefListID is null Order by TimeModified ASC".format(limit)
            # customer = "SELECT TOP {} ListId, ParentRefListID, Name, Salutation, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, TimeModified, ResaleNumber, AccountNumber, CustomerTypeRefFullName, TimeCreated, IsActive, SalesRepRefFullName, CustomFieldCustomerType, CustomFieldHowdidyouhearaboutus FROM Customer Order by TimeModified ASC".format(limit)

            # cursor.execute(customer)

        elif to_execute_account == 2:
            time_modified = "{ts'"+str(request.args.get('last_qbd_id'))+"'}" 
#             print(time_modified)
            # print (time_modified)
            customer = "SELECT TOP {} ListId, ParentRefListID, Name, Salutation, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, TimeModified, ResaleNumber, AccountNumber, CustomerTypeRefFullName, TimeCreated, IsActive, SalesRepRefFullName FROM Customer where timemodified >={} and ParentRefListID is null Order by TimeModified ASC".format(limit,time_modified)
            ## With Custom Fields
            # customer = "SELECT TOP {} ListId, ParentRefListID, Name, Salutation, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, TimeModified, ResaleNumber, AccountNumber, CustomerTypeRefFullName, TimeCreated, IsActive, SalesRepRefFullName, CustomFieldCustomerType, CustomFieldHowdidyouhearaboutus FROM Customer where timemodified >={} Order by TimeModified ASC".format(limit,time_modified)
            # customer = "SELECT TOP 80 ListId, ParentRefListID, Name, Salutation, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, TimeModified, ResaleNumber, AccountNumber, CustomerTypeRefFullName FROM Customer where Name='Himesh34'"

            # cursor.execute(customer)

        elif to_execute_account == 4:
            if request.args['fetch_record'] == 'one':
                # print ("Oneeeeeeeeeeeee")
                # ListID = list_id
                customer = "SELECT ListId, ParentRefListID, Name, Salutation, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, TimeModified, ResaleNumber, AccountNumber, CustomerTypeRefFullName, TimeCreated, IsActive, SalesRepRefFullName FROM Customer Where ListID='"+list_id+"'"
                ## With Custom Fields
                # customer = "SELECT ListId, ParentRefListID, Name, Salutation, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, TimeModified, ResaleNumber, AccountNumber, CustomerTypeRefFullName, TimeCreated, IsActive, SalesRepRefFullName, CustomFieldCustomerType, CustomFieldHowdidyouhearaboutus FROM Customer Where ListID='"+ListId+"'"
                cursor.execute(customer)
                # print ("Oneeeeeeeeeeeee")

        cursor.execute(customer)            
        odoo_cust_list = []

        for row in cursor.fetchall():
            odoo_cust_dict = {}
            row_as_list = [x for x in row]

            odoo_cust_dict['quickbooks_id'] = row_as_list[0] #0 ListId (36 varchar) quickbooks_id
            if row_as_list[1] != None:
                odoo_cust_dict['parent_qbd_id'] = row_as_list[1] #1 ParentRefListID (36 varchar) partner_qbd_id
            odoo_cust_dict['name'] = row_as_list[2] #2 Name (41 varchar) name
            odoo_cust_dict['title'] = row_as_list[3] #3 Salutation (15 varchar) title
            odoo_cust_dict['function'] = row_as_list[4] #4 JobTitle (41 varchar) function
            odoo_cust_dict['phone'] = row_as_list[5] #5 Phone (21 varchar) phone
            odoo_cust_dict['mobile'] = row_as_list[6] #6 AltPhone (21 varchar) mobile
            odoo_cust_dict['email'] = row_as_list[7] #7 Email (1023 varchar) email
            odoo_cust_dict['comment'] = row_as_list[8] #8 Notes (4095 varchar) comment         
            odoo_cust_dict['city'] = row_as_list[9] #9 BillAddressCity (31 varchar) city          
            odoo_cust_dict['zip'] = row_as_list[10] #10 BillAddressPostalCode (13 varchar) zip
            odoo_cust_dict['state'] = row_as_list[11] #11 BillAddressState (21 varchar) state_id
            odoo_cust_dict['country'] = row_as_list[12] #12 BillAddressCountry (31 varchar) country_id
            odoo_cust_dict['street'] = row_as_list[13] #13 BillAddressAddr1 (41 varchar) street
            odoo_cust_dict['street2'] = row_as_list[14] #14 BillAddressAddr2 (41 varchar)street2
            odoo_cust_dict['terms_qbd_id'] = row_as_list[15] #15 TermsRefListId (36 varchar) terms_qbd_id
            odoo_cust_dict['last_time_modified'] = str(row_as_list[16]) #16 TimeModified  last_time_modified
            odoo_cust_dict['vat'] = row_as_list[17] #17 ResaleNumber vat
            odoo_cust_dict['ref'] = row_as_list[18] #18 AccountNumber ref
            odoo_cust_dict['category_name'] = row_as_list[19] #18 CustomerTypeRefFullName category_name
            odoo_cust_dict['time_created'] = str(row_as_list[20]) #20 TimeCreated time_created
            odoo_cust_dict['is_active'] = row_as_list[21] #21 IsActive is_active
            odoo_cust_dict['user_name'] = row_as_list[22] #22 SalesRepRefFullName user_name
            
            # ----------------------- Custom Fields ----------------------- #
            # odoo_cust_dict['customer_type'] = row_as_list[23] #23 CustomFieldCustomerType customer_type
            # odoo_cust_dict['how_did_you_hear_about_us'] = row_as_list[24] #24 CustomeFieldHowdidyouhearaboutus how_did_you_hear_about_us
            
            # print (row_as_list[10])
        
            odoo_cust_list.append(odoo_cust_dict)
                
        print (odoo_cust_list)
        
        cursor.close()

        #file1=open('/data.txt','w+')
        
        return (json.dumps(odoo_cust_list))
        
        
    except Exception as e:
        # print (e)
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
@customer.route('/QBD/export_customers', methods = ['POST'])
def export_TPA_Customer_to_QBD():
    
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()
        # print (cursor)
                
        req = request.get_json(force=True)
        # print (req)
        if 'customers_list' in req:
            
            tpa_customer_list = []
            for rec in req.get('customers_list'):
                tpa_customer_dict={}
                # print (rec)

                salutation = last_name = company_name = job_title = phone = altphone = email = notes = baddr_city = baddr_postal = baddr_state = baddr_country = baddr1 = baddr2 = terms_ref = vat = ref = category_name = ''
                
                if not rec.get('company'):
                    parent_ref = rec.get('parent_ref') #ParentRefListID (36 varchar)

                name = rec.get('name')  #Name (41 varchar)
                company_name = rec.get('company_ref_name')

                if rec.get('title'):
                    salutation = rec.get('title') #Salutation (15 varchar)

                first_name = rec.get('first_name') #FirstName (25 varchar)

                if rec.get('last_name'):
                    last_name = rec.get('last_name') #LastName (25 varchar)

                if rec.get('function'):
                    job_title = rec.get('function') #JobTitle (41 varchar)

                if rec.get('phone'):
                    phone = rec.get('phone') #Phone (21 varchar)

                if rec.get('mobile'):
                    altphone = rec.get('mobile') #AltPhone (21 varchar)

                if rec.get('email'):
                    email = rec.get('email') #Email (1023 varchar)
                                    
                if rec.get('comment'):
                    notes = rec.get('comment') #Notes (4095 varchar)

                if rec.get('city'):
                    baddr_city = rec.get('city') #BillAddressCity (31 varchar)                

                if rec.get('zip'):
                    baddr_postal = rec.get('zip') #BillAddressPostalCode (13 varchar)

                if rec.get('state_id'):
                    baddr_state = rec.get('state_id') #BillAddressState (21 varchar)

                if rec.get('country_id'):
                    baddr_country = rec.get('country_id') #BillAddressCountry (31 varchar) 

                baddr1 = rec.get('first_name')+' ' #BillAddressAddr1 (41 varchar)
                if rec.get('last_name'):
                    baddr1+= rec.get('last_name') #BillAddressAddr1 (41 varchar)

                if rec.get('street'):
                    baddr2 = rec.get('street') #BillAddressAddr2 (41 varchar)

                if rec.get('street2'):
                    baddr3 = rec.get('street2') #BillAddressAddr3 (41 varchar)

                if rec.get('terms_qbd_id'):
                    terms_ref = rec.get('terms_qbd_id') #TermsRefListId (36 varchar)

                if rec.get('vat'): #ResaleNumber vat
                    vat = rec.get('vat')

                if rec.get('ref'): #AccountNumber ref
                    ref = rec.get('ref')

                if rec.get('category_name'): #CustomerTypeRefFullName category_name
                    category_name = rec.get('category_name')

                is_update=0
                if rec.get('partner_qbd_id'):
                    is_update = 1
                    quickbooks_id = rec.get('partner_qbd_id') #ListId (varchar 36) Only for Update Query                    

                if name:
                    check_record ="Select Top 1 ListId from Customer where Name='{}'".format(name)

                cursor.execute(check_record)
                is_present = cursor.fetchone()

                if not is_update:
                    if not is_present:
                        if not rec.get('company'):
                            
                            if parent_ref:
                                if category_name:
                                    if terms_ref:
                                        insertQuery = "INSERT INTO Customer(ParentRefListID, Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, ResaleNumber, AccountNumber, CustomerTypeRefFullName, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(parent_ref, name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, category_name, company_name)
                                    else:
                                        insertQuery = "INSERT INTO Customer(ParentRefListID, Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, ResaleNumber, AccountNumber, CustomerTypeRefFullName, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(parent_ref, name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, category_name, company_name)
                                else:
                                    if terms_ref:
                                        insertQuery = "INSERT INTO Customer(ParentRefListID, Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, ResaleNumber, AccountNumber, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(parent_ref, name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, company_name)
                                    else:
                                        insertQuery = "INSERT INTO Customer(ParentRefListID, Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, ResaleNumber, AccountNumber, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(parent_ref, name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, company_name)
                            else:
                                if category_name:                           
                                    if terms_ref:
                                        insertQuery = "INSERT INTO Customer(Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, ResaleNumber, AccountNumber, CustomerTypeRefFullName, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, category_name, company_name)
                                    else:
                                        insertQuery = "INSERT INTO Customer(Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, ResaleNumber, AccountNumber, CustomerTypeRefFullName, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, category_name, company_name)
                                else:
                                    if terms_ref:
                                        insertQuery = "INSERT INTO Customer(Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, ResaleNumber, AccountNumber, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, company_name)
                                    else:
                                        insertQuery = "INSERT INTO Customer(Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, ResaleNumber, AccountNumber, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, company_name)

                        else:
                            if category_name:
                                if terms_ref:
                                    insertQuery = "INSERT INTO Customer(Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, ResaleNumber, AccountNumber, CustomerTypeRefFullName, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, category_name, company_name)
                                else:
                                    insertQuery = "INSERT INTO Customer(Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, ResaleNumber, AccountNumber, CustomerTypeRefFullName, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, category_name, company_name)
                            else:
                                    if terms_ref:
                                        insertQuery = "INSERT INTO Customer(Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, TermsRefListId, ResaleNumber, AccountNumber, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, company_name)
                                    else:
                                        insertQuery = "INSERT INTO Customer(Name, Salutation, FirstName, LastName, JobTitle, Phone, AltPhone, Email, Notes, BillAddressCity, BillAddressPostalCode, BillAddressState, BillAddressCountry, BillAddressAddr1, BillAddressAddr2, ResaleNumber, AccountNumber, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, company_name)

                    
                        # print (insertQuery)

                    try:
                        if not is_present:
                            logging.info("Insert Query ----------------------------- ")
                            logging.info(insertQuery)
                            cursor.execute(insertQuery)
                            cursor.commit()

                            # lastInserted ="Select Top 1 ListId from customer order by timecreated desc"
                            lastInserted ="Select Top 1 ListId from Customer where Name='{}'".format(name)
                            cursor.execute(lastInserted)
                            record_id = cursor.fetchone()
                            logging.info("Last Inserted ----------------------------- ")
                            logging.info(record_id[0])

                            tpa_customer_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_customer_dict['quickbooks_id'] = record_id[0]
                            tpa_customer_dict['message'] = 'Successfully Created'
                            tpa_customer_list.append(tpa_customer_dict)
                        
                        else:
                            logging.info("Record Already Present in Quickbboks so updating id in Odoo ----------------------------- ")
                            logging.info(check_record)
                            logging.info(is_present[0])

                            tpa_customer_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_customer_dict['quickbooks_id'] = is_present[0]
                            tpa_customer_dict['message'] = 'Quickbooks Id Successfully Added'
                            tpa_customer_list.append(tpa_customer_dict)

                    except Exception as e:
                        logging.info("1")
                        logging.warning(e)
                        # print(e)
                        pass

                else:
                    if not rec.get('company'):
                        if parent_ref:
                            if category_name:
                                if terms_ref:
                                    updateQuery = "Update Customer Set ParentRefListID='{}', Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', TermsRefListId='{}', ResaleNumber='{}', AccountNumber='{}', CustomerTypeRefFullName='{}' where ListID= '{}'". format(parent_ref, name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, category_name, quickbooks_id)
                                else:
                                    updateQuery = "Update Customer Set ParentRefListID='{}', Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', ResaleNumber='{}', AccountNumber='{}', CustomerTypeRefFullName='{}' where ListID= '{}'". format(parent_ref, name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, category_name, quickbooks_id)
                            else:
                                if terms_ref:
                                    updateQuery = "Update Customer Set ParentRefListID='{}', Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', TermsRefListId='{}', ResaleNumber='{}', AccountNumber='{}' where ListID= '{}'". format(parent_ref, name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, quickbooks_id)
                                else:
                                    updateQuery = "Update Customer Set ParentRefListID='{}', Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', ResaleNumber='{}', AccountNumber='{}' where ListID= '{}'". format(parent_ref, name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, quickbooks_id)
                        else:
                            if category_name:
                                if terms_ref:
                                    updateQuery = "Update Customer Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', TermsRefListId='{}', ResaleNumber='{}', AccountNumber='{}', CustomerTypeRefFullName='{}' where ListID= '{}'". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, category_name, quickbooks_id)
                                else:
                                    updateQuery = "Update Customer Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', ResaleNumber='{}', AccountNumber='{}', CustomerTypeRefFullName='{}' where ListID= '{}'". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, category_name, quickbooks_id)
                            else:
                                if terms_ref:
                                    updateQuery = "Update Customer Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', TermsRefListId='{}', ResaleNumber='{}', AccountNumber='{}' where ListID= '{}'". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, quickbooks_id)
                                else:
                                    updateQuery = "Update Customer Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', ResaleNumber='{}', AccountNumber='{}' where ListID= '{}'". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, quickbooks_id)

                    else:
                        if category_name:
                            if terms_ref:
                                updateQuery = "Update Customer Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', TermsRefListId='{}', ResaleNumber='{}', AccountNumber='{}', CustomerTypeRefFullName='{}' where ListID= '{}'". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, category_name, quickbooks_id)
                            else:
                                updateQuery = "Update Customer Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', ResaleNumber='{}', AccountNumber='{}', CustomerTypeRefFullName='{}' where ListID= '{}'". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, category_name, quickbooks_id)
                        else:
                            if terms_ref:
                                updateQuery = "Update Customer Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', TermsRefListId='{}', ResaleNumber='{}', AccountNumber='{}' where ListID= '{}'". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, terms_ref, vat, ref, quickbooks_id)
                            else:
                                updateQuery = "Update Customer Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', JobTitle='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', BillAddressCity='{}', BillAddressPostalCode='{}', BillAddressState='{}', BillAddressCountry='{}', BillAddressAddr1='{}', BillAddressAddr2='{}', ResaleNumber='{}', AccountNumber='{}' where ListID= '{}'". format(name, salutation, first_name, last_name, job_title, phone, altphone, email, notes, baddr_city, baddr_postal, baddr_state, baddr_country, baddr1, baddr2, vat, ref, quickbooks_id)

                    # print ("0000000000000000000000000000000000000")
                    # print (updateQuery)

                    try:
                        logging.info("Update Query ----------------------------- ")
                        logging.info(updateQuery)
                        cursor.execute(updateQuery)
                        cursor.commit()
			
                        tpa_customer_dict['odoo_id'] = rec.get('odoo_id')
                        tpa_customer_dict['quickbooks_id'] = quickbooks_id
                        tpa_customer_dict['message'] = 'Successfully Updated'
                        tpa_customer_list.append(tpa_customer_dict)

                    except Exception as e:
                        logging.info("2")
                        logging.warning(e)
                        if not is_update:
                            tpa_customer_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_customer_dict['quickbooks_id'] = ''
                            tpa_customer_dict['message'] = 'Error While Creating'
                            tpa_customer_list.append(tpa_customer_dict)
                        else:
                            tpa_customer_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_customer_dict['quickbooks_id'] = rec.get('partner_qbd_id')
                            tpa_customer_dict['message'] = 'Error While Updating'
                            tpa_customer_list.append(tpa_customer_dict)
                        # print(e)
                        pass

           
            cursor.close()
            return (str({"Data":tpa_customer_list}))
        
        return (str({"Data":[]}))

    except Exception as e:
        logging.info("3")
        logging.warning(e)
        # print (e)
        # data = 0
        return ({"Status": 404, "Message":"Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])
