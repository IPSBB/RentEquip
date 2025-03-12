from unicodedata import name
from odoo import api, fields, models, _
import requests
import ast
import json
from datetime import datetime, timedelta
import time
from odoo.exceptions import UserError, ValidationError 
import re
import logging
from dateutil.parser import *
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qbd_tax_code = fields.Many2one('qbd.tax.code')
    

    # def _prepare_invoice_line(self):
    #     res = super(SaleOrderLine, self)._prepare_invoice_line()

    #     # if self.qbd_tax_code:
    #     #     res['qbd_tax_code'] = self.qbd_tax_code.id
    #     return res

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        super(SaleOrderLine, self)._compute_amount()
        if self.tax_id:
            self.qbd_tax_code = self.tax_id[0].qbd_tax_code
            
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_discount(self):
        super(SaleOrderLine, self)._compute_discount()
        if self.tax_id:
            self.qbd_tax_code = self.tax_id[0].qbd_tax_code

    def _compute_tax_id(self):
        for line in self:
            fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(
                lambda r: not line.company_id or r.company_id == line.company_id)
            line.tax_id = fpos.map_tax(
                taxes, line.product_id, line.order_id.partner_shipping_id) if fpos else taxes
            line.qbd_tax_code = line.tax_id.qbd_tax_code.id
            # print (" ----------------------------------------------------- ",line.tax_id)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    quickbooks_id = fields.Char("Quickbook id ", copy=False)
    qbd_sale_order_no = fields.Char('QBD SO No.', copy=False)
    qbd_memo = fields.Text('QBD Memo')
    is_updated = fields.Boolean('Is Updated')
    
    @api.model
    def create(self,vals):
        # print("\n\n\n\n\n Sale ORDER===>>>",vals)
        return super(SaleOrder,self).create(vals)
    def write(self, vals):
        # print("\n\n in create of sale order", vals)
        if 'is_updated' not in vals and 'quickbooks_id' not in vals and 'state' not in vals and 'date_order' not in vals and 'procurement_group_id' not in vals:
            vals['is_updated'] = True

        return super(SaleOrder, self).write(vals)

    def create_sale_orders(self, sale_orders):
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        _logger.info("SALE ORDER====>>>>>>>>>>>>>>{}".format(sale_orders))
        # _logger.info("Last RECORD===>>>>>>>>>>>>>>>>>{}".format(sale_orders[-1]))
        
        if isinstance(sale_orders, list) and len(sale_orders) >= 1:
            # _logger.info("SALE ORDER+===>>>>>>>>>>{}".format(sale_orders))
            # _logger.info("LENGTH==>>>>>>>>>>>>>>>>>>>{}".format(type(sale_orders)))
            last_record_so = sale_orders[-1]
            for order in sale_orders:
                vals = {}
                if 'quickbooks_id' in order and order.get('quickbooks_id'):
                    sale_order_id = self.search(
                        [('quickbooks_id', '=', order.get('quickbooks_id')),('state','not in', ['sale', 'cancel'])], limit=1)
                    if not sale_order_id:
                        # create new SO
                        vals = self._prepare_sale_order_dict(order)
                        if vals:
                            # _logger.info("SALE ORDER CREATE VALS====>>>{}".format(vals))
                            new_sale_order_id = self.create(vals)
                            
                            if 'order_lines' in order and order.get('order_lines'):
                                order_lines = order.get('order_lines')
                                # _logger.info("SALE ORDER ID===>>{}".format(new_sale_order_id))

                                so_line_id_list = self.create_sale_order_lines(
                                    order_lines, new_sale_order_id)
                                if new_sale_order_id:
                                    self.env.cr.commit()
                                    
                                if not self._context.get('skip_last_import_update', False):

                                    date_parsed = parse(order.get("last_time_modified"))
                                    company.write({
                                        'last_imported_qbd_id_for_sale_orders': date_parsed
                                    })

                            ### This code is commented as its causing confusion while importing the Sale order ###
                            # if 'state' in order and order.get('state'):
                            #     if order.get('state') == 'sale':
                            #         new_sale_order_id.action_confirm()

                            #         if not new_sale_order_id.order_line:
                            #             new_sale_order_id.action_cancel()

                            if 'date_order' in order and order.get('date_order'):
                                new_sale_order_id.write(
                                    {'date_order': order.get('date_order')})

                    if sale_order_id:
                        # _logger.info("SALE ORDER ID===>>>{}".format(sale_order_id))
                        vals = self._prepare_sale_order_dict(order)
                        # _logger.info(
                        #     "SALE ORDER UPDATE VALS====>>>{}".format(vals))
                        sale_order_id.write(vals)
                        if 'order_lines' in order and order.get('order_lines'):
                            self.update_order_lines(
                                order.get('order_lines'), sale_order_id)


                        if not self._context.get('skip_last_import_update', False):
                            company.write({
                                            'last_imported_qbd_id_for_sale_orders': order.get("last_time_modified")
                                        })
                        #### If the records is getting repeated this will inc the limit and try to fetch the new records
                        #    which will have other modified date to resolve the conflict of importing same data ####
                        if sale_order_id.quickbooks_id == last_record_so.get('quickbooks_id'):
                            # _logger.info("AGAIN FOR REQUEST")
                            
                            if last_record_so.get('last_time_modified') == company.last_imported_qbd_id_for_sale_orders:
                                limit_rec_import = int(company.import_so_limit) + int(company.import_so_limit)
                                # _logger.info("Limit REC IMPORT====>>>>>>>>>>>>>>>>{}".format(limit_rec_import))
                                if limit_rec_import >= 200:
                                    company.write({'import_so_limit': 10})
                                    return True
                                else:
                                    company.write({'import_so_limit': limit_rec_import})
                                    company.import_order(limit_rec_import)
        return True

    def _prepare_sale_order_dict(self, order):

        vals = {}

        if order:
            vals.update({
                'quickbooks_id': order.get('quickbooks_id') if order.get('quickbooks_id') else '',
                'date_order': order.get('date_order') if order.get('date_order') else '',
                'qbd_sale_order_no': order.get('qbd_sale_order_number') if order.get('qbd_sale_order_number') else '',
                'qbd_memo': order.get('qbd_memo') if order.get('qbd_memo') else '',
            })

            if 'partner_name' in order and order.get('partner_name'):
                partner_id = self.env['res.partner'].search(
                    [('quickbooks_id', '=', order.get('partner_name')), ('active', 'in', [True, False])], limit=1)
                if partner_id:
                        vals.update({'partner_id': partner_id['id']})

                else:
                    company_id = self.env.user.company_id
                    partner_id = company_id.import_partner(
                        order.get('partner_name'))
                    # _logger.info("Partner_id===>>>> {}".format(partner_id))
                    if partner_id:
                        vals.update({'partner_id': partner_id['id']})       
                 
        if vals:
            return vals

    def create_sale_order_lines(self, order_lines, order_id):
        so_line_id_list = []
        
        if order_lines:
            for line in order_lines:
                vals = {'order_id': order_id.id}
                if 'product_name' in line and line.get('product_name'):
                    # _logger.info("QUICKBOOK ID==>>>>>>>>>>>>>>{}".format(line.get('product_name')))
                    product_id = self.env['product.product'].search(
                        [('quickbooks_id', '=', line.get('product_name'))])
                    # _logger.info("PRODUCT ID===>>>>>>>>>>>{}".format(product_id))
                    # Streamlined implementation to always add tax, even for non-taxable items
                    if 'tax_code' in line and line.get('tax_code'):
                        tax_code = self.env['qbd.tax.code'].search([('name', '=', line.get('tax_code'))])
                        if tax_code:
                            vals.update({'qbd_tax_code': tax_code.id})

                            # Always attempt to add the tax, regardless of taxable status
                            if 'tax_qbd_id' in line and line.get('tax_qbd_id'):
                                tax_id = self.env['account.tax'].search(
                                    [('quickbooks_id', '=', line.get('tax_qbd_id'))])

                                if tax_id:
                                    vals.update({'tax_id': [(6, 0, [tax_id.id])]})
                                else:
                                    vals.update({'tax_id': [(6, 0, [])]})
                            else:
                                vals.update({'tax_id': [(6, 0, [])]})
                    else:
                        vals.update({'tax_id': [(6, 0, [])]})


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

                else:
                    continue

                vals.update({
                    'price_unit': float(line.get('price_unit')) if line.get('price_unit') else 0.00,
                    'product_uom_qty': float(line.get('product_uom_qty')) if line.get('product_uom_qty') else 0.00,
                    
                    'qty_invoiced': line.get('qty_invoiced') if line.get('qty_invoiced') else 0.00,

                })

                if line.get('name'):
                    string=line.get('name')
                    # _logger.info("LINE DESC===>>>>>>>>>>>{}".format(string))
                    text = self.cleanup_productdesc(string)
                    # _logger.info("TEXT===>>>>>>>>>>>>{}".format(text))
                    vals.update({
                        'name': text if text else '',
                    })
                if vals:
                    # _logger.info("Sale Order Line List====>>>>{}".format(vals))
                    so_line_id = self.env['sale.order.line'].create(vals)
                    so_line_id.write({'tax_id' : vals.get('tax_id') })
                    if so_line_id:
                        so_line_id_list.append(so_line_id)
                # _logger.info("VALS=============>>>>>>>>>>>{}".format(vals))
        if so_line_id_list:
            # print('so_line_id_list:::::::""""""""         ', so_line_id_list)
            return so_line_id_list
    
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

    def update_order_lines(self, order_lines_data, order_id):
        so_line_id = None
        product_qbd_id_list = []
        if order_id:
            for line in order_lines_data:
                exist_line = False
                ##search product in existed order if exist then update that line else create new line
                if order_id.order_line.filtered(lambda l: l.product_id.quickbooks_id == line.get('product_name')):
                    exist_line = order_id.order_line.filtered(lambda l: l.product_id.quickbooks_id == line.get('product_name'))

                if exist_line:
                    ##update the lines with new vals from qbd ..
                    exist_vals = {'price_unit': float(line.get('price_unit')) if line.get('price_unit') else 0.00,
                                        'product_uom_qty': float(line.get('product_uom_qty')) if line.get('product_uom_qty') else 0.00,
                                        'name': line.get('name') if line.get('name') else '',
                                        'qty_invoiced': line.get('qty_invoiced') if line.get('qty_invoiced') else 0.00,
                                        }
                    if line.get('tax_code'):
                        tax_code = self.env['qbd.tax.code'].search(
                            [('name', '=', line.get('tax_code'))],limit=1)
                        if tax_code:
                            exist_vals.update({'qbd_tax_code': tax_code.id})
                        if tax_code.is_taxable:
                            if line.get('tax_qbd_id'):
                                tax_id = self.env['account.tax'].search(
                                    [('quickbooks_id', '=', line.get('tax_qbd_id'))],limit=1)
                                if tax_id:
                                    exist_vals.update({
                                        'tax_id': [(6, 0, [tax_id.id])]
                                    })
                            else:
                                exist_vals.update({
                                    'tax_id': [(6, 0, [])]
                                })
                        else:
                            exist_line.write({
                                'tax_id': [(6, 0, [])]
                            })

                    exist_line.write(exist_vals)
                    continue
                else:
                    if line.get('product_name'):
                        print('\n\n+++++++++++++If product not found in line so create new product')
                        vals = {}
                        vals.update({'order_id': order_id.id})

                        if 'product_name' in line and line.get('product_name'):
                            product_id = self.env['product.template'].search(
                                [('quickbooks_id', '=', line.get('product_name'))])
                            print(product_id,'product_idproduct_idproduct_idproduct_idproduct_idbbbbbbbbbbbb')

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

                        vals.update({
                            'price_unit': float(line.get('price_unit')) if line.get('price_unit') else 0.00,
                            'product_uom_qty': float(line.get('product_uom_qty')) if line.get('product_uom_qty') else 0.00,
                            'name': line.get('name') if line.get('name') else '',
                            'qty_invoiced': line.get('qty_invoiced') if line.get('qty_invoiced') else 0.00,
                        })
                        if vals:
                            so_line_id = self.env['sale.order.line'].create(vals)

        if so_line_id:
            return True

    def export_sale_orders(self, order_id=False):
        # print('\n\nExport Sale Orders Calleeedd !!!!\n\n')
        order_data_list = []
        loger_dict = {}

        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id

        company.env['qbd.orderinvoice.logger'].search([]).unlink()
        company.check_tax_code_for_order_invoices()

        if not company.qb_default_tax:
            raise UserError(
                'Set Default Tax in Company -> QBD Account and Taxes Configuration -> Default Tax')

        if company.export_so_limit:
            limit = int(company.export_so_limit)
        else:
            limit = 0

        if company.export_sales_order_date:
            export_date = company.export_sales_order_date
        else:
            export_date = False

        self.env.cr.execute(
            "SELECT odoo_id FROM qbd_orderinvoice_logger WHERE type='sale'")
        result = self.env.cr.fetchall()
        so_data_list = []
        for rec in result:
            so_data_list.append(int(rec[0]))
        print (so_data_list)

        filters = [('id', 'not in', so_data_list),
                   ('state', 'in', ['sale', 'done'])]

        if export_date:
            export_date = fields.Datetime.from_string(export_date)
            # print("Before ------------------------------ ", type(export_date), export_date)
            export_date_start = datetime(
                export_date.year, export_date.month, export_date.day)
            # print ("After ------------------------------ ",type(export_date), export_date_start)
            export_date_end = export_date_start + \
                timedelta(hours=23, minutes=59, seconds=59)
            # print ("After ------------------------------ ",type(export_date), export_date_end)

            filters.append(
                ('date_order', '>=', export_date_start.strftime("%Y-%m-%d %H:%M:%S")))
            filters.append(
                ('date_order', '<=', export_date_end.strftime("%Y-%m-%d %H:%M:%S")))

        if company.export_updated_record:
            filters.append(('quickbooks_id', '!=', False))
            filters.append(('is_updated', '=', True))
        else:
            filters.append(('quickbooks_id', '=', False))

        _logger.info("Filter ====>>>>  {}".format(filters))
        # orders = self.search(filters, limit=limit)
        if order_id:
            orders = order_id
        else:
            orders = self.search(filters, limit=limit)
        _logger.info("SALE ORDER===>>>>>>>>>>>>>>>>{}".format(orders))
        print('Orders ::: ',orders)

        if orders:
            for order in orders:
                order_dict = {}
                if company.export_updated_record:
                    order_dict = self.get_order_dict(
                        order, company.export_updated_record)
                else:
                    order_dict = self.get_order_dict(order)
                    _logger.info("ORDER DICT ===>>>>>>>>>>{}".format(order_dict))
                if order_dict:
                    order_data_list.append(order_dict)

        if order_data_list:
            print('\n\nOrders data : ',order_data_list)
            # print('\nTotal Orders : ',len(order_data_list))
            _logger.info("ORDER LIST===>>>>>>>>>>>>>>>>>>{}".format(order_data_list))
            company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
            headers = {'content-type': "application/json"}
            data = order_data_list

            data = {'sale_orders_list': data}

            response = requests.request('POST', company.url + '/export_sale_orders', data=json.dumps(data),
                                        headers=headers,
                                        verify=False)

            # print("####################33Response Text", type(response.text), response.text)
            
            try:
                resp = ast.literal_eval(response.text)
                _logger.info("Response==>>>>>>>>>>>>>{}".format(resp))
                # print('Resp@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ : ', resp)
                if isinstance(resp,dict):
                    if company.export_updated_record == False:
                        for res in resp.get('Data'):
                            if resp.get('Message'):
                                raise UserError(_('No Sale Order Exported'))
                            if 'odoo_id' in res and res.get('odoo_id'):
                                so_id = self.browse(int(res.get('odoo_id')))
                                if so_id:
                                    so_id.write({
                                        'quickbooks_id': res.get('quickbooks_id'),
                                        'qbd_sale_order_no': res.get('qbd_sale_order_no') if res.get('qbd_sale_order_no') else '',
                                    })
                            loger_dict.update({'operation': 'Export Partner',
                                            'odoo_id': res.get('odoo_id'),
                                            'qbd_id': res.get('quickbooks_id'),
                                            'message': res.get('messgae')
                                            })
                            qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
                            # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})
                            # print("\n\n\n\nDatetime", res.get('last_modified_date'))
                            date_parsed = parse(res.get('last_modified_date'))
                            company.write({
                                'export_sales_order_date': date_parsed
                            })
                    else:
                        for res in resp.get('Data'):
                            if resp.get('Message'):
                                raise UserError(_('No Sale Order Exported'))
                            if 'odoo_id' in res and res.get('odoo_id'):
                                so_id = self.browse(int(res.get('odoo_id')))
                                if so_id:
                                    so_id.write({'is_updated': False})
                            loger_dict.update({'operation': 'Export Partner',
                                            'odoo_id': res.get('odoo_id'),
                                            'qbd_id': res.get('quickbooks_id'),
                                            'message': res.get('messgae')
                                            })
                            qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
                            # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})
                            # print("\n\n\n\nDatetime", res.get('last_modified_date'))
                            # date_parsed = parse(res.get('last_modified_date'))
                            # company.write({
                            #     'export_sales_order_date': date_parsed
                            # })
                else:
                    raise UserError(_("No Data in Response Check Quickbook Desktop Terminal"))
            except Exception as ex:
                _logger.error(str(ex))
                raise UserError(str(ex))
        return True
    def get_order_dict(self, order, export_updated_record=False):
        order_dict = {}

        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        default_tax_on_order = company.qb_default_tax.name

        if export_updated_record:
            order_dict.update({
                'sale_order_qbd_id': order.quickbooks_id,
            })
        else:
            order_dict.update({
                'sale_order_qbd_id': '',
            })

        order_dict['odoo_order_number'] = order.name if len(
            order.name) < 11 else order.id
        order_dict['default_tax_on_order'] = default_tax_on_order
        if not order.partner_id.quickbooks_id:
            ##export partner fist if not avaible ...............
            order.partner_id.export_partners(order.partner_id)
        order_dict.update({
            'odoo_id': order.id,
            'qbd_memo': order.name,
            'partner_name': order.partner_id.quickbooks_id,
            'confirmation_date': order.date_order.strftime('%Y-%m-%d'),
        })

        if order.order_line:
            order_dict.update({
                'order_lines': self.get_order_lines(order)
            })

        if order_dict:
            return order_dict

    def get_order_lines(self, order):
        order_lines = []

        for line in order.order_line:
            line_dict = {}

            description = line.name if line.name else ''
            bad_chars = [';', ':', '!', "*", "$", "'"]
            for i in bad_chars:
                description = description.replace(i, "")

            if line.product_id:
                if not line.product_id.quickbooks_id:
                    ##if product not avialble into qbd side then export first
                    line.product_id.export_products([line.product_id])
                line_dict.update({
                    'product_name': line.product_id.quickbooks_id if line.product_id else '',
                    'name': description,
                    'product_uom_qty': line.product_uom_qty if line.product_uom_qty else '',
                    'price_unit': line.price_unit if line.price_unit else '',
                    'tax_id': line.tax_id[0].quickbooks_id if line.tax_id else '',
                    'qbd_tax_code': line.qbd_tax_code.name if line.qbd_tax_code.name else '',
                    'price_subtotal': line.price_subtotal if line.price_subtotal else '',
                })

            if line_dict:
                order_lines.append(line_dict)

        if order_lines:
            return order_lines

    def export_sale_order_to_qbd(self):
        '''
            This method gets invoked from a server action
            to export selected sale order to QBD
        '''
        _logger.info("Sale Order TO BE EXPORTED ARE {}".format(self))
        self.export_sale_orders(order_id=self)
