from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import requests
import json
import ast
import logging
_logger = logging.getLogger(__name__)
from dateutil.parser import *

class AccountJournal(models.Model):
    _inherit = "account.journal"

    qbd_payment_method_id = fields.Many2one(
        'qbd.payment.method', string="QBD Payment Method")


class AccountAccount(models.Model):
    _inherit = "account.account"

    code = fields.Char(size=64, required=False, index=True)
    quickbooks_id = fields.Char("Quickbook id ", copy=False)
    is_updated = fields.Boolean('Is Updated')

    def write(self, vals):

        if 'is_updated' not in vals and 'quickbooks_id' not in vals:
            vals['is_updated'] = True

        return super(AccountAccount, self).write(vals)

    def export_account_to_qbd(self):
        for account in self:
            if account.quickbooks_id:
                return account.quickbooks_id
            else:
                account.export_accounts()

    def create_accounts(self, accounts_data):
        # accounts_data = ast.literal_eval(accounts_data)
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        _logger.info("LENGTH OF ACCOUNT===>>>>>>>>>>>>>>>>>{}".format(accounts_data))

        # IF all Account Imported
        if len(accounts_data) == 0:
            raise UserError(
                "It seems that all of the Chart of Accounts are already imported.")
        # print('Length of account_data', accounts_data)
        cnt = 0
        for account in accounts_data:
            account_obj = self.env['account.account']
            account_id = None
            _logger.info("ACCOUNT====>>>>>>>>>>>>>>>>>>\n\n\n\n\n\n{}".format(account))
            if 'quickbooks_id' in account and account.get('quickbooks_id'):
                account_id = account_obj.search(
                    [('quickbooks_id', '=', account.get('quickbooks_id'))])

                if not account_id and account.get('code'):
                    account_id = account_obj.search(
                        [('code', '=', account.get('code'))], limit=1)
                    if account_id:
                        account_id.write(
                            {'quickbooks_id': account.get('quickbooks_id')})
                        continue

                if not account_id:
                    # print('In iffff !!',account.get('name'))
                    # create new account
                    vals = {}
                    if 'quickbooks_id' in account and account.get('quickbooks_id'):
                        vals.update(
                            {'quickbooks_id': account.get('quickbooks_id')})

                    if 'name' in account and account.get('name'):
                        name = self.search(
                            [('name', '=', account.get('name'))])
                        if name:
                            continue
                        else:
                            vals.update({'name': account.get('name')})

                    if 'code' in account and account.get('code'):
                        vals.update({'code': account.get('code')})

                    if 'account_type' in account and account.get('account_type'):
                        account_type = account.get('account_type')
                        if account_type:
                            # account_type_id = self.env['account.account.type'].search([('name', '=', account_type)],
                            #                                                           limit=1)
                            # if account_type_id:
                            if account_type == "asset_receivable" or account_type == "liability_payable":
                                vals.update({'reconcile': True})

                            if account_type == "Bank":
                                vals.update(
                                    {'account_type': 'asset_cash'})

                            elif account_type == "AccountsReceivable":
                                vals.update(
                                    {'account_type': 'asset_receivable'})

                            elif account_type == "OtherAsset":
                                vals.update(
                                    {'account_type': 'asset_current'})

                            elif account_type == "FixedAsset":
                                vals.update(
                                    {'account_type': 'asset_fixed'})


                            elif account_type == "OtherCurrentAsset":
                                vals.update(
                                    {'account_type': 'asset_non_current'})

                            elif account_type == "AccountsPayable":
                                vals.update(
                                    {'account_type': 'liability_payable'})

                            elif account_type == "CreditCard":
                                vals.update(
                                    {'account_type': 'liability_credit_card'})

                            elif account_type == "OtherCurrentLiability":
                                vals.update(
                                    {'account_type': 'liability_current'})

                            elif account_type == "LongTermLiability" or account_type == 'NonPosting':
                                vals.update(
                                    {'account_type': 'liability_non_current'})

                            elif account_type == "Equity":
                                vals.update(
                                    {'account_type': 'equity'})

                            elif account_type == "Income":
                                vals.update(
                                    {'account_type': 'income'})

                            elif account_type == "CostOfGoodsSold":
                                vals.update(
                                    {'account_type': 'expense_direct_cost'})

                            elif account_type == "Expense":
                                vals.update(
                                    {'account_type': 'expense'})


                            elif account_type == "OtherIncome":
                                vals.update(
                                    {'account_type': 'income_other'})

                            elif account_type == "OtherExpense":
                                vals.update(
                                    {'account_type': 'expense_depreciation'})

                            else:
                                vals.update(
                                    {'account_type': account_type})

                        else:
                            if not account_type:
                                raise UserError(
                                    'User Type ' + account_type + ' not correctly set.')

                    if vals:
                        print('Vals===================== : ', vals)
                        new_account_id = account_obj.create(vals)
                        if new_account_id:
                            # print('New account id : ', new_account_id)

                            self.env.cr.commit()
                            # print("!! Account Commited !!",new_account_id.name)
                            date_parsed = parse(
                                account.get("last_time_modified"))
                            company.write({
                                'last_imported_qbd_id_for_account': date_parsed
                            })

                else:
                    print('In elsee !!!',account.get('code'))
                    # update record
                    vals = {}
                    if 'quickbooks_id' in account and account.get('quickbooks_id'):
                        vals.update(
                            {'quickbooks_id': account.get('quickbooks_id')})

                    if 'name' in account and account.get('name'):
                        vals.update({'name': account.get('name')})

                    if 'code' in account and account.get('code'):
                        vals.update({'code': account.get('code')})

                    if 'account_type' in account and account.get('account_type'):
                        account_type = account.get('account_type')

                        if account_type:
                            if account_type == "asset_receivable" or account_type == "liability_payable":
                                vals.update({'reconcile': True})

                            if account_type == "Bank":
                                vals.update(
                                    {'account_type': 'asset_cash'})

                            elif account_type == "AccountsReceivable":
                                vals.update(
                                    {'account_type': 'asset_receivable'})

                            elif account_type == "OtherAsset":
                                vals.update(
                                    {'account_type': 'asset_current'})

                            elif account_type == "FixedAsset":
                                vals.update(
                                    {'account_type': 'asset_fixed'})


                            elif account_type == "OtherCurrentAsset":
                                vals.update(
                                    {'account_type': 'asset_non_current'})


                            elif account_type == "AccountsPayable":
                                vals.update(
                                    {'account_type': 'liability_payable'})

                            elif account_type == "CreditCard":
                                vals.update(
                                    {'account_type': 'liability_credit_card'})

                            elif account_type == "OtherCurrentLiability":
                                vals.update(
                                    {'account_type': 'liability_current'})

                            elif account_type == "LongTermLiability" or account_type == 'NonPosting':
                                vals.update(
                                    {'account_type': 'liability_non_current'})

                            elif account_type == "Equity":
                                vals.update(
                                    {'account_type': 'equity'})

                            elif account_type == "Income":
                                vals.update(
                                    {'account_type': 'income'})

                            elif account_type == "CostOfGoodsSold":
                                vals.update(
                                    {'account_type': 'expense_direct_cost'})

                            elif account_type == "Expense":
                                vals.update(
                                    {'account_type': 'expense'})

                            elif account_type == "OtherIncome":
                                vals.update(
                                    {'account_type': 'income_other'})

                            elif account_type == "OtherExpense":
                                vals.update(
                                    {'account_type': 'expense_depreciation'})

                            # elif account_type =="NonPosting":
                            #     vals.update(
                            #         {'account_type': 'liability_credit_card'})

                            else:
                                vals.update(
                                    {'account_type': account_type})
                        else:
                            raise UserError(
                                'User Type ' + account_type + ' not correctly set.')

                    if vals:
                        account_id.write(vals)
                        date_parsed = parse(account.get("last_time_modified"))
                        company.write({
                            'last_imported_qbd_id_for_account': date_parsed
                        })

        return True

    # def get_account_type(self, qb_account_type):
    #     account_type = None
    #     if qb_account_type == 'Bank':
    #         account_type = 'Bank and Cash'
    #     elif qb_account_type == 'AccountsReceivable':
    #         account_type = 'Receivable'
    #     elif qb_account_type == 'AccountsPayable':
    #         account_type = 'Payable'
    #     elif qb_account_type == 'FixedAsset':
    #         account_type = 'Fixed Assets'
    #     elif qb_account_type == 'OtherAsset':
    #         account_type = 'Current Assets'
    #     elif qb_account_type == 'OtherCurrentAsset':
    #         account_type = 'Current Assets'
    #     elif qb_account_type == 'CreditCard':
    #         account_type = 'Credit Card'
    #     elif qb_account_type == 'OtherCurrentLiability':
    #         account_type = 'Current Liabilities'
    #     elif qb_account_type == 'LongTermLiability' or qb_account_type == 'NonPosting':
    #         account_type = 'Non-current Liabilities'
    #     elif qb_account_type == 'Equity':
    #         account_type = 'Equity'
    #     elif qb_account_type == 'Income':
    #         account_type = 'Income'
    #     elif qb_account_type == 'Expense':
    #         account_type = 'Expenses'
    #     elif qb_account_type == 'CostOfGoodsSold':
    #         account_type = 'Cost of Revenue'
    #     elif qb_account_type == 'OtherIncome':
    #         account_type = 'Other Income'
    #     elif qb_account_type == 'OtherExpense' or qb_account_type == 'Suspense':
    #         account_type = 'Expenses'

    #     if account_type:
    #         return account_type

    def export_accounts(self):
        account_data_list = []
        loger_dict = {}
        loger_list = []
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id

        if company.export_acc_limit:
            limit = int(company.export_acc_limit)
        else:
            limit = 0
        # if self is record then only export that record else export all records which are not exported.
        if self:
            accounts = self
        else:
            if company.export_updated_record:
                accounts = self.search(
                    [('quickbooks_id', '!=', None), ('is_updated', '=', True)], limit=limit)
            else:
                accounts = self.search([('quickbooks_id', '=', None)], limit=limit)

        # print('\n\nAccountss :', accounts, '\n\n')

        if accounts:
            for account in accounts:
                account_dict = {}
                if company.export_updated_record:
                    account_dict = self.get_account_dict(
                        account, company.export_updated_record)
                else:
                    account_dict = self.get_account_dict(account)

                if account_dict:
                    account_data_list.append(account_dict)

        if account_data_list:
            # print('\n\nAccount data list : \n\n',account_data_list,'\n\n\n')
            # print('\n\n Total Count :: ',len(account_data_list))

            company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
            headers = {'content-type': "application/json"}
            data = account_data_list

            data = {'account_list': data}

            response = requests.request('POST', company.url + '/export_accounts', data=json.dumps(data), headers=headers,
                                        verify=False)

            # print("Response Text", type(response.text),response.text)

            try:
                resp = ast.literal_eval(response.text)
                if isinstance(resp, dict):
                    if company.export_updated_record == False:
                        if resp.get("Message"):
                            raise UserError(_("No Accounts Exported"))
                        for res in resp.get('Data'):
                            if 'odoo_id' in res and res.get('odoo_id'):
                                account_id = self.browse(int(res.get('odoo_id')))

                                if account_id:
                                    account_id.write(
                                        {'quickbooks_id': res.get('quickbooks_id')})
                            loger_dict.update({'operation': 'Export Account',
                                            'odoo_id': res.get('odoo_id'),
                                            'qbd_id': res.get('quickbooks_id'),
                                            'message': res.get('messgae')
                                            })
                            qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
                            # company.write({'qbd_loger_id':[(4, qbd_loger_id.id)]})

                    else:
                        for res in resp.get('Data'):
                            if 'odoo_id' in res and res.get('odoo_id'):
                                account_id = self.browse(int(res.get('odoo_id')))

                                if account_id:
                                    account_id.write({'is_updated': False})
                            loger_dict.update({'operation': 'Export Account',
                                            'odoo_id': res.get('odoo_id'),
                                            'qbd_id': res.get('quickbooks_id'),
                                            'message': res.get('messgae')
                                            })
                            qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
                            # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})
                else:
                    raise UserError(_("No Data in Response Check Quickbook Desktop Terminal"))
            except Exception as ex: 
                _logger.error(str(ex))
                raise UserError(str(ex))
        return True

    def get_account_dict(self, account, is_send_updated=False):
        account_dict = {}

        # print ("---------------------", account.user_type_id.name)
        # print ("---------------------",self.getAccountType(account.user_type_id.name))

        bad_chars = [';', ':', '!', "*", "$", "'"]
        name = account.name
        for i in bad_chars:
            name = name.replace(i, "")

        if len(name) > 30:
            name = name[:30]

        if is_send_updated:
            account_dict.update({
                'account_qbd_id': account.quickbooks_id
            })
        else:
            account_dict.update({
                'account_qbd_id': ''
            })

        account_dict.update({
            'odoo_id': account.id,
            # 'code': account.code if account.code else '',
            'name': name if account.name else '',
            'user_type_id': self.getAccountType(account.account_type) if self.getAccountType(
                account.account_type) else ''
        })

        if account.code:
            code = account.code
            account_dict.update({
                'code': (code[:7]) if len(code) > 7 else code
            })
        else:
            account_dict.update({
                'code': ''
            })

        if account_dict:
            return account_dict

    def getAccountType(self, AccountType):
        qbAccountType = ''

        if AccountType == "asset_cash" or AccountType == "asset_cash":
            qbAccountType = "Bank"

        elif AccountType == "asset_receivable":
            qbAccountType = "AccountsReceivable"

        elif AccountType == "liability_payable":
            qbAccountType = "AccountsPayable"

        elif AccountType == "asset_fixed":
            qbAccountType = "FixedAsset"

        elif AccountType == "asset_current":
            qbAccountType = "OtherAsset"

        elif AccountType == "asset_non_current":
            qbAccountType = "OtherCurrentAsset"

        elif AccountType == "liability_credit_card":
            qbAccountType = "CreditCard"

        elif AccountType == "liability_current":
            qbAccountType = "OtherCurrentLiability"

        elif AccountType == "liability_non_current":
            qbAccountType = "LongTermLiability"

        elif AccountType == "equity":
            qbAccountType = "Equity"

        elif AccountType == "income" or AccountType == "equity_unaffected":
            qbAccountType = "Income"

        elif AccountType == "expense":
            qbAccountType = "Expense"

        elif AccountType == "expense_direct_cost":
            qbAccountType = "CostOfGoodsSold"

        elif AccountType == "income_other":
            qbAccountType = "OtherIncome"

        elif AccountType == "expense_depreciation":
            qbAccountType = "OtherExpense"

        return qbAccountType


class AccountPayment(models.Model):
    _inherit = "account.payment"

    quickbooks_id = fields.Char("Quickbook id ", copy=False)
    qbd_ref_no = fields.Char("QBD Ref No.")
    is_updated = fields.Boolean("Is Updated")

    @api.model
    def create(self, vals):
        payment_id = super(AccountPayment, self).create(vals)
        # print ("Payment -------------------------------------- ",payment_id,payment_id.id,payment_id.communication)
        if not payment_id.ref:
            payment_id.ref = 'Payment_'+str(payment_id.id)
        return payment_id

    def write(self, vals):
        if 'is_updated' not in vals and 'quickbooks_id' not in vals:
            vals['is_updated'] = True
        return super(AccountPayment, self).write(vals)

# @dhrup post method of odoo 12

#     def post(self):
#         """ Create the journal items for the payment and update the payment's state to 'posted'.
#             A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
#             and another in the destination reconcilable account (see _compute_destination_account_id).
#             If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
#             If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
#         """
#         for rec in self:
#
#             if rec.state != 'draft':
#                 raise UserError(_("Only a draft payment can be posted."))
#
#             if any(inv.state != 'open' for inv in rec.invoice_ids):
#                 raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))
#
#             # keep the name in case of a payment reset to draft
#             if not rec.name:
#                 # Use the right sequence to set the name
#                 if rec.payment_type == 'transfer':
#                     sequence_code = 'account.payment.transfer.custom'
#                 else:
#                     if rec.partner_type == 'customer':
#                         if rec.payment_type == 'inbound':
#                             sequence_code = 'account.payment.customer.invoice.custom'
#                         if rec.payment_type == 'outbound':
#                             sequence_code = 'account.payment.customer.refund.custom'
#                     if rec.partner_type == 'supplier':
#                         if rec.payment_type == 'inbound':
#                             sequence_code = 'account.payment.supplier.refund.custom'
#                         if rec.payment_type == 'outbound':
#                             sequence_code = 'account.payment.supplier.invoice.custom'
#                 rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
#                     sequence_code)
#                 if not rec.name and rec.payment_type != 'transfer':
#                     raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))
#
#             # Create the journal entry
#             amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
#             move = rec._create_payment_entry(amount)
#
#             # In case of a transfer, the first journal entry created debited the source liquidity account and credited
#             # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
#             if rec.payment_type == 'transfer':
#                 transfer_credit_aml = move.line_ids.filtered(
#                     lambda r: r.account_id == rec.company_id.transfer_account_id)
#                 transfer_debit_aml = rec._create_transfer_entry(amount)
#                 (transfer_credit_aml + transfer_debit_aml).reconcile()
#
#             rec.write({'state': 'posted', 'move_name': move.name})
#         return True
#
    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconcilable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        AccountMove = self.env['account.move'].with_context(
            default_type='entry')
        for rec in self:

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted."))

            if any(inv.state != 'posted' for inv in rec.invoice_ids):
                raise ValidationError(
                    _("The payment cannot be processed because the invoice is not open!"))

            # keep the name in case of a payment reset to draft
            if not rec.name:
                # Use the right sequence to set the name
                if rec.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer.custom'
                else:
                    if rec.partner_type == 'customer':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.customer.invoice.custom'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund.custom'
                    if rec.partner_type == 'supplier':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund.custom'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice.custom'
                rec.name = self.env['ir.sequence'].next_by_code(
                    sequence_code, sequence_date=rec.date)
                if not rec.name and rec.payment_type != 'transfer':
                    raise UserError(
                        _("You have to define a sequence for %s in your company.") % (sequence_code,))

            moves = AccountMove.create(rec._prepare_payment_moves())
            moves.filtered(
                lambda move: move.journal_id.post_at != 'bank_rec').post()

            # Update the state / move before performing any reconciliation.
            move_name = self._get_move_name_transfer_separator().join(moves.mapped('name'))
            rec.write({'state': 'posted', 'move_name': move_name})

            if rec.payment_type in ('inbound', 'outbound'):
                # ==== 'inbound' / 'outbound' ====
                if rec.invoice_ids:
                    (moves[0] + rec.invoice_ids).line_ids \
                        .filtered(lambda line: not line.reconciled and line.account_id == rec.destination_account_id)\
                        .reconcile()
            elif rec.payment_type == 'transfer':
                # ==== 'transfer' ====
                moves.mapped('line_ids')\
                    .filtered(lambda line: line.account_id == rec.company_id.transfer_account_id)\
                    .reconcile()

        return True


    def create_payments(self, payments):
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        # print('\n\n\nPayments ::\n', payments)
        # print('\nTotal Payment Data : ', len(payments))

        if isinstance(payments, list) and len(payments) >= 1:
            last_record_payments = payments[-1]
            for payment in payments:
                vals = {}
                # print(f'\nProcessing Payment: {payment}')

                if 'quickbooks_id' in payment and payment.get('quickbooks_id'):
                    payment_id = self.search(
                        [('quickbooks_id', '=', payment.get('quickbooks_id'))], limit=1)
                    # print(f'\nPayment ID found: {payment_id}')

                    if not payment_id:
                        # CHECK PAYMENT FOR INVOICE - "DHARMESH"
                        vals = self._prepare_payment_dict(payment)
                        if vals:
                            if payment.get('invoice_data'):
                                for invoice_data in payment.get('invoice_data'):
                                    inv = self.env['account.move'].sudo().search(
                                        [('qbd_number', '=', invoice_data)], limit=1)
                                    if inv:
                                        # print('inv::::::::1::::::::::', inv)
                                        # print('inv::::::::1::::::::::', inv.state)
                                        # VALIDATE INVOICE
                                        if inv.state == 'draft':
                                            # print('inv::::::::::2::::::::', inv)
                                            inv.action_post()
                                        # ENSURE INVOICE IS NOT PAID
                                        if inv.payment_state not in ['paid', 'in_payment']:
                                            # REGISTER PAYMENT
                                            payment_register_model = self.env['account.payment.register']
                                            payment_vals = {
                                                'payment_date': fields.Date.today(),
                                                'amount': inv.amount_residual,
                                                'payment_type': 'inbound',
                                                'partner_type': 'customer',
                                                'partner_id': inv.partner_id.id,
                                                'journal_id': vals.get('journal_id'),
                                            }
                                            payment_register = payment_register_model.with_context(
                                                active_model='account.move',
                                                active_ids=inv.ids).create(
                                                payment_vals)
                                            action = payment_register.action_create_payments()
                                            payment_record = self.env['account.payment'].search([('id','=', action.get('res_id'))])
                                            # print('payment recorddddddddddd', payment_record)
                                            if payment_record:
                                                payment_record.write({'quickbooks_id':vals.get('quickbooks_id')})
                                            # Import date Update
                                            date_parsed = parse(payment.get("last_time_modified"))
                                            company.write({
                                                'last_imported_qbd_id_for_payments': date_parsed
                                            })
                                            self._cr.commit()
                                    else:
                                        logger_obj = self.env['qbd.connection.logger'].sudo()
                                        logger_obj.create(
                                            {
                                                'message': 'There was no Invoice Found For :' + str(
                                                    invoice_data) + '. Please import Invoice !',
                                                'type': 'Import Invoice',
                                                'date': datetime.now()
                                            })
                            else:
                                new_payment_id = self.create(vals)
                                if new_payment_id:
                                    # self.env.cr.commit()
                                    # print('New Payment Commited :: ', new_payment_id.name)
                                    date_parsed = parse(payment.get("last_time_modified"))
                                    company.write({
                                        'last_imported_qbd_id_for_payments': date_parsed
                                    })
                                self._cr.commit()

                    else:
                        # print('\n\nUpdate Existing Payment ')
                        # print('\n\nPayment dict =======================================: ', payment_id.id, '\n')
                        vals = self._prepare_payment_dict(payment)

                        if vals:
                            payment_id.write(vals)
                            # print(f'\nPayment Updated: {payment_id}')

                        date_parsed = parse(payment.get("last_time_modified"))
                        company.write({
                            'last_imported_qbd_id_for_payments': date_parsed
                        })
                        self._cr.commit()

                        if payment_id.quickbooks_id == last_record_payments.get('quickbooks_id'):
                            if last_record_payments.get(
                                    'last_time_modified') == company.last_imported_qbd_id_for_payments:
                                _logger.info("AGAIN GONE FOR REQUEST PAYMENTS")
                                limit_rec_import = int(company.import_pay_limit) + int(company.import_pay_limit)
                                if limit_rec_import >= 1500:
                                    company.write({'import_pay_limit': 100})
                                    return True
                                else:
                                    company.write({'import_pay_limit': limit_rec_import})
                                    company.import_payments(limit_rec_import)

        return True


    def _prepare_payment_dict(self, payment):
        vals = {}
        _logger.info("PAYMENT===>>>>>>>>>>>>>>>>>{}".format(payment))

        if payment:
            if 'partner_name' in payment and payment.get('partner_name'):
                partner_id = self.env['res.partner'].search(
                    [('quickbooks_id', '=', payment.get('partner_name'))], limit=1)

                if partner_id:
                    vals.update({
                        'partner_id': partner_id.id
                    })

            vals.update({
                'quickbooks_id': payment.get('quickbooks_id') if payment.get('quickbooks_id') else '',
                'date': payment.get('date') if payment.get('date') else False,
                'partner_type': payment.get('partner_type') if payment.get('partner_type') else 'customer',
                'payment_type': payment.get('payment_type') if payment.get('payment_type') else 'inbound',
                'amount': float(payment.get('amount')) if payment.get('amount') else 0.00,
                'qbd_ref_no': payment.get('payment_ref_number') if payment.get('payment_ref_number') else '',
                # 'payment_method_line_id': 1,
            })

            if 'communication' in payment and payment.get('communication') and payment.get('communication') != 'None':
                vals.update({'ref': payment.get('communication')})

            # if 'payment_method_name' in payment and payment.get('payment_method_name'):
            #     qbd_payment_method_id = self.env['qbd.payment.method'].search(
            #         [('name', '=', payment.get('payment_method_name'))], limit=1)
            #
            #     if qbd_payment_method_id:
            #         journal_id = self.env['account.journal'].search(
            #             [('qbd_payment_method_id', '=', qbd_payment_method_id.id)], limit=1)
            #         # print(f"Journal ID found: {journal_id}")
            #
            #         if journal_id:
            #             vals.update({'journal_id': journal_id.id})
            #         else:
            #             raise UserError(
            #                 'Please set Journal for QBD Payment Method - ' + payment.get('payment_method_name'))

            # if payment.get('payment_method_name') == None:
            #     journal_id = self.env['account.journal'].search([], limit=1)
            #     # print(f"Default Journal ID found: {journal_id}")
            #
            #     if journal_id:
            #         vals.update({'journal_id': journal_id.id})

            if 'payment_method_name' in payment and payment.get('payment_method_name'):
                if payment.get('payment_method_name') == 'Cash':
                    journal_id = self.env['account.journal'].search([('name', '=', 'Cash'), ('code', '=', 'CSH1')], limit=1)
                    if journal_id:
                        vals.update({'journal_id': journal_id.id})
                else:
                    journal_id = self.env['account.journal'].search([('name', '=', 'Bank'),('code', '=', 'BNK1')],limit=1)
                    if journal_id:
                        vals.update({'journal_id': journal_id.id})

        if vals:
            # print(f"Prepared Payment Dictionary: {vals}")
            return vals

    def export_payments(self, is_vendor_payment=False):
        # print('Export Payments !!!!!! 2222222222222')
        payment_data_list = []
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        if company.export_pay_limit:
            limit = int(company.export_pay_limit)
        else:
            limit = 0

        if company.export_payment_date:
            export_date = company.export_payment_date
        else:
            export_date = False
        if is_vendor_payment:
            filters = [('quickbooks_id', '=', False), ('state', '=','posted'), ('payment_type', '=', 'outbound')]
        else:
            filters = [('quickbooks_id', '=', False), ('state', '=','posted'), ('payment_type', '=', 'inbound')]

        if export_date:
            filters.append(('date', '>=', export_date))

        payments = self.search(filters, limit=limit)
        # print('Payments ::',payments)

        if payments:
            for payment in payments:
                payment_dict = {}
                payment_dict = self.get_paymet_dict(payment)

                if payment_dict:
                    payment_data_list.append(payment_dict)

        if payment_data_list:
            # print('\n\nPayment data list :::: ',payment_data_list)
            # print('\n\nTotal Payment Count ::: ',len(payment_data_list),'\n\n')

            company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
            headers = {'content-type': "application/json"}
            data = payment_data_list

            data = {'payments_list': data}

            _logger.info("DATA=====>>>>>>>>>>>>>>>>>{}".format(data))

            if is_vendor_payment:
                response = requests.request('POST', company.url + '/export_vendor_payments', data=json.dumps(data),
                                        headers=headers,
                                        verify=False)
            else:
                response = requests.request('POST', company.url + '/export_payments', data=json.dumps(data),
                                            headers=headers,
                                            verify=False)

            try:
                resp = ast.literal_eval(response.text)
                # print("======================response==================",response)
                _logger.info("RESPONSE===>>>>>>>>>>>>>>>>>>>>>>{}".format(resp))
                
                if isinstance(resp, dict):

                    for res in resp.get('Data'):
                        if resp.get('Message'):
                            raise UserError(_('No Payments Exported'))
                        if 'odoo_id' in res and res.get('odoo_id'):
                            payment_id = self.browse(int(res.get('odoo_id')))
                            if payment_id:
                                payment_id.write({
                                    'quickbooks_id': res.get('quickbooks_id'),
                                    'qbd_ref_no': res.get('payment_ref_number') if res.get('payment_ref_number') else False,
                                })
                                date_parsed = parse(res.get('last_modified_date'))
                                if is_vendor_payment:
                                    company.write({
                                        'export_vendor_payment_date': date_parsed
                                    })
                                else:
                                    company.write({
                                        'export_payment_date': date_parsed
                                    })
                else:
                    raise UserError(_("No Data in Response Check Quickbook Desktop Terminal"))
            except Exception as ex:
                _logger.error(str(ex))
                raise UserError(str(ex))
        return True


    def get_paymet_dict(self, payment):
        payment_dict = {}

        inv_qb_id = False
        invoice_id = False

        if payment.ref:
            invoice_id = self.env['account.move'].search(
                [('name', '=', payment.ref)], limit=1)
        if invoice_id:
            if invoice_id.amount_residual >= payment.amount:
                inv_qb_id = invoice_id.quickbooks_id if invoice_id.quickbooks_id else False

        # print ("Invoice QBD ID ---------------------------------------", inv_qb_id, invoice_id, payment.communication.split("/")[0])
        payment_dict.update({
            # 'ref_number': payment.name if len(payment.name)<=11 else payment.id,
            'ref_number': payment.qbd_ref_no,
            'odoo_id': payment.id,
            'partner_name': payment.partner_id.quickbooks_id if payment.partner_id else False,
            'date': payment.date.strftime('%Y-%m-%d') if payment.date else False,
            'amount': payment.amount if payment.amount else '',
            'payment_method_name': payment.journal_id.qbd_payment_method_id.quickbooks_id if payment.journal_id else '',
            'ref': payment.ref if payment.ref else '',
            'invoice_quickbooks_number': inv_qb_id,
        })

        # print ("Payment Dict -------------------------------", payment_dict)
        if payment_dict:
            return payment_dict


class AccountPayRegInherit(models.TransientModel):
    _inherit = "account.payment.register"

    qbd_ref_no = fields.Char('QBD Reference Number ')

    @api.model
    def create(self, vals):
        res = super(AccountPayRegInherit, self).create(vals)
        return res

    def _create_payment_vals_from_wizard(self, batch_result):
        res = super(AccountPayRegInherit,
                    self)._create_payment_vals_from_wizard(batch_result)
        # print("res")
        res.update({'qbd_ref_no': self.qbd_ref_no})

        return res
