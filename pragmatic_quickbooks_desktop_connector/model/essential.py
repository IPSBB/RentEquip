from odoo import api, fields, models, _
import ast
import json
import requests
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError

class Salesperson(models.Model):
    _inherit = "res.users"

    quickbooks_id = fields.Char("Quickbook id ", copy=False)

    def create_import_salesperson(self, formatted_data):
        _logger.info("LENGTH OF SALESPERSON DATA===>>>>>>>>>>>>>>>>>{}".format(len(formatted_data)))

        for salesperson_data in formatted_data:
            user_obj = self.env['res.users']
            user_id = None

            _logger.info("SALESPERSON DATA====>>>>>>>>>>>>>>>>>>\n\n{}".format(salesperson_data))

            # Check if the record already exists based on quickbooks_id
            if 'quickbooks_id' in salesperson_data and salesperson_data.get('quickbooks_id'):
                user_id = user_obj.search([('quickbooks_id', '=', salesperson_data.get('quickbooks_id'))], limit=1)

            if not user_id:
                # Concatenate Initial and SalesRepEntityRefFullName for the name
                initial = salesperson_data.get('Initial', '')
                full_name = salesperson_data.get('SalesRepEntityRefFullName', '')
                name = f"{initial}. {full_name}".strip()  # Create the name format

                # Use email if available, otherwise fallback to name for login
                login = salesperson_data.get('email') or name

                # Check for an existing user with the same login
                existing_user = user_obj.search([('login', '=', login)], limit=1)
                if existing_user:
                    _logger.warning("User with login '{}' already exists. Generating a unique login.".format(login))
                    login = f"{login}_{salesperson_data.get('name') or 'new'}"

                # Prepare the values to create a new record
                vals = {
                    'quickbooks_id': salesperson_data.get('quickbooks_id'),
                    'name': name,
                    'login': login,  # Use email or name for login
                    # Add other fields if required
                }

                # Create the new salesperson (user)
                try:
                    new_user_id = user_obj.create(vals)
                    if new_user_id:
                        _logger.info("Created new salesperson: {}".format(new_user_id.name))
                        self.env.cr.commit()
                        _logger.info("Salesperson committed successfully!")
                except Exception as e:
                    _logger.error("Error creating salesperson: {}".format(e))
                    self.env.cr.rollback()  # Rollback on error to avoid partial commits

        return True

    # def create_import_salesperson(self, formatted_data):
    #     _logger.info("LENGTH OF SALESPERSON DATA===>>>>>>>>>>>>>>>>>{}".format(len(formatted_data)))

    #     for salesperson_data in formatted_data:
    #         user_obj = self.env['res.users']
    #         user_id = None

    #         _logger.info("SALESPERSON DATA====>>>>>>>>>>>>>>>>>>\n\n{}".format(salesperson_data))

    #         # Check if the record already exists based on quickbooks_id
    #         if 'quickbooks_id' in salesperson_data and salesperson_data.get('quickbooks_id'):
    #             user_id = user_obj.search([('quickbooks_id', '=', salesperson_data.get('quickbooks_id'))], limit=1)

    #         if not user_id:
    #             # Concatenate Initial and SalesRepEntityRefFullName for the name
    #             initial = salesperson_data.get('Initial', '')
    #             full_name = salesperson_data.get('SalesRepEntityRefFullName', '')
    #             name = f"{initial}. {full_name}".strip()  # Create the name format

    #             # Use email if available, otherwise fallback to name for login
    #             login = salesperson_data.get('email') or name

    #             # Prepare the values to create a new record
    #             vals = {
    #                 'quickbooks_id': salesperson_data.get('quickbooks_id'),
    #                 'name': name,
    #                 'login': login,  # Use email or name for login
    #                 # Add other fields if required
    #             }

    #             # Create the new salesperson (user)
    #             new_user_id = user_obj.create(vals)
    #             if new_user_id:
    #                 _logger.info("Created new salesperson: {}".format(new_user_id.name))
    #                 self.env.cr.commit()
    #                 _logger.info("Salesperson committed successfully!")

    #     return True

class Shipping_methos(models.Model):
    _inherit = "delivery.carrier"

    quickbooks_id = fields.Char(string="Quickbook id ", copy=False)

    def create_import_ship_via(self, formatted_data):
        _logger.info("LENGTH OF SHIP METHODS DATA===>>>>>>>>>>>>>>>>>{}".format(len(formatted_data)))

        for ship_method_data in formatted_data:
            carrier_obj = self.env['delivery.carrier']
            carrier_id = None

            _logger.info("SHIP METHOD DATA====>>>>>>>>>>>>>>>>>>\n\n{}".format(ship_method_data))

            # Check if the record already exists based on quickbooks_id
            if 'quickbooks_id' in ship_method_data and ship_method_data.get('quickbooks_id'):
                carrier_id = carrier_obj.search([('quickbooks_id', '=', ship_method_data.get('quickbooks_id'))],
                                                limit=1)

            if not carrier_id:
                # Prepare the values to create a new record
                default_product_id = self.env['product.product'].search([('name', '=', 'Shipping Method')],
                                                                        limit=1).id

                vals = {
                    'quickbooks_id': ship_method_data.get('quickbooks_id'),
                    'name': ship_method_data.get('name'),
                    'product_id':default_product_id
                    # Assuming the name of the ship method
                    # Add other fields if required
                }

                # Create the new ship method (carrier)
                new_carrier_id = carrier_obj.create(vals)
                if new_carrier_id:
                    _logger.info("Created new ship method: {}".format(new_carrier_id.name))
                    self.env.cr.commit()  # Commit the transaction
                    _logger.info("Ship method committed successfully!")

        return True


class ResPartner_Category_Inherit(models.Model):
    _inherit = "res.partner.category"

    quickbooks_id = fields.Char("Quickbook id ", copy=False)
    tag_type = fields.Selection([('customer', 'Customer'), ('vendor', 'Vendor')], string='Tag Type')

    ### Import Res Partner Categories
    def import_vendor_customer_category(self, partner_category_data, tag_type):
        # print('\n\nPartner Category data : ',partner_category_data)
        # print('\n\nTotal count : ',len(partner_category_data))
        #print("tag_type==============",tag_type)
        if partner_category_data:
            for record in partner_category_data:
                vals = {}
                if 'name' in record and record.get('name'):
                    vals.update({
                        'name': record.get('name'),
                        'quickbooks_id': record.get('quickbooks_id'),
                        'tag_type': tag_type
                    })
                    tags_id = self.search([('quickbooks_id', '=', record.get('quickbooks_id'))])
                    if not tags_id:
                        tags_id = self.search([('name','=',record.get('name'))], limit=1)
                    if not tags_id:
                        if vals:
                            self.create(vals)
                    else:
                        tags_id.write(vals)
        return True

class Parnter_Title(models.Model):
    _inherit = "res.partner.title"

    ### Import Partner Title
    def import_partner_title(self, partner_title_data):

        if partner_title_data:
            for record in partner_title_data:
                vals = {}
                if 'name' in record and record.get('name'):
                    partner_title_id = self.search([('name','=',record.get('name'))],limit=1)
                    if not partner_title_id:
                        vals.update({
                            'name': record.get('name'),
                        })
                        if vals:
                            self.create(vals)
        return True

class AccountPaymentTerms(models.Model):
    _inherit = "account.payment.term"

    quickbooks_id = fields.Char("Quickbook id ", copy=False)

    ### Import Payment Terms
    def import_payment_terms(self,payment_term_data):
        if payment_term_data:
            for record in payment_term_data:
                vals = {}
                if 'name' in record and record.get('name'):
                    payment_term_id = self.search([('name','=',record.get('name'))],limit=1)

                    if not payment_term_id:
                        vals.update({
                            'name': record.get('name'),
                            'quickbooks_id': record.get('quickbooks_id')
                        })
                        if vals:
                            self.create(vals)
                    else:
                        vals.update({
                            'quickbooks_id': record.get('quickbooks_id')
                        })
                        payment_term_id.write(vals)
        return True

    # @api.multi
    # def export_payment_terms(self):
    #     print('Export QBD Payment Terms hereeeeeeeeeeeeeeeeeeeeee')
    #     payment_term_data = []
    #     qbd_payment_terms = self.search([('quickbooks_id','=',None)])
    #
    #     if qbd_payment_terms:
    #         for record in qbd_payment_terms:
    #             payment_term_dict= {}
    #             payment_term_dict.update({
    #                 'odoo_id':record.id,
    #                 'name':record.name
    #             })
    #
    #             if payment_term_dict:
    #                 payment_term_data.append(payment_term_dict)
    #
    #     if payment_term_data:
    #         print('\nPayment Term data : ',payment_term_data)
    #         print('Total Count ',len(payment_term_data))
    #         company = self.env['res.users'].search([('id', '=', 2)]).company_id
    #         headers = {'content-type': "application/json"}
    #         data = payment_term_data
    #
    #         data = {'payment_term_list': data}
    #
    #         response = requests.request('POST', company.url + '/export_payment_terms', data=json.dumps(data),
    #                                     headers=headers,
    #                                     verify=False)
    #
    #         print("Response Text ", type(response.text), response.text)
    #
    #         resp = ast.literal_eval(response.text)
    #
    #         print('\n\nResp: ', resp,'\n\n')
    #
    #         for res in resp[0].get('Data'):
    #
    #             if 'odoo_id' in res and res.get('odoo_id'):
    #                 payment_term_id = self.browse(int(res.get('odoo_id')))
    #
    #                 if payment_term_id:
    #                     payment_term_id.write({'quickbooks_id': res.get('quickbooks_id')})
    #
    #     return True

class AccountTaxes(models.Model):
    _inherit = "account.tax"

    quickbooks_id = fields.Char("Quickbook id", copy=False)
    qbd_tax_code = fields.Many2one('qbd.tax.code')
    desc = fields.Char("Description")

    ### Import Sales Tax
    def import_sales_tax(self,item_tax_data, company_id):
        # print('\n\nItem Tax data : ',item_tax_data)
        # print('\n\nTotal count : ',len(item_tax_data))
        # print("COMPANY ID",company_id, company_id.country_id.id)
        _logger.info("SALE TAX DATA===>>>>>>>>>>>>>>>>>>>>>>{}".format(item_tax_data))
        if not company_id.country_id.id:
            raise UserError("Set the Country in Company Form")
        if item_tax_data:
            for record in item_tax_data:
                vals = {}
                # tax_group_id = self.env.ref('pragmatic_quickbooks_desktop_connector.tax_group_1').id
                if 'name' in record and record.get('name'):
                    # print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh")
                    ##check first if quickbook id is existed in tax master if availble then update that record
                    vals.update({
                        'name': record.get('name'),
                        'desc': record.get('desc'),
                        'amount': record.get('amount'),
                        'quickbooks_id': record.get('quickbooks_id'),
                        # 'tax_group_id' :tax_group_id,
                    })
                    tax_id = self.search([('quickbooks_id', '=', record.get('quickbooks_id'))])
                    if not tax_id:
                        tax_id = self.search(['&', ('name', '=', record.get('name')), ('amount','=',record.get('amount'))], limit=1)
                    if not tax_id:
                        self.create(vals)
                    else:
                        tax_id.write(vals)

        return True

class QBDTaxCode(models.Model):
    _name = "qbd.tax.code"
    _description = "QBD Tax Code"

    name = fields.Char('Name')
    is_taxable = fields.Boolean('Is Taxable',)
    quickbooks_id = fields.Char("Quickbook id", copy=False)

    ### Import Tax Code
    def import_tax_code(self,item_tax_code_data):
        # print('\n\nItem Tax Code : ',item_tax_code_data)
        # print('\n\nTotal count : ',len(item_tax_code_data))
        if item_tax_code_data:
            for record in item_tax_code_data:
                vals = {}

                if 'name' in record and record.get('name'):
                    tax_code_id = self.search([('name','=',record.get('name'))],limit=1)


                    if not tax_code_id:
                        vals.update({
                            'name': record.get('name'),
                            'is_taxable': record.get('taxable'),
                            'quickbooks_id': record.get('quickbooks_id'),
                        })

                        if vals:
                            self.create(vals)

                    else:
                        # print ("In Write -------------------------------------------- Tax Code")
                        vals.update({
                            'quickbooks_id': record.get('quickbooks_id'),
                        })
                        tax_code_id.write(vals)
        return True