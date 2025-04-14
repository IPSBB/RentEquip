from datetime import datetime as dt
import requests
import ast
import logging
import json
import secrets

# from sqlalchemy import true
from dateutil.parser import *
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class Product(models.Model):
    _inherit = 'product.product'


    def export_product_to_qbd_server_action(self):
        product_lst = []
        for rec in self:
            if (self.env.user.company_id.export_updated_record and rec.is_updated) or not rec.quickbooks_id:
                rec.export_products(product_lst=[rec])

            else:
                _logger.error("NON Conditions matched for product export to the qbd")

    def export_product_cron(self):
        self.export_products()

    def get_product_dict(self, product, is_updated=False):
        # Name name (31 varchar) --DONE
        # IsActive active (1 bit) --DONE
        # Type type --DONE
        # ManufacturerPartNumber barcode (31 varchar)
        # Description name (4095 varchar)
        # SalesTaxCodeRefFullName tax_code (3 varchar)
        # QuantityOnHand qty_available (18 decimal)
        # SalesAndpurchaseSalesDesc description_sale (4095 varchar)
        # SalesAndpurchasePurchaseDesc description_purchase (4095 varchar)
        # SalesOrPurchasePrice sales_purchase_price_and_purchase_cost (18 decimal)
        # SalesAndPurchaseSalesPrice sales_purchase_price_and_purchase_cost (18 decimal) [IF NOT FOUND IN SalesOrPurchasePrice]
        # PurchaseCost sales_purchase_price_and_purchase_cost (18 decimal)
        # SalesPrice sales_price (18 decimal)
        # SalesOrPurchaseAccountRefListID property_account_income_quickbook_id(36 varchar)
        # IncomeAccountRefListID property_account_income_quickbook_id (36 varchar)

        product_dict = {}
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        if is_updated == True:
            product_dict.update({'product_qbd_id': product.quickbooks_id, })
        else:
            product_dict.update({'product_qbd_id': '', })

        name = product.default_code if product.default_code else product.name
        if len(name) > 30:
            name = name[:30]

        bad_chars = [';', ':', '!', "*", "$", "'"]
        for i in bad_chars:
            name = name.replace(i, "")

        description = product.name
        for i in bad_chars:
            description = description.replace(i, "")

        product_dict.update({

            'odoo_id': product.id,
            'product_qbd_id': product.quickbooks_id,
            'name': name,
            'description': description,
            'type': product.type if product.type else '',
            'active': product.active if product.active else True,
            'barcode': product.barcode if product.barcode else '',
            'sales_purchase_price_and_purchase_cost': product.standard_price if product.standard_price else 0.0,
            'sales_price': product.list_price if product.list_price else 0.0,
            'description_purchase': product.description_purchase if product.description_purchase else '',
            'qty_available': product.qty_available if product.qty_available else '',
            'tax_code': product.qbd_tax_code.name if product.qbd_tax_code else '',
        })

        if product.property_account_income_id:
            product_dict.update({
                'property_account_income_quickbook_id': product.property_account_income_id.quickbooks_id
            })
        elif product.categ_id.property_account_income_categ_id:
            product_dict.update({
                'property_account_income_quickbook_id': product.categ_id.property_account_income_categ_id.quickbooks_id
            })

        elif company.qb_income_account:
            if not company.qb_income_account.quickbooks_id:
                raise ValidationError("Please verify the Income Account with a linked QuickBooks ID in the company account configuration.")
            product_dict.update({
                'property_account_income_quickbook_id': company.qb_income_account.quickbooks_id
            })
        else:
            raise UserError('Please set income account for product - {}'.format(product.name))

        if company.qb_asset_account:
            if not company.qb_asset_account.quickbooks_id:
                raise ValidationError("Please verify the Asset Account with a linked QuickBooks ID in the company account configuration.")
            product_dict.update({
                'asset_account_quickbook_id': company.qb_asset_account.quickbooks_id
            })

        if company.qb_cogs_account:
            if not company.qb_cogs_account.quickbooks_id:
                raise ValidationError("Please verify the COGS Account with a linked QuickBooks ID in the company account configuration.")
            product_dict.update({
                'cogs_account_quickbook_id': company.qb_cogs_account.quickbooks_id
            })

        if product_dict:
            # print(product_dict)
            return product_dict


    def export_products(self, product_lst=[]):

        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        if company and not company.url:
            raise ValidationError("Please check the qbd connection for company %s" %(company.name))
        loger_dict = {}
        if company.export_pro_limit:
            limit = int(company.export_pro_limit)
        else:
            limit = 0

        if company.export_updated_record:
            products = self.search([('quickbooks_id', '!=', False),
                                    ('is_updated', '=', True)], limit=limit)
        else:
            products = self.search([('quickbooks_id', '=', False)], limit=limit)

        # IF WE HAVE product_lst in method param set, then products will be reassigned to the list
        if product_lst:
            products = product_lst
            _logger.info("PRODUCTS FOR EXPORT ARE : {}".format(products))

        # print('Hereeeeeeeeeeee in product export\n')
        product_data_list = []

        # print('\nProducts : ', products, '\n')

        if products:

            for product in products:
                product_dict = {}
                # only export updated products
                if company.export_updated_record:
                    product_dict = self.get_product_dict(product, company.export_updated_record)

                # only export newly created records
                else:
                    product_dict = self.get_product_dict(product)
    
                if product_dict:
                    product_data_list.append(product_dict)

        if product_data_list:
            # print('\n\nProduct Data List :: ', product_data_list, '\n\n')
            # print('Total Count : ', len(product_data_list))

            company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
            headers = {'content-type': "application/json"}
            data = product_data_list

            data = {'products_list': data}

            response = requests.request('POST', company.url + '/export_products', data=json.dumps(data),
                                        headers=headers,
                                        verify=False)


            try:

                resp = response.json()
                _logger.info("RESPONSE PRODUUCT==>>>>>>>>>>>%s", resp)
                print('\n\nResp : ', resp, '\n')
                if isinstance(resp, dict):
                    if company.export_updated_record == False:
                        print("in the iffffffffffffffffffffffffffffffffffffffffffffffffff")
                        if resp.get('Message'):
                            raise UserError(_("No Product was Exported"))

                        for res in resp.get('Data'):
                            if 'odoo_id' in res and res.get('odoo_id'):
                                product_id = self.browse(int(res.get('odoo_id')))
                                print('product_id:      ', product_id)

                                if product_id:
                                    if res.get('quickbooks_id'):
                                        product_id.write({'quickbooks_id': res.get('quickbooks_id')})
                                        print(product_id.write({'quickbooks_id': res.get('quickbooks_id')}), "uuuuuuuuuuuuuuuuuuuuuuuuuuuuu")
                            loger_dict.update({'operation': 'Export Product',
                                               'odoo_id': res.get('odoo_id'),
                                               'qbd_id': res.get('quickbooks_id'),
                                               'message': res.get('messgae')
                                               })
                            qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
                            # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})

                    else:
                        print("in the elseeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
                        if resp.get('Message'):
                            raise UserError(_("No Product was Exported"))
                        for res in resp.get('Data'):
                            if 'odoo_id' in res and res.get('odoo_id'):
                                product_id = self.browse(int(res.get('odoo_id')))

                                if product_id:
                                    product_id.write({'is_updated': False})
                            loger_dict.update({'operation': 'Export Product',
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


class ProductTemplate(models.Model):
    _inherit = "product.template"

    invent_adjustment_created = fields.Boolean('Inventory Adjustment', default=False)
    qty_updated = fields.Boolean('QTY UPDATED', default=False)
    quickbooks_id = fields.Char("Quickbook id ", copy=False)
    is_updated = fields.Boolean("Is Updated")
    qbd_tax_code = fields.Many2one('qbd.tax.code')
    qbd_product_type = fields.Selection([('ItemNonInventory', 'Item Non Inventory'),
                                         ('ItemInventory', 'Item Inventory'),
                                         ('ItemGroup', 'Item Group'),
                                         ('ItemService', 'Item Service'),
                                         ('ItemInventoryAssembly', 'Item Inventory Assembly'),
                                         ('ItemOtherCharge', 'Item Other Charge'),
                                         ('ItemFixedAsset', 'Item Fixed Asset')
                                         ])
    full_name = fields.Char('Quickbook Full Name', copy=False)

    def export_product_to_qbd_server_action(self):
        product_lst = []
        for rec in self:
            if (self.env.user.company_id.export_updated_record and rec.is_updated) or not rec.quickbooks_id:
                rec.export_products(product_lst=[rec])

            else:
                _logger.error("NON Conditions matched for product export to the qbd")

    def uncheck_update_flags_server_action(self):
        # print('Self Context : ', self._context, self)
        try:
            for rec in self:
                if rec.qty_updated:
                    rec.write({'qty_updated': False})
            return True
        except Exception as e:
            _logger.error(_('Error : %s' % e))

    def uncheck_inventory_flags_server_action(self):
        try:
            for rec in self:
                if rec.invent_adjustment_created:
                    rec.write({'invent_adjustment_created': False})
        except Exception as e:
            _logger.error(_('Error : %s' % e))

        return True

    @api.model
    def create(self, vals):
        # print ("-------------------------",vals)
        product_id = super(ProductTemplate, self).create(vals)
        if 'qbd_tax_code' in vals:
            check_tax = self.env['qbd.tax.code'].search([('id', '=', vals['qbd_tax_code'])])
            if not check_tax.is_taxable:
                product_id.taxes_id = [(6, 0, [])]
        return product_id

    def write(self, vals):
        # print ("In write of Product Template  11 -------------------------", vals)

        if not 'is_updated' in vals and not 'quickbooks_id' in vals:
            vals['is_updated'] = True
        if 'qbd_tax_code' in vals:
            check_tax = self.env['qbd.tax.code'].search([('id', '=', vals['qbd_tax_code'])])
            if not check_tax.is_taxable:
                # print ("In write of Product Template 22 -------------------------", check_tax.is_taxable)
                vals['taxes_id'] = [(6, 0, [])]
        # print ("In write of Product Template  33 -------------------------", vals)
        return super(ProductTemplate, self).write(vals)

    def _check_product_qbd_id(self):
        '''
            This is a helper function which will validate if the 
            product has QBD ID or not
            
        '''
        if not self.quickbooks_id:
            raise UserError(_('Cannot import BOM for {}, as it does not have QBD ID set'.format(self.name)))

    def _send_response_to_bom(self, parsed_response):
        '''
            helper method to send data to the BOM file
            @params : parsed_reponse(list of dict)
        '''
        self.env['mrp.bom'].create_bom_of_qbd_product(parsed_response)

    def _post(self, qbd_id=None):
        '''
            This method will post the request with qbd_id and will receive the response
            from the QBD
            @params : qbd_id(char)
        '''
        data = {'qbd_id': qbd_id}
        company = self.env.user.company_id
        if not company.url:
            raise UserError(_("QBD Server URL not added for current company !"))
        response = requests.get(company.url + '/' + 'import/BOM', params=data)
        if response.status_code == 200:
            _logger.info("GOT RESPONSE {}".format(response.text))
            try:
                parsed_response = response.json()
                if 'bom_lines' in parsed_response and len(parsed_response['bom_lines']) > 0:
                    self._send_response_to_bom(parsed_response)
                else:
                    _logger.info("NO DATA LENGTH")
            except Exception as ex:
                _logger.error(str(ex))
                raise UserError(str(ex))
        else:
            raise UserError(_(response.text))

    @api.model
    def product_bom_import_qbd(self):
        '''
            This method gets invoked from the server action
            to import BOM of this product from QBD
        '''
        for rec in self:
            # Check if product has QBD ID set
            rec._check_product_qbd_id()
            rec._post(qbd_id=rec.quickbooks_id)

    def export_updated_inventory_to_qbd(self):
        '''
            This method is invoked via CRON to update the product
            quantities to QBD
        '''
        product_ids = self.env['product.product'].sudo().search([('quickbooks_id', '!=', False),
                                                                 ('qty_updated', '=', False),
                                                                 ('type', '=', 'product')], limit=20)
        # print(product_ids)
        product_data_lst = []
        for product_id in product_ids:
            product_data = self._prepare_product_inventory_data(product_id)
            product_data_lst.append(product_data)

        # AFTER FORMATTING MAKE A REQUESTS POST TO THE QBD
        _logger.info("DATA IS {}".format(product_data_lst))
        headers = {'content-type': 'application/json'}
        if product_data_lst:
            company = self.env.user.company_id
            resp = requests.post(company.url + '/' + 'import_product_quantities', data=json.dumps(product_data_lst),
                                 headers=headers, verify=False)
            _logger.info("RESPONSE {} {}".format(resp.text, resp.status_code))
            if resp.status_code == 200:
                for rec in product_ids:
                    rec.qty_updated = True
                    _logger.info("QTY UPDATED !!!")

    def _prepare_product_inventory_data(self, product_id):
        '''
            Acts as a helper method to prepare and return the products inventory data
            @params : product_id(obj)
            @returns : product_data_dict(dict)
        '''
        company = self.env.user.company_id
        product_data_dict = {}
        product_data_dict['AccountRefListID'] = company.qb_asset_account.quickbooks_id
        product_data_dict['TxnDate'] = self._format_date(dt.now().date())
        product_data_dict['RefNumber'] = '{}_{}'.format(product_id.id,
                                                        self._get_ref_number())
        product_data_dict['RefNumber'] = self._truncate_ref_num(product_data_dict['RefNumber'])
        product_data_dict['Memo'] = product_id.description or ''
        product_data_dict['InventoryAdjustmentLineItemRefListID'] = product_id.quickbooks_id
        product_data_dict['InventoryAdjustmentLineQuantityAdjustmentNewQuantity'] = product_id.qty_available
        _logger.info("PRODUCT DICT==>>>>>>>>>>>>>>>>>>{}".format(product_data_dict))
        return product_data_dict

    def import_updated_inventory_qbd_to_odoo(self):
        headers = {'content-type': "application/json"}
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        _logger.info("COMPANY CATEGORY IS-------------> {} ".format(company))
        if company.inventory_adjust_limit:
            limit = company.inventory_adjust_limit
        else:
            limit = 1

        try:
            params = {'to_execute_account': 1, 'function_name': 'import_products', 'limit': limit,
                      'inventory_adjustment': True}
            # print("\n\n im port product before response", params)
            response = requests.request('GET', company.url + '/import_products', params=params, headers=headers,
                                        verify=False)
            formatted_data = json.loads(response.text)
            # print('\n\nFormatted Response Found : ', formatted_data)
            product = self.env['product.template']
            stock_change_qty = self.env['stock.change.product.qty']
            for val in formatted_data:
                product_exists = None
                dictval = product._prepare_product_dict(val)

                if dictval.get('qbd_product_type') == 'ItemInventory':
                    print('\n\nPrdouct Found : ', dictval)
                    product_exists = product.search([('quickbooks_id', '=', dictval.get('quickbooks_id')),
                                                     ('invent_adjustment_created', '=', False)])

                if product_exists:
                    self.adjust_inventory(product_exists, dictval.get('qty_available'))
                    stockvals = {
                        'product_id': product_exists.product_variant_id.id,
                        'new_quantity': abs(dictval.get('qty_available')),
                        'product_tmpl_id': product_exists.id
                    }
                    # print("\n\nFound Stock----------------", product_exists, "\n\n---------------- stock qunat-------", stockvals)
                    _logger.info("vals are ------->{}".format(stockvals))
                    res = stock_change_qty.create(stockvals)
                    product_exists.write({'invent_adjustment_created': True})
                    _logger.info("RES IS ----------->{}".format(res))
                    res.change_product_qty()

        except Exception as e:
            # raise ValidationError(_('Inventory Update Failed due to %s' % str(e)))
            _logger.warning(_('Inventory Update Failed due to %s' % str(e)))

    def adjust_inventory(self, product, quantity):
        """ Adjust inventory of the given products
        """
        stockLocation = self.env.ref('stock.warehouse0')
        print('!!!!!!!!!!!!!!!!!!!!11')
        print(product)
        print(quantity)

        inventory = self.env['stock.quant'].create({
            # 'name': 'QBD Inventory Adjustment',
            'location_id': stockLocation.lot_stock_id.id,
            'product_id': product.product_variant_id.id,
            'inventory_quantity': abs(quantity),
            'product_uom_id': self.env.ref('uom.product_uom_unit').id
        })
        # print('\n\nInventory Adjustment : ', inventory)
        # obj = self.env['stock.inventory.line'].create({
        #     'product_id': product.id,
        #     'product_uom_id': self.env.ref('uom.product_uom_unit').id,
        #     'inventory_id': inventory.id,
        #     'product_qty': abs(quantity),
        #     'location_id': stockLocation.lot_stock_id.id,
        # })
        # print('\n\nInventory Adjustment Line : ',product,quantity,obj)
        inventory.action_apply_inventory()
        # inventory.action_validate()
        return True

    def _format_date(self, dt):
        '''
            Helper method to format and export date
            @params: dt(obj)
            @returns : formatted_date(str) (YYYY-MM-DD)
        '''
        return str(dt.year) + '-' + str(dt.month).zfill(2) + '-' + str(dt.day).zfill(2)

    def _truncate_ref_num(self, ref_num):
        ''' truncates refnumber as QBD allows max 11 char inventory adjustment line table'''
        if (ref_num and len(ref_num) > 11):
            return ref_num[:11]
        else:
            return ref_num

    def _get_ref_number(self):
        ref_number = secrets.token_urlsafe(16)
        _logger.info("Unique Reference Number==>>>{}".format(ref_number))

        return ref_number

    # class ProductProduct(models.Model):
    #     _inherit = "product.product"

    def create_product(self, products):
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id

        if 'product' in products[0]:
            product = products[0].get('product')
            vals = {}
            # print("PRODUCT ----------------------------------------", product)

            if 'quickbooks_id' in product and product.get('quickbooks_id'):
                product_id = self.search([('quickbooks_id', '=', product.get('quickbooks_id'))], limit=1)

                if not product_id:
                    vals = self._prepare_product_dict(product)
                    if vals:

                        new_product_id = self.create(vals)
                        if new_product_id:
                            self.env.cr.commit()
                    return new_product_id

                else:
                    vals = self._prepare_product_dict(product)
                    product_id.write(vals)
                    return product_id

    ##import product from quickbooks....
    def import_product_by_quickbooks_id(self, quickbooks_id):
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        headers = {'content-type': "application/json"}
        params = {'product_qbd_id': quickbooks_id, 'to_execute_account': 3}
        try:
            response = requests.request('GET', self.url + '/import_products', params=params, headers=headers,
                                        verify=False)

        except Exception as e:
            raise UserError(e)
        formatted_data = json.loads(response.text)
        if formatted_data:
            product = self.create_product(formatted_data)
            return product


    def create_products(self, products):
        # print('\n\n\nProducts :: ', products)
        # print('\n\n Total product Count : ', len(products))
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        if len(products) == 0:
            raise UserError(
                "It seems that all of the Products are already imported.")
        imported_product_id = False
        for product in products:
            vals = {}
            if 'quickbooks_id' in product and product.get('quickbooks_id'):
                product_id = self.search([('quickbooks_id', '=', product.get('quickbooks_id'))], limit=1)
                ##search by internal ref ...
                # if not product_id:
                #     product_id = self.search([('default_code', '=', product.get('default_code'))], limit=1)
                # print('product_id:::::::::::222222222222222:::::::::::::::::', product_id)
                if not product_id:
                    vals = self._prepare_product_dict(product)
                    if vals:
                        _logger.info("Process to create product")
                        new_product_id = self.create(vals)
                        if new_product_id:
                            self.env.cr.commit()
                            date_parsed = parse(
                                product.get("last_time_modified"))
                            company.write({
                                'last_imported_qbd_id_for_product': date_parsed
                            })
                            imported_product_id = new_product_id
                else:
                    # update existing product ..........
                    vals = self._prepare_product_dict(product)
                    product_id.write(vals)
                    _logger.info("Updated Product .........")
                    date_parsed = parse(
                        product.get("last_time_modified"))
                    company.write({
                        'last_imported_qbd_id_for_product': date_parsed
                    })

        return imported_product_id

    def _prepare_product_dict(self, product):
        vals = {}
        if product:
            vals.update({
                'name': product.get('name') if product.get('name') else '',
                'quickbooks_id': product.get('quickbooks_id') if product.get('quickbooks_id') else '',
                'default_code': product.get('default_code') if product.get('default_code') else '',
                'active': product.get('active') if product.get('active') else True,
                'standard_price': float(product.get('standard_price')) if product.get('standard_price') else 0.00,
                'list_price': float(product.get('list_price')) if product.get('list_price') else 0.00,
                'description': product.get('description') if product.get('description') else '',
                'qty_available': float(product.get('qty_available')) if product.get('qty_available') else 0.000,
                'description_purchase': product.get('description_purchase') if product.get(
                    'description_purchase') else '',
                'type': product.get('type') if product.get('type') else '',
                'qbd_product_type': product.get('qbd_product_type', False),
                'description_sale': product.get('full_name') if product.get('full_name') else '',
            })

            if 'tax_code' in product and product.get('tax_code'):
                tax_code = self.env['qbd.tax.code'].search([('name', '=', product.get('tax_code'))],limit=1)
                if tax_code:
                    vals.update({
                        'qbd_tax_code': tax_code.id
                    })
            if product.get('barcode'):
                vals.update({'barcode': product.get('barcode')})

            company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
            if 'income_account_id' in product and product.get('income_account_id'):
                account_id = self.env['account.account'].search([('quickbooks_id', '=', product.get('income_account_id'))],
                                                                limit=1)
                if account_id:
                    vals.update({'property_account_income_id': account_id.id})
                if not account_id:
                    if company.qb_income_account:
                        vals.update({'property_account_income_id': company.qb_income_account.id})

            else:
                if company.qb_income_account:
                    vals.update({'property_account_income_id': company.qb_income_account.id})
                else:
                    raise UserError("Please set the Product Income Account in Company Configuration")

            if company.qb_expense_account:
                vals.update({'property_account_expense_id': company.qb_expense_account.id})
            else:
                raise UserError("Please set the Product Expense Account in Company Configuration")
        if vals:
            if 'qbd_product_type' in vals and vals.get('qbd_product_type') == 'ItemInventory':
                if 'type' not in vals:
                    vals.update({'type': 'product'})
            elif 'qbd_product_type' in vals and vals.get('qbd_product_type') ==  'ItemService':
                if 'type' not in vals:
                    vals.update({'type': 'service'})
            else:
                if 'type' not in vals:
                    vals.update({'type': 'consu'})
            return vals

    # def export_products(self, product_lst=[]):
    #
    #     company = self.env['res.users'].search([('id', '=', 2)]).company_id
    #     loger_dict = {}
    #     if company.export_pro_limit:
    #         limit = int(company.export_pro_limit)
    #     else:
    #         limit = 0
    #
    #     if company.export_updated_record:
    #         products = self.search([('quickbooks_id', '!=', False),
    #                                 ('is_updated', '=', True)], limit=limit)
    #     else:
    #         products = self.search([('quickbooks_id', '=', False)], limit=limit)
    #
    #     # IF WE HAVE product_lst in method param set, then products will be reassigned to the list
    #     if product_lst:
    #         products = product_lst
    #         _logger.info("PRODUCTS FOR EXPORT ARE : {}".format(products))
    #
    #     # print('Hereeeeeeeeeeee in product export\n')
    #     product_data_list = []
    #
    #     # print('\nProducts : ', products, '\n')
    #
    #     if products:
    #
    #         for product in products:
    #             product_dict = {}
    #             # only export updated products
    #             if company.export_updated_record:
    #                 product_dict = self.get_product_dict(product, company.export_updated_record)
    #
    #             # only export newly created records
    #             else:
    #                 product_dict = self.get_product_dict(product)
    #                 print("---------------", product_dict)
    #
    #             if product_dict:
    #                 product_data_list.append(product_dict)
    #
    #     if product_data_list:
    #         # print('\n\nProduct Data List :: ', product_data_list, '\n\n')
    #         # print('Total Count : ', len(product_data_list))
    #
    #         company = self.env['res.users'].search([('id', '=', 2)]).company_id
    #         headers = {'content-type': "application/json"}
    #         data = product_data_list
    #
    #         data = {'products_list': data}
    #
    #         response = requests.request('POST', company.url + '/export_products', data=json.dumps(data),
    #                                     headers=headers,
    #                                     verify=False)
    #
    #
    #         try:
    #
    #             resp = response.json()
    #             _logger.info("RESPONSE PRODUUCT==>>>>>>>>>>>%s", resp)
    #             print('\n\nResp : ', resp, '\n')
    #             if isinstance(resp, dict):
    #                 if company.export_updated_record == False:
    #
    #                     if resp.get('Message'):
    #                         raise UserError(_("No Product was Exported"))
    #
    #                     for res in resp.get('Data'):
    #                         if 'odoo_id' in res and res.get('odoo_id'):
    #                             product_id = self.browse(int(res.get('odoo_id')))
    #
    #                             if product_id:
    #                                 if res.get('quickbooks_id'):
    #                                     product_id.write({'quickbooks_id': res.get('quickbooks_id')})
    #                         loger_dict.update({'operation': 'Export Product',
    #                                            'odoo_id': res.get('odoo_id'),
    #                                            'qbd_id': res.get('quickbooks_id'),
    #                                            'message': res.get('messgae')
    #                                            })
    #                         qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
    #                         # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})
    #
    #                 else:
    #                     if resp.get('Message'):
    #                         raise UserError(_("No Product was Exported"))
    #                     for res in resp.get('Data'):
    #                         if 'odoo_id' in res and res.get('odoo_id'):
    #                             product_id = self.browse(int(res.get('odoo_id')))
    #
    #                             if product_id:
    #                                 product_id.write({'is_updated': False})
    #                         loger_dict.update({'operation': 'Export Product',
    #                                            'odoo_id': res.get('odoo_id'),
    #                                            'qbd_id': res.get('quickbooks_id'),
    #                                            'message': res.get('messgae')
    #                                            })
    #                         qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
    #                         # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})
    #             else:
    #                 raise UserError(_("No Data in Response Check Quickbook Desktop Terminal"))
    #         except Exception as ex:
    #             _logger.error(str(ex))
    #             raise UserError(str(ex))
    #     return True

    def get_product_dict(self, product, is_updated=False):
        # Name name (31 varchar) --DONE
        # IsActive active (1 bit) --DONE
        # Type type --DONE
        # ManufacturerPartNumber barcode (31 varchar)
        # Description name (4095 varchar)
        # SalesTaxCodeRefFullName tax_code (3 varchar)
        # QuantityOnHand qty_available (18 decimal)
        # SalesAndpurchaseSalesDesc description_sale (4095 varchar)
        # SalesAndpurchasePurchaseDesc description_purchase (4095 varchar)
        # SalesOrPurchasePrice sales_purchase_price_and_purchase_cost (18 decimal)
        # SalesAndPurchaseSalesPrice sales_purchase_price_and_purchase_cost (18 decimal) [IF NOT FOUND IN SalesOrPurchasePrice]
        # PurchaseCost sales_purchase_price_and_purchase_cost (18 decimal)
        # SalesPrice sales_price (18 decimal)
        # SalesOrPurchaseAccountRefListID property_account_income_quickbook_id(36 varchar)
        # IncomeAccountRefListID property_account_income_quickbook_id (36 varchar)

        product_dict = {}
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        if is_updated == True:
            product_dict.update({'product_qbd_id': product.quickbooks_id, })
        else:
            product_dict.update({'product_qbd_id': '', })

        name = product.default_code if product.default_code else product.name
        if len(name) > 30:
            name = name[:30]

        bad_chars = [';', ':', '!', "*", "$", "'"]
        for i in bad_chars:
            name = name.replace(i, "")

        description = product.name
        for i in bad_chars:
            description = description.replace(i, "")

        product_dict.update({

            'odoo_id': product.id,
            'product_qbd_id': product.quickbooks_id,
            'name': name,
            'description': description,
            'type': product.type if product.type else '',
            'active': product.active if product.active else True,
            'barcode': product.barcode if product.barcode else '',
            'sales_purchase_price_and_purchase_cost': product.standard_price if product.standard_price else 0.0,
            'sales_price': product.list_price if product.list_price else 0.0,
            'description_purchase': product.description_purchase if product.description_purchase else '',
            'qty_available': product.qty_available if product.qty_available else '',
            'tax_code': product.qbd_tax_code.name if product.qbd_tax_code else '',
        })

        if product.property_account_income_id:
            product_dict.update({
                'property_account_income_quickbook_id': product.property_account_income_id.quickbooks_id
            })
        elif product.categ_id.property_account_income_categ_id:
            product_dict.update({
                'property_account_income_quickbook_id': product.categ_id.property_account_income_categ_id.quickbooks_id
            })

        elif company.qb_income_account:
            product_dict.update({
                'property_account_income_quickbook_id': company.qb_income_account.quickbooks_id
            })
        else:
            raise UserError('Please set income account for product - {}'.format(product.name))

        if company.qb_asset_account:
            product_dict.update({
                'AssetAccountRefListID': company.qb_asset_account.quickbooks_id
            })
        # else:
        #     raise UserError('Set Asset account in Company Configuration')

        if company.qb_cogs_account:
            product_dict.update({
                'COGSAccountRefListID': company.qb_cogs_account.quickbooks_id
            })
        # else:
        #     raise UserError('Set COGS account in Company Configuration')

        if product_dict:
            # print(product_dict)
            return product_dict

    def export_product_cron(self):
        # print('\n\ncron calledddddddddddd\n\n')
        self.export_products()

    @api.onchange('qbd_product_type')
    def onchange_product_type(self):
        if self.qbd_product_type == 'ItemService':
            self.detailed_type = 'service'
        elif self.qbd_product_type == 'ItemInventory':
            self.detailed_type = 'product'
        else:
            self.detailed_type = 'consu'
