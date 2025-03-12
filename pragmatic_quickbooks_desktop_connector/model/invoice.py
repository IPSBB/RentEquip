from odoo import api, fields, models, _
import requests
import ast
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging
import re
import json

_logger = logging.getLogger(__name__)
from dateutil.parser import *


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def create(self, vals):
        if vals['type'] == 'sale':
            sequence_id = self.env['ir.sequence'].search(
                [('code', '=', 'invoice_sequencing')])
            vals['sequence'] = sequence_id.id
        res = super(AccountJournal, self).create(vals)
        return res

    # @api.multi
    def write(self, vals):
        if 'type' in vals:
            if vals['type'] == 'sale':
                sequence_id = self.env['ir.sequence'].search(
                    [('code', '=', 'invoice_sequencing')])
                vals['sequence'] = sequence_id.id
        elif self.type == 'sale':
            sequence_id = self.env['ir.sequence'].search(
                [('code', '=', 'invoice_sequencing')])
            vals['sequence'] = sequence_id.id
        res = super(AccountJournal, self).write(vals)
        return res


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    qbd_tax_code = fields.Many2one('qbd.tax.code')

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        super(AccountInvoiceLine, self)._compute_product_uom_id()
        vals = {}
        if self.tax_ids:
            vals['qbd_tax_code'] = self.tax_ids[0].qbd_tax_code.id
        self.update(vals)

    @api.onchange('tax_ids')
    def _onchange_tax_id(self):
        vals = {}
        if self.tax_ids:
            vals['qbd_tax_code'] = self.tax_ids[0].qbd_tax_code.id
            self.update(vals)

    # @api.model
    # def write(self, vals):
    #     _logger.info("VALS===>>>>>>>>>>>>>>>>>>>>>>>{}".format(vals))
    #     return super(AccountInvoiceLine, self).write(vals)


class AccountInvoice(models.Model):
    _inherit = "account.move"

    quickbooks_id = fields.Char("Quickbook id ", copy=False)
    qbd_number = fields.Char("QBD INV No.", copy=False)
    is_updated = fields.Boolean('Is Updated')
    lpo_no = fields.Char('LPO #', copy=False)
    veh_or_w_bill = fields.Char('VEH/W.BILL#', copy=False)
    etr_no = fields.Char('ETR #', copy=False)
    qbd_tax = fields.Many2one('account.tax', string="QBD Tax", copy=False)

    # def _check_balanced(self):
    #     ''' Assert the move is fully balanced debit = credit.
    #     An error is raised if it's not the case.
    #     '''
    #     moves = self.filtered(lambda move: move.line_ids)
    #     if not moves:
    #         return

    #     # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
    #     # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
    #     # It happens as the ORM makes the create with the 'no_recompute' statement.
    #     self.env['account.move.line'].flush(
    #         self.env['account.move.line']._fields)
    #     self.env['account.move'].flush(['journal_id'])
    #     self._cr.execute('''
    #         SELECT line.move_id, ROUND(SUM(line.debit - line.credit), currency.decimal_places)
    #         FROM account_move_line line
    #         JOIN account_move move ON move.id = line.move_id
    #         JOIN account_journal journal ON journal.id = move.journal_id
    #         JOIN res_company company ON company.id = journal.company_id
    #         JOIN res_currency currency ON currency.id = company.currency_id
    #         WHERE line.move_id IN %s
    #         GROUP BY line.move_id, currency.decimal_places
    #         HAVING ROUND(SUM(line.debit - line.credit), currency.decimal_places) >= 0.5;
    #     ''', [tuple(self.ids)])

    #     query_res = self._cr.fetchall()
    #     # print('query_res : ', query_res)
    #     if query_res:
    #         ids = [res[0] for res in query_res]
    #         sums = [res[1] for res in query_res]
    #         raise UserError(
    #             _("Cannot create unbalanced journal entry. Ids: %s\nDifferences debit - credit: %s") % (ids, sums))

    def write_taxcode(self, res):
        for rec in res.invoice_line_ids:
            move_line_obj = self.env['account.move.line'].search([('id', '=', rec.id)])
            if rec.tax_ids:
                _logger.info("TAX IDS===>>>>>>>>>>{}".format(rec.tax_ids))
                move_line_obj.qbd_tax_code = rec.tax_ids[0].qbd_tax_code.id
                _logger.info("ACCOUNT LINE ===>>>>>>>>>>>>>>>>>>>>{}".format(move_line_obj.qbd_tax_code))

    @api.model
    def create(self, vals):
        res = super(AccountInvoice, self).create(vals)
        self.write_taxcode(res)
        _logger.info("RES===>>>>>>>>>>>>>>>>>>>>{}".format(res))
        return res

    def write(self, vals):
        # print("\n\n in create of invoice",self, vals)
        if 'is_updated' not in vals and 'quickbooks_id' not in vals and 'state' not in vals and 'invoice_date' not in vals and 'invoice_date_due' not in vals and 'move_id' not in vals and 'move_name' not in vals and 'ref' not in vals:  # and 'date' not in vals
            vals['is_updated'] = True
        self.write_taxcode(self)
        return super(AccountInvoice, self).write(vals)

    def prepare_invoice(self, invoice_vals, move_type=False, existed_invoice_id=None):
        partner_model = self.env['res.partner']
        invoice_model = self.env['account.move']
        invoice_id = False

        is_vendor_bill = move_type == 'in_invoice'
        # Retrieve or create a partner (customer) record
        for invoice in invoice_vals:
            if 'partner_name' in invoice and invoice.get('partner_name'):
                partner = partner_model.search([('quickbooks_id', '=', invoice.get('partner_name'))], limit=1)
            if not partner:
                company_id = self.env.user.company_id
                if is_vendor_bill:
                    # For vendor bills, import vendors
                    partner = company_id.import_vendor(invoice.get('partner_name'))
                else:
                    # For customer invoices, import customers
                    partner = company_id.import_partner(invoice.get('partner_name'))
                    
                if partner:
                    # Refresh partner search after import
                    partner = partner_model.search([('quickbooks_id', '=', invoice.get('partner_name'))], limit=1)

                ##TO DO
            # partner_data = {
            #     'quickbooks_id': partner_qbd_id,
            #     'name': 'Customer Name',  # Replace with the actual customer name
            #     # Add other partner data fields as needed
            # }
                # partner = partner_model.create(partner_data)

            invoice_data = {
                'partner_id': partner.id,
                'invoice_date': fields.Date.today(),
                'quickbooks_id': invoice.get('quickbooks_id'),
                'qbd_number': invoice.get('number') if invoice.get('number') else '',
                'lpo_no': invoice.get('po_number') if invoice.get('po_number') else '',
                'etr_no': invoice.get('etr_number') if invoice.get('etr_number') else '',
                'veh_or_w_bill': invoice.get('veh_bill') if invoice.get('veh_bill') else '',
                'move_type': move_type,
                # 'invoice_date_due': '2024-02-29',  # Replace with the actual due date
                # Add other invoice data fields as needed
            }
            # if move_type  == 'in_invoice':
            #     invoice_data.update({'move_type':'in_invoice'})
            # else:
            #     invoice_data.update({'move_type': 'out_invoice'})

            linked_transactions = invoice.get('linked_transactions')
            if linked_transactions:
                qbd_sale_order_no = linked_transactions[0] if isinstance(linked_transactions, list) else linked_transactions
                # Search for sale order with matching qbd_sale_order_no
                sale_order = self.env['sale.order'].search([
                    ('qbd_sale_order_no', '=', qbd_sale_order_no),
                    ('partner_id', '=', partner.id)
                ], limit=1)

                if sale_order:
                    invoice_data.update({
                        'invoice_origin': sale_order.name,
                    })
                else:
                    # Create log entry when sale order is not found
                    self.env['qbd.linked.logger'].create({
                        'message': f'Sale order is not imported for the invoice {invoice.get("number")}',
                        'invoice_id': invoice.get('number'),
                        'sale_qbd_id': qbd_sale_order_no,
                        'type': 'sale_order_missing',
                        'date': fields.Datetime.now()
                    })
                    continue
                
            if 'date_due' in invoice and invoice.get('date_due'):
                invoice_data.update({'invoice_date_due': invoice.get('date_due')})
            # Create the invoice
            if 'term_name' in invoice and invoice.get('term_name'):
                term_id = self.env['account.payment.term'].search(
                    [('name', '=', invoice.get('term_name'))])

                if term_id:
                    invoice_data.update(({'invoice_payment_term_id': term_id.id}))
            if 'date_invoice' in invoice and invoice.get('date_invoice'):
                invoice_data.update({'invoice_date': invoice.get('date_invoice')})
            # if not existed_invoice_id:
            #     invoice_id = invoice_model.create(invoice_data)

            # Create invoice lines based on the QBD response
            if existed_invoice_id:
                existe_inv_line = []
                invoice_id = existed_invoice_id
                for line_data in invoice.get('invoice_lines'):
                    product_qbd_id = line_data.get('product_name')
                    if not product_qbd_id:
                        continue
                    product = self.env['product.product'].search([('quickbooks_id', '=', product_qbd_id)], limit=1)
                    if not product:
                        company_id = self.env.user.company_id
                        company_id.import_specific_product(line_data.get('product_name'))
                        product = self.env['product.product'].search(
                        [('quickbooks_id', '=', product_qbd_id)])

                    for product in product:
                        if product:
                            if existed_invoice_id.invoice_line_ids.filtered(lambda r: r.product_id == product):
                                for line in existed_invoice_id.invoice_line_ids.filtered(
                                        lambda r: r.product_id == product):
                                    tax_qbd_id = line_data.get('tax_qbd_id')
                                    tax = self.env['account.tax'].search([('quickbooks_id', '=', tax_qbd_id)], limit=1)
                                    # Sanitize the 'name' field to remove all non-printable characters
                                    name = line_data.get('name', 'Product Description')
                                    if name:
                                        # Remove non-printable characters using regex
                                        name = re.sub(r'[^\x20-\x7E]', '', name).strip()
                                    price_quntity = line_data.get('quantity', 1)
                                    price_subtotal = line_data.get('price_unit', 0)
                                    # try:
                                    #     price_unit = float(line_data.get('price_unit', 0))
                                    # except (TypeError, ValueError):
                                    price_unit = 0.0
                                    invoice_line_data = {
                                        'product_id': product.id,
                                        'name': name,
                                        'quantity': float(line_data.get('quantity', 1)),
                                        # 'price_unit': price_unit,
                                        'account_id': product.property_account_income_id.id if product.property_account_income_id else product.categ_id.property_account_income_categ_id.id,
                                        'tax_ids': [(6, 0, [tax.id])] if tax else [],
                                    }
                                    if line_data.get('price_unit'):
                                        try:
                                            price_unit = float(line_data['price_unit'])
                                        except (TypeError, ValueError):
                                            price_unit = 0.0
                                        invoice_line_data.update({'price_unit': price_unit})
                                    else:
                                        invoice_line_data.update({'price_unit': 0.0})
                                    
                                    linked_transactions = invoice.get('linked_transactions')
                                    print("----------linked_transactions------------",linked_transactions)
                                    if linked_transactions:
                                        qbd_sale_order_no = invoice['linked_transactions'][0] if isinstance(invoice['linked_transactions'], list) else invoice['linked_transactions']
                                        # Search for sale order with matching qbd_sale_order_no
                                        sale_order = self.env['sale.order'].search([
                                            ('qbd_sale_order_no', '=', qbd_sale_order_no),
                                            # ('state', 'in', ['sale', 'done']),
                                            ('partner_id', '=', partner.id)
                                        ], limit=1)
                                    # Link to sale order line if sale order exists
                                        if sale_order:
                                            sale_line = sale_order.order_line.filtered(lambda l: l.product_id.id == product.id)

                                            if sale_line:
                                                invoice_line_data.update({
                                                    'sale_line_ids': [(4, sale_line.id)]
                                                })
                                    line.write(invoice_line_data)


                            else:
                                tax_qbd_id = line_data.get('tax_qbd_id')
                                tax = self.env['account.tax'].search([('quickbooks_id', '=', tax_qbd_id)], limit=1)
                                # Sanitize the 'name' field to remove all non-printable characters
                                name = line_data.get('name', 'Product Description')
                                if name:
                                    # Remove non-printable characters using regex
                                    name = re.sub(r'[^\x20-\x7E]', '', name).strip()
                                invoice_line_data = {
                                    'product_id': product.id,
                                    'name': name,
                                    'quantity': float(line_data.get('quantity', 1)),
                                    # 'price_unit': float(line_data.get('price_unit', 0)),
                                    'account_id': product.property_account_income_id.id if product.property_account_income_id else product.categ_id.property_account_income_categ_id.id,
                                    'tax_ids': [(6, 0, [tax.id])] if tax else [],
                                    'move_id': existed_invoice_id.id,
                                }
                                if line_data.get('price_unit'):
                                    try:
                                        price_unit = float(line_data['price_unit'])
                                    except (TypeError, ValueError):
                                        price_unit = 0.0
                                    invoice_line_data.update({'price_unit': price_unit})
                                else:
                                    invoice_line_data.update({'price_unit': 0.0})
                                

                                linked_transactions = invoice.get('linked_transactions')
                                print("----------linked_transactions------------",linked_transactions)
                                if linked_transactions:
                                    qbd_sale_order_no = invoice['linked_transactions'][0] if isinstance(invoice['linked_transactions'], list) else invoice['linked_transactions']
                                    # Search for sale order with matching qbd_sale_order_no
                                    sale_order = self.env['sale.order'].search([
                                        ('qbd_sale_order_no', '=', qbd_sale_order_no),
                                        # ('state', 'in', ['sale', 'done']),
                                        ('partner_id', '=', partner.id)
                                    ], limit=1)
                                    # Link to sale order line if sale order exists
                                    if sale_order:
                                        sale_line = sale_order.order_line.filtered(lambda l: l.product_id.id == product.id)
                                        if sale_line:
                                            invoice_line_data.update({
                                                'sale_line_ids': [(4, sale_line.id)]
                                            })

                                self.env['account.move.line'].create(invoice_line_data)

            else:
                new_line_invoice = []
                for line_data in invoice.get('invoice_lines'):
                    product_qbd_id = line_data.get('product_name')
                    if not product_qbd_id:
                        continue
                    if product_qbd_id:
                        product = self.env['product.product'].search([('quickbooks_id', '=', product_qbd_id)], limit=1)
                        if not product:
                            company_id = self.env.user.company_id
                            company_id.import_specific_product(line_data.get('product_name'))
                            product = self.env['product.product'].search(
                            [('quickbooks_id', '=', product_qbd_id)])
                        if product:
                            tax_qbd_id = line_data.get('tax_qbd_id')
                            tax = self.env['account.tax'].search([('quickbooks_id', '=', tax_qbd_id)], limit=1)
                            # Sanitize the 'name' field to remove all non-printable characters
                            name = line_data.get('name', 'Product Description')
                            if name:
                                # Remove non-printable characters using regex
                                name = re.sub(r'[^\x20-\x7E]', '', name).strip()

                            invoice_line_data = {
                                'product_id': product.id,
                                'name': name,
                                'quantity': float(line_data.get('quantity', 1)),
                                # 'price_unit': float(line_data.get('price_unit', 0)) if line_data.get('price_unit') else 0,
                                'account_id': product.property_account_income_id.id if product.property_account_income_id else product.categ_id.property_account_income_categ_id.id,
                                'tax_ids': [(6, 0, [tax.id])] if tax else [],
                            }
                            if line_data.get('price_unit'):
                                try:
                                    price_unit = float(line_data['price_unit'])
                                except (TypeError, ValueError):
                                    price_unit = 0.0
                                invoice_line_data.update({'price_unit': price_unit})
                            else:
                                invoice_line_data.update({'price_unit': 0.0})

                            linked_transactions = invoice.get('linked_transactions')
                            print("----------linked_transactions------------",linked_transactions)
                            if linked_transactions:
                                qbd_sale_order_no = invoice['linked_transactions'][0] if isinstance(invoice['linked_transactions'], list) else invoice['linked_transactions']
                                # Search for sale order with matching qbd_sale_order_no
                                sale_order = self.env['sale.order'].search([
                                    ('qbd_sale_order_no', '=', qbd_sale_order_no),
                                    # ('state', 'in', ['sale', 'done']),
                                    ('partner_id', '=', partner.id)
                                ], limit=1)
                                # Link to sale order line if sale order exists
                                if sale_order:
                                    sale_line = sale_order.order_line.filtered(lambda l: l.product_id.id == product.id)
                                    if sale_line:
                                        invoice_line_data.update({
                                            'sale_line_ids': [(4, sale_line.id)]
                                        })

                            new_line_invoice.append((0, 0, invoice_line_data))
                if new_line_invoice:
                    invoice_data.update({'invoice_line_ids': new_line_invoice})

                # invoice_data.invoice_line_ids['name'] = 'vishal'
                invoice_id = invoice_model.create(invoice_data)

        return invoice_id

    def create_invoice(self, invoices):
        # _logger.info("\n\n\n\n\n\n\nINVOICES===>>>>>>>>>>>>>>>>>>>>>>{}".format(invoices))
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        journal_id = self.env['account.journal'].search(
            [('type', '=', 'sale')])
        if not journal_id:
            raise ValidationError('Please create journal of type sale ..')
        if isinstance(invoices, list) and len(invoices) >= 1:
            last_record_inv = invoices[-1]
            for invoice in invoices:
                vals = {}

                if 'quickbooks_id' in invoice and invoice.get('quickbooks_id'):
                    invoice_id = self.search(
                        [('quickbooks_id', '=', invoice.get('quickbooks_id'))], limit=1)
                    if not invoice_id:
                        new_invoice_id = self.prepare_invoice([invoice], move_type='out_invoice',
                                                              existed_invoice_id=None)
                        if new_invoice_id:
                            new_invoice_id.write({'state': 'draft'})

                        # IF GET BOOLEAN IS_PAID TRUE -> VALIDATE INVOICE - DHARMESH
                        if new_invoice_id and invoice.get('state') and invoice.get('state') == 'paid':
                            if new_invoice_id.invoice_line_ids:
                                new_invoice_id.sudo().action_post()

                        if new_invoice_id:
                            self.env.cr.commit()

                            if not self._context.get('skip_last_import_update', False):
                                date_parsed = parse(
                                    invoice.get("last_time_modified"))
                                company.write({
                                    'last_imported_qbd_id_for_invoice': date_parsed
                                })
                    if invoice_id:
                        # print("invoice founddddddddddddddddd",invoice_id)
                        if invoice_id.state in ['posted', 'cancel']:
                            continue

                        invoice_id = self.prepare_invoice([invoice], move_type='out_invoice',
                                                          existed_invoice_id=invoice_id)

                        # print("existed invice idd::     ",invoice_id)
                        if not self._context.get('skip_last_import_update', False):
                            company.write({
                                'last_imported_qbd_id_for_invoice': invoice.get("last_time_modified")
                            })
                        #### If the records is getting repeated this will inc the limit and try to fetch the new records
                        #    which will have other modified date to resolve the conflict of importing same data ####
                        if invoice_id and invoice_id.quickbooks_id == last_record_inv.get('quickbooks_id'):
                            if last_record_inv.get('last_time_modified') == company.last_imported_qbd_id_for_invoice:
                                _logger.info("AGAIN GONE FOR REQUEST INVOICE")

                                limit_rec_import = int(company.import_inv_limit) + int(company.import_inv_limit)

                                # _logger.info("Limit REC IMPORT====>>>>>>>>>>>>>>>>{}".format(limit_rec_import))
                                if limit_rec_import >= 50:
                                    company.write({'import_inv_limit': 10})
                                    return True
                                else:
                                    company.write({'import_inv_limit': limit_rec_import})
                                    company.import_invoice(limit_rec_import)
        return True

    def create_vendor_bill(self, vendor_bill):
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        journal_id = self.env['account.journal'].search([('type', '=', 'purchase')])
        is_vendor_bill = True
        if not journal_id:
            raise UserError('Please create journal of type Purchase ..')
        for bill in vendor_bill:
            if 'quickbooks_id' in bill and bill.get('quickbooks_id'):
                vendor_bill_id = self.search([('quickbooks_id', '=', bill.get('quickbooks_id'))], limit=1)

                if not vendor_bill_id:
                    new_invoice_id = self.prepare_invoice([bill], move_type='in_invoice', existed_invoice_id=None)

                    if new_invoice_id:
                        new_invoice_id.write({'state': 'draft'})
                        if new_invoice_id:
                            new_invoice_id.write({'state': 'draft'})

                        # IF GET BOOLEAN IS_PAID TRUE -> VALIDATE BILL - DHARMESH
                        if new_invoice_id and bill.get('state') and bill.get('state') == 'paid':
                            if new_invoice_id.invoice_line_ids:
                                new_invoice_id.sudo().action_post()

                        if new_invoice_id:
                            self.env.cr.commit()
                            # print('New Invoice Commited :: ', new_invoice_id.name)
                            company.write({
                                'last_imported_qbd_id_for_vendor_bill': bill.get("last_time_modified")
                            })
                if vendor_bill_id:
                    if vendor_bill_id.state in ['posted', 'cancel']:
                        continue
                    bill_created = self.prepare_invoice([bill], move_type='in_invoice',
                                                        existed_invoice_id=vendor_bill_id)
                    company.write({
                        'last_imported_qbd_id_for_invoice': bill.get("last_time_modified")
                    })

    def _prepare_invoice_dict(self, invoice, is_vendor_bill=None):
        vals = {}
        _logger.info("\n\n\n\n\n\n\nINVOICE===>>>>>>>>>>>>>>>>>>{}".format(invoice))
        if invoice.get('qbd_tax'):
            tax_id = self.env['account.tax'].search([('quickbooks_id', '=', invoice.get('qbd_tax'))])
            _logger.info("TAX ===>>>>>>>>>>>>{}".format(tax_id))
        if invoice:
            vals.update({
                'quickbooks_id': invoice.get('quickbooks_id') if invoice.get('quickbooks_id') else '',
                'invoice_date_due': invoice.get('date_due') if invoice.get('date_due') else '',
                'qbd_number': invoice.get('number') if invoice.get('number') else '',
                'lpo_no': invoice.get('po_number') if invoice.get('po_number') else '',
                'etr_no': invoice.get('etr_number') if invoice.get('etr_number') else '',
                'veh_or_w_bill': invoice.get('veh_bill') if invoice.get('veh_bill') else '',
            })
            if invoice.get('qbd_tax'):
                vals.update({'qbd_tax': tax_id.id})
            if is_vendor_bill:
                vals.update({'move_type': 'in_invoice'})
            else:
                vals.update({'move_type': 'out_invoice'})

                # print("Invoice Vals==>>>", vals)
            if 'partner_name' in invoice and invoice.get('partner_name'):
                partner_id = self.env['res.partner'].search(
                    [('quickbooks_id', '=', invoice.get('partner_name')), ('active', 'in', [True, False])],
                    limit=1)

                if partner_id:
                    vals.update({'partner_id': partner_id.id})
                else:
                    company_id = self.env.user.company_id
                    partner_id = company_id.import_partner(
                        invoice.get('partner_name'))
                    # if partner_id:
                    if type(partner_id) != dict:
                        vals.update({'partner_id': partner_id.id})
            if 'term_name' in invoice and invoice.get('term_name'):
                term_id = self.env['account.payment.term'].search(
                    [('name', '=', invoice.get('term_name'))])

                if term_id:
                    vals.update(({'invoice_payment_term_id': term_id.id}))
            if 'date_invoice' in invoice and invoice.get('date_invoice'):
                vals.update({'invoice_date': invoice.get('date_invoice')})

        if vals:
            return vals

    def create_invoice_lines(self, invoice_lines, invoice_id):
        invoice_line_id_list = []
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id

        if invoice_lines:
            for line in invoice_lines:
                _logger.info(_('\n\nline IDs : %s' % line))
                vals_ol = {}
                vals_col = {}
                vals_tol = {}

                if invoice_id:
                    vals_ol.update({'move_id': invoice_id.id})
                    vals_col.update({'move_id': invoice_id.id})
                    vals_tol.update({'move_id': invoice_id.id})

                if 'product_name' in line and line.get('product_name'):
                    product_id = self.env['product.product'].search(
                        [('quickbooks_id', '=', line.get('product_name'))])

                    if product_id:
                        vals_ol.update({'product_id': product_id.id})
                        vals_col.update({'product_id': False})
                        vals_tol.update({'product_id': False})
                    if 'tax_code' in line and line.get('tax_code'):
                        # print("TAX CODE", line.get('tax_code'))
                        tax_code = self.env['qbd.tax.code'].search(
                            [('name', '=', line.get('tax_code'))])
                        if tax_code:
                            vals_ol.update({'qbd_tax_code': tax_code.id})
                        _logger.info(_("\n\n tax_code : %s" % tax_code))

                        if tax_code.is_taxable and tax_code.quickbooks_id:
                            tax_id = self.env['account.tax'].search(
                                [('quickbooks_id', '=', tax_code.quickbooks_id)], limit=1)
                            if tax_id:
                                _logger.info(_('Got Tax : %s' % tax_id))
                                vals_ol.update(
                                    {'tax_ids': [(6, 0, [tax_id.id])]})
                                vals_col.update({'tax_ids': False})
                                vals_tol.update({'tax_ids': False})
                            else:
                                _logger.warning('Tax Error')
                    else:
                        vals_ol.update({'tax_ids': False})
                        vals_col.update({'tax_ids': False})
                        vals_tol.update({'tax_ids': False})

                    if product_id.property_account_income_id:
                        vals_ol.update(
                            {'account_id': product_id.property_account_income_id.id})
                    elif product_id.categ_id.property_account_income_categ_id:
                        vals_ol.update(
                            {'account_id': product_id.categ_id.property_account_income_categ_id.id})
                    else:
                        vals_ol.update(
                            {'account_id': company.qb_income_account.id})

                    if invoice_id.partner_id.property_account_receivable_id:
                        vals_col.update(
                            {'account_id': invoice_id.partner_id.property_account_receivable_id.id})
                        vals_tol.update(
                            {'account_id': invoice_id.partner_id.property_account_receivable_id.id})
                else:
                    continue

                vals_ol.update({
                    'quantity': float(line.get('quantity')) if line.get('quantity') else 0.00,
                    # 'exclude_from_invoice_tab': False,
                })

                if line.get('name'):
                    string = line.get('name')
                    _logger.info("LINE DESC===>>>>>>>>>>>{}".format(string))
                    text = self.cleanup_productdesc(string)
                    # _logger.info("TEXT===>>>>>>>>>>>>{}".format(text))
                    vals_ol.update({
                        'name': text if text else '',
                    })
                vals_col.update({
                    'quantity': float(line.get('quantity')) if line.get('quantity') else 0.00,
                    'name': False,
                    # 'exclude_from_invoice_tab': True,
                })

                vals_tol.update({
                    'quantity': float(line.get('quantity')) if line.get('quantity') else 0.00,
                    'name': False,
                    # 'exclude_from_invoice_tab': True,
                })

                if 'price_unit' in line and line.get('price_unit') != 'None':
                    vals_ol.update(
                        {'price_unit': float(line.get('price_unit'))})
                    vals_col.update(
                        {'price_unit': -(float(line.get('price_unit')))})

                    vals_ol.update(
                        {'credit': abs(vals_ol['quantity']) * abs(float(line.get('price_unit')))})
                    vals_ol.update({'debit': 0})

                    vals_col.update({'credit': 0})
                    vals_col.update(
                        {'debit': abs(vals_col['quantity']) * abs(float(line.get('price_unit')))})
                else:
                    vals_ol.update({'price_unit': 0})
                    vals_col.update({'price_unit': 0})

                    vals_ol.update({'credit': 0})
                    vals_ol.update({'debit': 0})

                    vals_col.update({'credit': 0})
                    vals_col.update({'debit': 0})

                if vals_ol.get('tax_ids'):
                    tax_amount = tax_id.amount
                    vals_tol['price_unit'] = abs(
                        float(vals_ol['quantity']) * vals_ol['price_unit'] * float(tax_amount / 100))
                    vals_tol['credit'] = vals_tol['price_unit']
                    vals_tol['debit'] = 0

                    vals_col['debit'] += vals_tol['credit']

                    vals_ol['tax_repartition_line_id'] = False
                    vals_col['tax_repartition_line_id'] = False
                    tax_repartition_line_id = self.env['account.tax.repartition.line'].search(
                        [('repartition_type', '=', 'tax')], limit=1)
                    vals_tol['tax_repartition_line_id'] = tax_repartition_line_id.id

                    vals_ol['tax_base_amount'] = 0
                    vals_col['tax_base_amount'] = 0
                    vals_tol['tax_base_amount'] = vals_ol['quantity'] * \
                                                  vals_ol['price_unit']
                else:
                    vals_tol.update({'price_unit': 0})
                    vals_tol.update({'credit': 0})
                    vals_tol.update({'debit': 0})

                if vals_ol and vals_col:
                    data = []
                    # print("VALS OL===>>>", vals_ol)
                    data.append(vals_ol)
                    # print("VALS COL===>>>", vals_col)
                    # data.append(vals_col)
                    if vals_ol.get('tax_ids'):
                        data.append(vals_tol)
                    _logger.info(_('\n\n data : %s ' % data))
                    invoice_line_id = self.env['account.move.line'].create(
                        data)

                    _logger.info(
                        _("5----------------------------------------------------------\n\n%s\n" % invoice_line_id))
                    # invoice_line_id._compute_price()
                    if invoice_line_id:
                        invoice_line_id_list.append(invoice_line_id)
        if invoice_line_id_list:
            return invoice_line_id_list

    def cleanup_productdesc(self, string):
        """
            This Method will cleanup the Byte character from the Order line Description field
        """
        try:
            text = re.sub("[^\x20-\x7E]", "", string)
            text.strip()
        except Exception as e:
            raise UserError(e)
        return text

    def update_invoice_lines(self, invoice_lines, invoice_id):
        # print('In update invoice method: ',invoice_id)
        invoice_line_id = None
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id

        product_qbd_id_list = []
        if invoice_id:
            for invoice_line in invoice_id.invoice_line_ids:
                product_qbd_id_list.append(invoice_line.product_id.quickbooks_id)

            for line in invoice_lines:
                if line.get('product_name') not in product_qbd_id_list:
                    # print('If product not found in line so create new product')
                    vals = {}

                    vals.update({'invoice_id': invoice_id.id})

                    if 'product_name' in line and line.get('product_name'):
                        product_id = self.env['product.product'].search(
                            [('quickbooks_id', '=', line.get('product_name'))])

                        if product_id:
                            vals.update({
                                'product_id': product_id.id
                            })

                        else:
                            company_id = self.env.user.company_id
                            company_id.import_specific_product(line.get('product_name'))
                            product_id = self.env['product.product'].search(
                            [('quickbooks_id', '=', line.get('product_name'))])

                            if product_id:
                                vals.update({'product_id': product_id.id})

                        if product_id.property_account_income_id:
                            vals.update({'account_id': product_id.property_account_income_id.id})
                        elif product_id.categ_id.property_account_income_categ_id:

                            vals.update({'account_id': product_id.categ_id.property_account_income_categ_id.id})
                        else:
                            vals.update({'account_id': company.qb_income_account.id})
                    else:
                        continue

                    vals.update({
                        'price_unit': float(line.get('price_unit')) if line.get('price_unit') else 0.00,
                        'quantity': float(line.get('quantity')) if line.get('quantity') else 0.00,
                        'name': line.get('name') if line.get('name') else '',
                    })

                    if vals:
                        invoice_line_id = self.env['account.move.line'].create(vals)

        if invoice_line_id:
            return True

    # @api.multi

    def export_invoices(self, invoice_lst=False, is_vendor_bill=False):
        # print('Export Invoices !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        loger_dict = {}
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        if company and not company.url:
            raise ValidationError("Please check the qbd connection for company %s" %(company.name))

        company.env['qbd.orderinvoice.logger'].search([]).unlink()
        company.check_tax_code_for_order_invoices()

        if not company.qb_default_tax:
            raise UserError(
                'Set Default Tax in Company -> QBD Account and Taxes Configuration -> Default Tax')

        if self._context.get('is_vendor_bill'):
            limit = int(company.export_vendor_bill_limit)
        elif company.export_inv_limit:
            limit = int(company.export_inv_limit)
        else:
            limit = 0

        if self._context.get('is_vendor_bill'):
            export_date = company.export_vendor_bill_date
        elif company.export_invoice_date:
            export_date = company.export_invoice_date
        else:
            export_date = False

        self.env.cr.execute(
            "SELECT odoo_id FROM qbd_orderinvoice_logger WHERE type='invoice'")
        result = self.env.cr.fetchall()
        invoice_data_list = []
        for rec in result:
            invoice_data_list.append(int(rec[0]))

        filters = [('id', 'not in', invoice_data_list),
                   ('state', 'in', ['posted'])]

        if export_date:
            export_date = fields.Datetime.from_string(export_date)
            export_date_start = datetime(
                export_date.year, export_date.month, export_date.day)
            export_date_end = export_date_start + \
                              timedelta(hours=23, minutes=59, seconds=59)

        if self._context.get('is_vendor_bill'):
            filters.append(('move_type', '=', 'in_invoice'))
        else:
            filters.append((('move_type', '=', 'out_invoice')))

        if export_date:
            filters.append(('invoice_date', '>=', export_date))

        if company.export_updated_record:
            filters.append(('quickbooks_id', '!=', False))
            filters.append(('is_updated', '=', True))
        else:
            filters.append(('quickbooks_id', '=', False))

        if invoice_lst:
            invoices = invoice_lst
        else:
            _logger.info("FILTER===>>>>>>>>>>>>>>>>{}".format(filters))
            invoices = self.search(filters, limit=limit)
            _logger.info("INVOICESS===>>>>>>>>>>>>>>>>>>>>{}".format(invoices))

        invoice_data_list = []
        if invoices:
            for invoice in invoices:
                invoice_dict = {}
                if company.export_updated_record:
                    if self._context.get('is_vendor_bill'):
                        invoice_dict = self.get_invoice_dict(invoice, company.export_updated_record,
                                                             is_vendor_bill=True)
                    else:
                        invoice_dict = self.get_invoice_dict(invoice, company.export_updated_record)
                else:
                    if self._context.get('is_vendor_bill'):
                        invoice_dict = self.get_invoice_dict(invoice, is_vendor_bill=True)
                    else:
                        invoice_dict = self.get_invoice_dict(invoice)

                if invoice_dict:
                    invoice_data_list.append(invoice_dict)

        if invoice_data_list:
            # print('\n\nInvoice data : ', invoice_data_list)
            # print('\nTotal Invoices : ', len(invoice_data_list))

            company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
            headers = {'content-type': "application/json"}
            data = invoice_data_list

            data = {'invoices_list': data}

            url = None

            _logger.info("DATA IS {}".format(data))
            response = requests.request('POST', company.url + '/export_invoices', data=json.dumps(data),
                                        headers=headers,
                                        verify=False)

            # print("Response Text", type(response.text), response.text)

            try:
                resp = ast.literal_eval(response.text)

                # print('Resp : ', resp)
                if isinstance(resp, dict):
                    if resp.get('Message'):
                        raise UserError(_('No Invoice Exported'))
                    if company.export_updated_record == False:
                        for res in resp.get('Data'):
                            if 'odoo_id' in res and res.get('odoo_id'):
                                inv_id = self.browse(int(res.get('odoo_id')))
                                if inv_id:
                                    inv_id.write({
                                        'quickbooks_id': res.get('quickbooks_id') if res.get(
                                            'quickbooks_id') else False,
                                        'qbd_number': res.get('qbd_invoice_ref_no') if res.get(
                                            'qbd_invoice_ref_no') else '',
                                    })
                            loger_dict.update({'operation': 'Export Invoice',
                                               'odoo_id': res.get('odoo_id'),
                                               'qbd_id': res.get('quickbooks_id'),
                                               'message': res.get('messgae')
                                               })
                            qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
                            # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})
                            if 'last_modified_date' in res and res.get('last_modified_date'):
                                date_parsed = parse(res.get('last_modified_date'))
                                if self._context.get('is_vendor_bill'):
                                    company.write({
                                        'export_vendor_bill_date': date_parsed
                                    })
                                else:
                                    company.write({
                                        'export_invoice_date': date_parsed
                                    })
                    else:
                        for res in resp.get('Data'):
                            if res.get('Message'):
                                raise UserError(_('No Invoice Exported'))
                            if 'odoo_id' in res and res.get('odoo_id'):
                                inv_id = self.browse(int(res.get('odoo_id')))
                                if inv_id:
                                    if res.get('messgae') == 'Successfully Updated':
                                        inv_id.write({'is_updated': False})

                            loger_dict.update({'operation': 'Export Invoice',
                                               'odoo_id': res.get('odoo_id'),
                                               'qbd_id': res.get('quickbooks_id'),
                                               'message': res.get('messgae')
                                               })
                            qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
                            # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})
                            if 'last_modified_date' in res and res.get('last_modified_date'):
                                date_parsed = parse(res.get('last_modified_date'))
                                if self._context.get('is_vendor_bill'):
                                    company.write({
                                        'export_vendor_bill_date': date_parsed
                                    })
                                else:
                                    company.write({
                                        'export_invoice_date': date_parsed
                                    })

                else:
                    raise UserError(_("No Data in Response Check Quickbook Desktop Terminal"))
            except Exception as ex:
                _logger.error(str(ex))
                raise ValidationError(str(ex))
        return True

    def get_invoice_dict(self, invoice, export_updated_record=False, is_vendor_bill=False):
        invoice_dict = {}
        _logger.info("INVOICE===>>>>>>>>>>>>{}".format(invoice))
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        # default_tax_on_invoice = company.qb_default_tax.name
        if not invoice.qbd_tax:
            raise UserError("Set QBD Tax to Invoice")
        default_tax_on_invoice = invoice.qbd_tax.name
        # print ("Default Taxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx ",default_tax_on_invoice)

        if export_updated_record:
            invoice_dict.update({
                'invoice_order_qbd_id': invoice.quickbooks_id,
            })
        else:
            invoice_dict.update({
                'invoice_order_qbd_id': '',
            })

        invoice_dict['odoo_invoice_number'] = invoice.name if len(
            invoice.name) < 11 else invoice.id
        invoice_dict['default_tax_on_invoice'] = default_tax_on_invoice
        if is_vendor_bill:
            invoice_dict.update({'is_vendor_bill': True})

        if not invoice.partner_id.quickbooks_id:
            if invoice.partner_id.supplier_rank:
                invoice.partner_id.export_vendors(invoice.partner_id)

            elif invoice.partner_id.customer_rank:
            
                invoice.partner_id.export_partners(invoice.partner_id)

        invoice_dict.update({
            'odoo_id': invoice.id,
            # 'name': order.name,
            'qbd_memo': invoice.name if invoice.name else '',
            'partner_name': invoice.partner_id.quickbooks_id,
            'invoice_date': invoice.invoice_date.strftime('%Y-%m-%d'),
            'lpo_no': invoice.lpo_no,
            'veh_or_w_bill': invoice.veh_or_w_bill,
            'etr_no': invoice.etr_no,
        })

        if invoice.invoice_line_ids:
            invoice_dict.update({
                'invoice_lines': self.get_invoice_lines(invoice)
            })
        if invoice_dict:
            return invoice_dict

    def get_invoice_lines(self, invoice):
        invoice_lines = []
        for line in invoice.invoice_line_ids:
            line_dict = {}
            description = line.name if line.name else ''
            bad_chars = [';', ':', '!', "*", "$", "'"]
            for i in bad_chars:
                description = description.replace(i, "")
            if not line.product_id.quickbooks_id:
                ##if product not avialble into qbd side then export first
                line.product_id.export_products([line.product_id])
            if line.product_id:
                line_dict.update({
                    'payment_terms': invoice.partner_id.property_payment_term_id.name if invoice.partner_id.property_payment_term_id.quickbooks_id else '',
                    'ref_number': invoice.id,
                    'product_name': line.product_id.quickbooks_id if line.product_id else '',
                    'name': description,
                    'quantity': line.quantity if line.quantity else '',
                    'price_unit': line.price_unit if line.price_unit else '',
                    'tax_id': line.tax_ids[0].quickbooks_id if line.tax_ids else '',
                    'qbd_tax_code': line.qbd_tax_code.name if line.qbd_tax_code.name else '',
                    'price_subtotal': line.price_subtotal if line.price_subtotal else '',
                })

            if line_dict:
                invoice_lines.append(line_dict)

        if invoice_lines:
            return invoice_lines

    def export_invoice_to_qbd_server_action(self):
        '''
            This method gets invoked from a server action
            to export selected invoices to QBD
        '''
        # ENSURE IF ALL ARE VENDOR BILL OR ALL ARE INVOICES
        if all([x.move_type == 'in_invoice' for x in self]):
            self.export_invoices(invoice_lst=self, is_vendor_bill=True)
        elif all([x.move_type == 'out_invoice' for x in self]):
            # self.export_invoices(invoice_lst=self, is_vendor_bill=False)
            if self.invoice_date:
                self.export_invoices(invoice_lst=self, is_vendor_bill=False)
            else:

                raise UserError(
                    'Invoice Date is required to Export Invoice to QBD')
        else:
            raise UserError(
                'Selected records must be either all invoices or all bills')
