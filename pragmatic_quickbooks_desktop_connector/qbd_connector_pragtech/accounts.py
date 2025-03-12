from flask import Blueprint, request
from connection import connect_to_qbd, close_connection_to_qbd
import logging
import json
logging.basicConfig(level=logging.DEBUG)

accounts = Blueprint('accounts', __name__, template_folder='templates')


def getodooAccountType(AccountType):
    qbAccountType = []

    if AccountType == "Bank":
        qbAccountType = "asset_cash"

    elif AccountType == "AccountsReceivable":
        qbAccountType = "asset_receivable"

    elif AccountType == "AccountsPayable":
        qbAccountType = "liability_payable"

    elif AccountType == "FixedAsset":
        qbAccountType = "asset_fixed"

    elif AccountType == "OtherAsset":
        qbAccountType = "asset_current"

    elif AccountType == "OtherCurrentAsset":
        qbAccountType = "asset_non_current"

    elif AccountType == "CreditCard":
        qbAccountType = "liability_credit_card"

    elif AccountType == "OtherCurrentLiability":
        qbAccountType = "liability_current"

    elif AccountType == "LongTermLiability" or AccountType == "NonPosting":
        qbAccountType = "liability_non_current"

    elif AccountType == "Equity":
        qbAccountType = "equity"

    elif AccountType == "Income":
        qbAccountType = "income"

    elif AccountType == "Expense":
        qbAccountType = "expense"

    elif AccountType == "CostOfGoodsSold":
        qbAccountType = "expense_direct_cost"

    elif AccountType == "OtherIncome":
        qbAccountType = "income_other"

    elif AccountType == "OtherExpense":
        qbAccountType = "expense_depreciation"

    return qbAccountType


'''
TPA - Third Party Application
'''


@accounts.route('/QBD/import_account', methods=['GET'])
def import_QBD_Accounts_to_TPA():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()

        cursor.execute("SELECT COUNT(ListId) FROM account")
        record_count = cursor.fetchone()

        to_execute_account = int(request.args.get('to_execute_account'))
        limit = int(request.args.get('limit'))

        # print (type(to_execute_account))

        if to_execute_account == 1:
            parent_accounts = "SELECT TOP {} ListID, ParentRefListID, Name, AccountType, AccountNumber, TimeModified FROM account Order by TimeModified ASC".format(limit)
        elif to_execute_account == 2:
            time_modified = "{ts'" + str(request.args.get('last_qbd_id')) + "'}"
            # print (time_modified)
            parent_accounts = "SELECT TOP {} ListID, ParentRefListID, Name, AccountType, AccountNumber, TimeModified FROM account where timemodified >={}".format(limit, time_modified)

        cursor.execute(parent_accounts)

        odoo_account_list = []
        records = cursor.fetchall()
        for row in records:
            odoo_account_dict = {}
            row_as_list = [x for x in row]
            if row_as_list[4]:
                odoo_account_dict['quickbooks_id'] = row_as_list[0]

                odoo_account_dict['name'] = row_as_list[2]

                odooAccountType = getodooAccountType(row_as_list[3])
                
                odoo_account_dict['account_type'] = odooAccountType  # use account_type to find account user_type_id
                if odooAccountType == 'asset_receivable' or odooAccountType == 'liability_payable':
                    odoo_account_dict['reconcile'] = True;  # reconcile should be true when account type is receivable or payable

                odoo_account_dict['code'] = row_as_list[4]
                odoo_account_dict['last_time_modified'] = str(row_as_list[5])
                odoo_account_list.append(odoo_account_dict)

                print (records)

        cursor.close()
        if not odoo_account_list:
            print ("Return Empty")
            return (str(0))

        if to_execute_account == 1 or to_execute_account == 2:
            print(odoo_account_list)
            return (json.dumps(odoo_account_list))

    except Exception as e:
        # print (e)
        logging.info("1")
        logging.warning(e)
        data = 0
        return ({"Status": 404,
                 "Message": "Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])


'''
TPA - Third Party Application
'''


@accounts.route('/QBD/export_accounts', methods=['POST'])
def export_TPA_Accounts_to_QBD():
    try:
        data = connect_to_qbd()
        con = data[0]
        cursor = con.cursor()
        # print (cursor)
        is_update = 0
        req = request.get_json(force=True)
        if 'account_list' in req:
            tpa_accounts_list = []

            for rec in req.get('account_list'):
                tpa_accounts_dict = {}
                # print (rec)

                is_update = 0
                if rec.get('account_qbd_id'):
                    quickbooks_id = rec.get('account_qbd_id')
                    is_update = 1

                if rec.get('code'):
                    check_record = "Select Top 1 ListId from account where AccountNumber='{}' and Name='{}'".format(rec.get('code'), rec.get('name'))

                cursor.execute(check_record)
                is_present = cursor.fetchone()

                if not is_update:
                    if not is_present:
                        insertQuery = "INSERT INTO Account(AccountNumber , Name, AccountType) VALUES ('" + rec.get('code') + "','" + rec.get('name') + "','" + rec.get('user_type_id') + "')"
                        # print (insertQuery)
                        try:
                            logging.info("Insert Query ----------------------------- ")
                            logging.info(insertQuery)

                            cursor.execute(insertQuery)
                            # lastInserted ="Select Top 1 ListId from account order by timecreated desc"
                            lastInserted = "Select Top 1 ListId from account where AccountNumber='{}' and Name='{}'".format(rec.get('code'), rec.get('name'))

                            cursor.execute(lastInserted)
                            # cursor.commit()
                            # print (lastInserted)
                            record = cursor.fetchone()
                            logging.info("Last Inserted ----------------------------- ")
                            logging.info(record[0])
                            # print (record)
                            tpa_accounts_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_accounts_dict['quickbooks_id'] = record[0]
                            tpa_accounts_dict['messgae'] = 'Successfully Created'
                            tpa_accounts_list.append(tpa_accounts_dict)

                        except Exception as e:
                            logging.info("1")
                            logging.warning(e)
                            # print(e)
                            pass
                    else:
                        logging.info("Record Already Present in Quickbboks so updating id in Odoo ----------------------------- ")
                        logging.info(check_record)
                        logging.info(is_present[0])

                        tpa_accounts_dict['odoo_id'] = rec.get('odoo_id')
                        tpa_accounts_dict['quickbooks_id'] = is_present[0]
                        tpa_accounts_dict['messgae'] = 'Quickbooks Id Successfully Added'
                        tpa_accounts_list.append(tpa_accounts_dict)

                else:
                    updateQuery = "Update Account Set AccountNumber='{}' , Name='{}', AccountType='{}' where ListId='{}'".format(rec.get('code'), rec.get('name'), rec.get('user_type_id'), quickbooks_id)
                    # print (updateQuery)
                    try:
                        cursor.execute(updateQuery)
                        cursor.commit()

                        tpa_accounts_dict['odoo_id'] = rec.get('odoo_id')
                        tpa_accounts_dict['quickbooks_id'] = rec.get('account_qbd_id')
                        tpa_accounts_dict['messgae'] = 'Successfully Updated'
                        tpa_accounts_list.append(tpa_accounts_dict)

                    except Exception as e:
                        logging.info("2")
                        logging.warning(e)
                        if not is_update:
                            tpa_accounts_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_accounts_dict['quickbooks_id'] = ''
                            tpa_accounts_dict['messgae'] = 'Error While Creating:' + e
                            tpa_accounts_list.append(tpa_accounts_dict)
                        else:
                            tpa_accounts_dict['odoo_id'] = rec.get('odoo_id')
                            tpa_accounts_dict['quickbooks_id'] = rec.get('account_qbd_id')
                            tpa_accounts_dict['messgae'] = 'Error While Updating:' + e
                            tpa_accounts_list.append(tpa_accounts_dict)

                        # print(e)
                        pass

            # print(tpa_accounts_list)
            # return (str([{"Data":"Success"}]))
            cursor.close()
            return {"Data": tpa_accounts_list}

        return {"Data": [],"Message":'No Accounts Exported'}

    except Exception as e:
        logging.info("3")
        logging.warning(e)

        # print (e)
        # data = 0
        return ({"Status": 404, "Message": "Please wait for sometime and check whether Quickbooks Desktop and Command Prompt are running as adminstrator."})

    finally:
        if data != 0:
            close_connection_to_qbd(data[0])
