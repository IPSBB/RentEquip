from flask import Blueprint, request
from connection import connect_to_qbd, close_connection_to_qbd
import logging
import json
logging.basicConfig(level=logging.DEBUG)

vendor = Blueprint('vendor', __name__, template_folder='templates')

'''
TPA - Third Party Application
'''


@vendor.route('/QBD/import_vendor')
def import_QBD_Vendor_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        to_execute_account = int(request.args.get('to_execute_account'))
        if request.args.get('limit'):
            limit = int(request.args.get('limit'))
        if request.args.get('list_id'):
            list_id = request.args.get('list_id')

        # 0 ListId (36 varchar) quickbooks_id
        # 1 Name (41 varchar) name
        # 2 Salutation (15 varchar) title
        # 3 Phone (21 varchar) phone
        # 4 AltPhone (21 varchar) mobile
        # 5 Email (1023 varchar) email
        # 6 Notes (4095 varchar) comment
        # 7 VendorAddressCity (31 varchar) city
        # 8 VendorAddressPostalCode (13 varchar) zip
        # 9 VendorAddressState (21 varchar) state_id
        # 10 VendorAddressCountry (31 varchar) country_id
        # 11 VendorAddressAddr1 (41 varchar) street
        # 12 VendorAddressAddr2 (41 varchar)street2
        # 13 TermsRefListId (36 varchar) terms_qbd_id
        # 14 TimeModified  last_time_modified
        # 15 VendorTaxIdent vat
        # 16 AccountNumber ref
        # 17 VendorTypeRefFullName category_name
        # 18 IsActive is_active

        if to_execute_account == 1:
            vendor = "Select TOP {} ListId, Name, Salutation, Phone, AltPhone, Email, Notes, VendorAddressCity, VendorAddressPostalCode, VendorAddressState, VendorAddressCountry, VendorAddressAddr1, VendorAddressAddr2, TermsRefListId, TimeModified, VendorTaxIdent, AccountNumber, VendorTypeRefFullName, IsActive from Vendor Order by TimeModified ASC".format(
                limit)
            # cursor.execute(vendor)
        elif to_execute_account == 2:
            time_modified = "{ts'"+str(request.args.get('last_qbd_id'))+"'}"
            # print (time_modified)
            vendor = "Select TOP {} ListId, Name, Salutation, Phone, AltPhone, Email, Notes, VendorAddressCity, VendorAddressPostalCode, VendorAddressState, VendorAddressCountry, VendorAddressAddr1, VendorAddressAddr2, TermsRefListId, TimeModified, VendorTaxIdent, AccountNumber, VendorTypeRefFullName, IsActive from Vendor where timemodified >={}".format(
                limit, time_modified)
            # print (vendor)
            # cursor.execute(vendor)
        elif to_execute_account == 4:
            if request.args.get('fetch_record') and list_id:
                ListID = list_id
                vendor = "Select ListId, Name, Salutation, Phone, AltPhone, Email, Notes, VendorAddressCity, VendorAddressPostalCode, VendorAddressState, VendorAddressCountry, VendorAddressAddr1, VendorAddressAddr2, TermsRefListId, TimeModified, VendorTaxIdent, AccountNumber, VendorTypeRefFullName, IsActive from Vendor where ListID ='"+ListID+"'"

        cursor.execute(vendor)
        odoo_vendor_list = []

        for row in cursor.fetchall():
            odoo_vendor_dict = {}
            row_as_list = [x for x in row]

            # 0 ListId (36 varchar) quickbooks_id
            odoo_vendor_dict['quickbooks_id'] = row_as_list[0]
            # 1 Name (41 varchar) name
            odoo_vendor_dict['name'] = row_as_list[1]
            # 2 Salutation (15 varchar) title
            odoo_vendor_dict['title'] = row_as_list[2]
            # 3 Phone (21 varchar) phone
            odoo_vendor_dict['phone'] = row_as_list[3]
            # 4 AltPhone (21 varchar) mobile
            odoo_vendor_dict['mobile'] = row_as_list[4]
            # 5 Email (1023 varchar) email
            odoo_vendor_dict['email'] = row_as_list[5]
            # 6 Notes (4095 varchar) comment
            odoo_vendor_dict['comment'] = row_as_list[6]
            # 7 VendorAddressCity (31 varchar) city
            odoo_vendor_dict['city'] = row_as_list[7]
            # 8 VendorAddressPostalCode (13 varchar) zip
            odoo_vendor_dict['zip'] = row_as_list[8]
            # 9 VendorAddressState (21 varchar) state_id
            odoo_vendor_dict['state'] = row_as_list[9]
            # 10 VendorAddressCountry (31 varchar) country_id
            odoo_vendor_dict['country'] = row_as_list[10]
            # 11 VendorAddressAddr1 (41 varchar) street
            odoo_vendor_dict['street'] = row_as_list[11]
            # 12 VendorAddressAddr2 (41 varchar)street2
            odoo_vendor_dict['street2'] = row_as_list[12]
            # 13 TermsRefListId (36 varchar) terms_qbd_id
            odoo_vendor_dict['terms_qbd_id'] = row_as_list[13]
            odoo_vendor_dict['last_time_modified'] = str(
                row_as_list[14])  # 14 TimeModified  last_time_modified
            odoo_vendor_dict['is_vendor'] = True
            odoo_vendor_dict['vat'] = row_as_list[15]  # 15 VendorTaxIdent vat
            odoo_vendor_dict['ref'] = row_as_list[16]  # 16 AccountNumber ref
            # 17 VendorTypeRefFullName category_name
            odoo_vendor_dict['category_name'] = row_as_list[17]
            # 18 IsActive  is_active
            odoo_vendor_dict['is_active'] = row_as_list[18]

            odoo_vendor_list.append(odoo_vendor_dict)

        # print (odoo_cust_list)

        cursor.close()
        return (json.dumps(odoo_vendor_list))

    except Exception as e:
        # print (e)
        data = 0
        return ({"Status": 404, "Message": "Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])


'''
TPA - Third Party Application
'''


@vendor.route('/QBD/export_vendors', methods=['POST'])
def export_TPA_Vendors_to_QBD():

    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()
        # print (cursor)

        req = request.get_json(force=True)
        # print (req)
        if 'vendors_list' in req:

            tpa_vendor_list = []
            for rec in req.get('vendors_list'):
                tpa_vendor_dict = {}
                # print (rec)

                salutation = last_name = phone = altphone = email = notes = vaddr_city = vaddr_postal = vaddr_state = vaddr_country = vaddr1 = vaddr2 = terms_ref = vat = ref = category_name = ''

                name = rec.get('name')  # Name (41 varchar)
                company_name = rec.get('name')
                if rec.get('title'):
                    salutation = rec.get('title')  # Salutation (15 varchar)

                first_name = rec.get('first_name')  # FirstName (25 varchar)

                if rec.get('last_name'):
                    last_name = rec.get('last_name')  # LastName (25 varchar)

                if rec.get('phone'):
                    phone = rec.get('phone')  # Phone (21 varchar)

                if rec.get('mobile'):
                    altphone = rec.get('mobile')  # AltPhone (21 varchar)

                if rec.get('email'):
                    email = rec.get('email')  # Email (1023 varchar)

                if rec.get('comment'):
                    notes = rec.get('comment')  # Notes (4095 varchar)

                if rec.get('city'):
                    # VendorAddressCity (31 varchar)
                    vaddr_city = rec.get('city')

                if rec.get('zip'):
                    # VendorAddressPostalCode (13 varchar)
                    vaddr_postal = rec.get('zip')

                if rec.get('state_id'):
                    # VendorAddressState (21 varchar)
                    vaddr_state = rec.get('state_id')

                if rec.get('country_id'):
                    # VendorAddressCountry (31 varchar)
                    vaddr_country = rec.get('country_id')

                if rec.get('street'):
                    # VendorAddressAddr1 (41 varchar)
                    vaddr1 = rec.get('street')

                if rec.get('street2'):
                    # VendorAddressAddr2 (41 varchar)
                    vaddr2 = rec.get('street2')

                if rec.get('terms_qbd_id'):
                    # TermsRefListId (36 varchar)
                    terms_ref = rec.get('terms_qbd_id')

                if rec.get('vat'):
                    vat = rec.get('vat')  # TermsRefListId (36 varchar)

                if rec.get('ref'):
                    ref = rec.get('ref')  # TermsRefListId (36 varchar)

                if rec.get('category_name'):
                    # TermsRefListId (36 varchar)
                    category_name = rec.get('category_name')

                is_update = 0
                if rec.get('vendor_qbd_id'):
                    quickbooks_id = rec.get('vendor_qbd_id')
                    is_update = 1

                if name:
                    check_record = "Select Top 1 ListId from Vendor where Name='{}'".format(
                        name)

                cursor.execute(check_record)
                is_present = cursor.fetchone()

                if not is_update:
                    if not is_present:
                        if category_name:
                            if terms_ref:
                                insertQuery = "INSERT INTO Vendor(Name, Salutation, FirstName, LastName, Phone, AltPhone, Email, Notes, VendorAddressCity, VendorAddressPostalCode, VendorAddressState, VendorAddressCountry, VendorAddressAddr1, VendorAddressAddr2, TermsRefListId, VendorTaxIdent, AccountNumber, VendorTypeRefFullName, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(
                                    name, salutation, first_name, last_name, phone, altphone, email, notes, vaddr_city, vaddr_postal, vaddr_state, vaddr_country, vaddr1, vaddr2, terms_ref, vat, ref, category_name, company_name)
                            else:
                                insertQuery = "INSERT INTO Vendor(Name, Salutation, FirstName, LastName, Phone, AltPhone, Email, Notes, VendorAddressCity, VendorAddressPostalCode, VendorAddressState, VendorAddressCountry, VendorAddressAddr1, VendorAddressAddr2, VendorTaxIdent, AccountNumber, VendorTypeRefFullName, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(
                                    name, salutation, first_name, last_name, phone, altphone, email, notes, vaddr_city, vaddr_postal, vaddr_state, vaddr_country, vaddr1, vaddr2, vat, ref, category_name, company_name)
                        else:
                            if terms_ref:
                                insertQuery = "INSERT INTO Vendor(Name, Salutation, FirstName, LastName, Phone, AltPhone, Email, Notes, VendorAddressCity, VendorAddressPostalCode, VendorAddressState, VendorAddressCountry, VendorAddressAddr1, VendorAddressAddr2, TermsRefListId, VendorTaxIdent, AccountNumber, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(
                                    name, salutation, first_name, last_name, phone, altphone, email, notes, vaddr_city, vaddr_postal, vaddr_state, vaddr_country, vaddr1, vaddr2, terms_ref, vat, ref, company_name)
                            else:
                                insertQuery = "INSERT INTO Vendor(Name, Salutation, FirstName, LastName, Phone, AltPhone, Email, Notes, VendorAddressCity, VendorAddressPostalCode, VendorAddressState, VendorAddressCountry, VendorAddressAddr1, VendorAddressAddr2, VendorTaxIdent, AccountNumber, CompanyName) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')". format(
                                    name, salutation, first_name, last_name, phone, altphone, email, notes, vaddr_city, vaddr_postal, vaddr_state, vaddr_country, vaddr1, vaddr2, vat, ref, company_name)

                        # print (insertQuery)

                    try:
                        if not is_present:
                            logging.info(
                                "Insert Query ----------------------------- ")
                            logging.info(insertQuery)
                            cursor.execute(insertQuery)

                            lastInserted = "Select Top 1 ListId from Vendor where Name='{}'".format(
                                name)
                            cursor.commit()
                            cursor.execute(lastInserted)
                            record_id = cursor.fetchone()
                            logging.info(
                                "Last Inserted ----------------------------- ")
                            logging.info(record_id[0])

                            tpa_vendor_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_vendor_dict['quickbooks_id'] = record_id[0]
                            tpa_vendor_dict['message'] = "Successfully Created"
                            tpa_vendor_list.append(tpa_vendor_dict)

                        else:
                            logging.info(
                                "Record Already Present in Quickbboks so updating id in Odoo ----------------------------- ")
                            logging.info(check_record)
                            logging.info(is_present[0])

                            tpa_vendor_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_vendor_dict['quickbooks_id'] = is_present[0]
                            tpa_vendor_dict['message'] = "Quickbooks Id Successfully Added"
                            tpa_vendor_list.append(tpa_vendor_dict)

                    except Exception as e:
                        logging.info("1")
                        logging.warning(e)
                        # print(e)
                        pass

                else:
                    if category_name:
                        if terms_ref:
                            updateQuery = "Update Vendor Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', VendorAddressCity='{}', VendorAddressPostalCode='{}', VendorAddressState='{}', VendorAddressCountry='{}', VendorAddressAddr1='{}', VendorAddressAddr2='{}', TermsRefListId='{}', VendorTaxIdent='{}', AccountNumber='{}', VendorTypeRefFullName='{}' where ListID= '{}'". format(
                                name, salutation, first_name, last_name, phone, altphone, email, notes, vaddr_city, vaddr_postal, vaddr_state, vaddr_country, vaddr1, vaddr2, terms_ref, vat, ref, category_name, quickbooks_id)
                        else:
                            updateQuery = "Update Vendor Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', VendorAddressCity='{}', VendorAddressPostalCode='{}', VendorAddressState='{}', VendorAddressCountry='{}', VendorAddressAddr1='{}', VendorAddressAddr2='{}', VendorTaxIdent='{}', AccountNumber='{}', VendorTypeRefFullName='{}' where ListID= '{}'". format(
                                name, salutation, first_name, last_name, phone, altphone, email, notes, vaddr_city, vaddr_postal, vaddr_state, vaddr_country, vaddr1, vaddr2, vat, ref, category_name, quickbooks_id)
                    else:
                        if terms_ref:
                            updateQuery = "Update Vendor Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', VendorAddressCity='{}', VendorAddressPostalCode='{}', VendorAddressState='{}', VendorAddressCountry='{}', VendorAddressAddr1='{}', VendorAddressAddr2='{}', TermsRefListId='{}', VendorTaxIdent='{}', AccountNumber='{}' where ListID= '{}'". format(
                                name, salutation, first_name, last_name, phone, altphone, email, notes, vaddr_city, vaddr_postal, vaddr_state, vaddr_country, vaddr1, vaddr2, terms_ref, vat, ref, quickbooks_id)
                        else:
                            updateQuery = "Update Vendor Set Name='{}', Salutation='{}', FirstName='{}', LastName='{}', Phone='{}', AltPhone='{}', Email='{}', Notes='{}', VendorAddressCity='{}', VendorAddressPostalCode='{}', VendorAddressState='{}', VendorAddressCountry='{}', VendorAddressAddr1='{}', VendorAddressAddr2='{}', VendorTaxIdent='{}', AccountNumber='{}' where ListID= '{}'". format(
                                name, salutation, first_name, last_name, phone, altphone, email, notes, vaddr_city, vaddr_postal, vaddr_state, vaddr_country, vaddr1, vaddr2, vat, ref, quickbooks_id)

                    # print (updateQuery)
                    try:
                        cursor.execute(updateQuery)
                        # lastInserted ="Select Top 1 ListId from vendor order by timecreated desc"
                        cursor.commit()
                        # cursor.execute(lastInserted)

                        tpa_vendor_dict['odoo_id'] = rec.get('odoo_id')
                        tpa_vendor_dict['quickbooks_id'] = rec.get(
                            'vendor_qbd_id')
                        tpa_vendor_dict['message'] = "Successfully Updated"
                        tpa_vendor_list.append(tpa_vendor_dict)

                    except Exception as e:
                        logging.info("2")
                        logging.warning(e)

                        if not is_update:
                            tpa_vendor_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_vendor_dict['quickbooks_id'] = ''
                            tpa_vendor_dict['message'] = "Error While Creating"
                            tpa_vendor_list.append(tpa_vendor_dict)
                        else:
                            tpa_vendor_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_vendor_dict['quickbooks_id'] = rec.get(
                                'vendor_qbd_id')
                            tpa_vendor_dict['message'] = "Error While Updating"
                            tpa_vendor_list.append(tpa_vendor_dict)
                        # logging.info("\nException ------- ",e)
                        pass

            # print(tpa_vendor_list)
            # return (str([{"Data":"Success"}]))
            cursor.close()
            return {"Data": tpa_vendor_list}

        return {"Data": [],"Message":'No Vendor Exported'}

    except Exception as e:
        logging.info("3")
        logging.warning(e)

        # logging.error("\nException ------- ",e)
        # data = 0
        return ({"Status": 404, "Message": "Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])
