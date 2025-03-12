from odoo import api, fields, models, _
import requests
import ast
import json
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

from email.policy import default

# from sqlalchemy import false

from datetime import datetime
from dateutil.parser import *
from odoo.exceptions import RedirectWarning, ValidationError, UserError
from requests.exceptions import ConnectionError

class QBDLoger(models.Model):
    _name = 'qbd.loger'
    _description = 'QBD Logger'
    _order = 'id desc'
    operation = fields.Char("Operation")
    odoo_id = fields.Char('Odoo ID')
    qbd_id = fields.Char('QBD ID')
    message = fields.Char('Message')
    # res_company_id = fields.Many2one('res.company')

class QBD_DuplicateLogger(models.Model):
    _name = 'qbd.duplicates.logger'
    _description = 'QBD Duplicates Logger'

    odoo_id = fields.Char('Odoo ID')
    name = fields.Char("Name")
    parent_dcode = fields.Char("Parent/Default Code")
    qbd_id = fields.Char("Quickbooks ID")
    type = fields.Selection([
        ('product', 'Product'),
        ('vendor', 'Vendor'),
        ('customer', 'Customer'),
        ], string='Type')
    message = fields.Char('Message')

class QBD_OrderInvoiceLogger(models.Model):
    _name = 'qbd.orderinvoice.logger'
    _description = 'QBD Order Invoice Logger'
    odoo_id = fields.Char('Odoo ID')
    name = fields.Char("Name")
    qbd_id = fields.Char("Quickbooks ID")
    type = fields.Selection([
        ('sale', 'Sales Order'),
        ('invoice', 'Invoices'),
        ], string='Type')
    message = fields.Char('Message')

class QBD_ConnectionLogger(models.Model):
    _name = 'qbd.connection.logger'
    _rec_name = 'message'
    _description = 'QBD Connection Logger'
    _order = 'id desc'


    message = fields.Char('Message')
    type = fields.Char('Type')
    date = fields.Datetime('Date')




class QBD_LinkedLogger(models.Model):
    _name = 'qbd.linked.logger'
    # _rec_name = 'message'
    _description = 'QBD Linked Logger'
    # _order = 'id desc'


    message = fields.Char('Message')
    invoice_id = fields.Char('Invoice Id')
    sale_qbd_id = fields.Char('Sale Order QBD id')
    type = fields.Char('Type')
    date = fields.Datetime('Date')


    def import_specific_order(self, qbd_sale_order_no=None):
        is_imported = False
        headers = {'content-type': "application/json"}
        formatted_data = []
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        # if not limit_rec_import:
        if company.import_so_limit:
            limit = company.import_so_limit
        else:
            limit = 0

        if self.sale_qbd_id:
            params = {
                'to_execute_account': 3,
                'fetch_record': 'one',
                'qbd_sale_order_id': self.sale_qbd_id,
            }
        
            # try:
            company_id = self.env.company
            # _logger.info("ComPANY ===res saleorder========>>>>>>>>>>>>>>>{}".format(company_id))
            response = requests.request('GET', company_id.url + '/import_sales_order', params=params,
                                        headers=headers,
                                        verify=False)

            formatted_data = json.loads(response.text)
            _logger.info("FORMATTED DATA===res saleorder========>>>>>>>>>>>>>>>>{}".format(formatted_data))

            if formatted_data :
                is_imported = self.env['sale.order'].with_context(skip_last_import_update=True).create_sale_orders(
                    formatted_data)


            if is_imported:
                params = {
                    'to_execute_account': 3,
                    'qbd_invoice_number': self.invoice_id,
                    # 'is_vendor_bill': 'True' if is_vendor_bill else ''
                }

            try:
                response = requests.request('GET', company_id.url + '/import_invoice', params=params, headers=headers,
                                            verify=False)
                # print("\n\n response.text2 : ", response.text)
            except Exception as e:
                raise UserError(e)

            formatted_data = json.loads(response.text)
            print("formatted_dataformatted_dataformatted_dataformatted_data:::      ", formatted_data)

        if formatted_data:
            is_imported = self.env['account.move'].with_context(skip_last_import_update=True).create_invoice(
                formatted_data)

            return company.sendMessage({'Message': "Data imported Successful !!"})