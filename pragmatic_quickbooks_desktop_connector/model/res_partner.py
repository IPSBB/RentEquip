# from sqlalchemy import false
from odoo import api, fields, models, _
import requests
import ast
import json
import logging
import re
from odoo import modules
from odoo.exceptions import UserError, ValidationError
from dateutil.parser import *

from odoo.tools.misc import file_path
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    quickbooks_id = fields.Char("Quickbook id ", copy=False)
    is_updated = fields.Boolean('Is Updated')
    qbd_date_created = fields.Date()
    fq_primary_key = fields.Char("FQ Primary Key", copy=False)

#     @api.model
#     def default_get(self, fields):
#
#         vals = super(ResPartner, self).default_get(fields)
#         if 'res_partner_search_mode' in self._context and self._context['res_partner_search_mode'] == 'customer':
#             category_ids = self.env['res.partner.category'].search([('tag_type', '=', 'customer')])
#             if category_ids:
#                 vals['category_id'] = [(6, 0, category_ids.ids)]
#         if 'res_partner_search_mode' in self._context and self._context['res_partner_search_mode'] == 'supplier' :
#             category_ids = self.env['res.partner.category'].search([('tag_type', '=', 'customer')])
#             print("\n\ncategory_ids==============",category_ids)
#             if category_ids:
#                 vals['category_id'] = [(6, 0, category_ids.ids)]
#
#         return vals

    def export_partner_to_qbd(self):
        for rec in self:
            if rec.customer_rank == 1:
                rec.export_partners(partner_id=rec)
            elif rec.supplier_rank == 1:
                rec.export_vendors(vendor_id=rec)

    @api.onchange('category_id')
    def item_delivered_ids_onchange(self):
        cat_list = []
        if 'res_partner_search_mode' in self._context and self._context['res_partner_search_mode'] == 'customer':
            category_ids = self.env['res.partner.category'].search(
                [('tag_type', '=', 'customer')])
            if category_ids:
                for category_id in category_ids:
                    cat_list.append(category_id.id)

        if 'res_partner_search_mode' in self._context and self._context['res_partner_search_mode'] == 'supplier':
            category_ids = self.env['res.partner.category'].search(
                [('tag_type', '=', 'vendor')])
            if category_ids:
                for category_id in category_ids:
                    cat_list.append(category_id.id)

        return {'domain': {'category_id': [('id', 'in', cat_list)]}}

    @api.model
    def create(self, vals):
        _logger.info("VALS==>>>>>>>>>>>{}".format(vals))
        try:
            if vals.get('vat'):
                if vals['vat']:
                    if 'customer_rank' in vals and vals['customer_rank']:
                        if len(vals['vat']) > 15:
                            raise UserError(
                                "Tax ID should be not more than 15 characters for Customers.")
                    elif 'supplier_rank' in vals and vals['supplier_rank']:
                        data = vals['vat']
                        match = re.search(
                            "^[0-9]{3}-[0-9]{2}-[0-9]{4}$|^[0-9]{2}-[0-9]{7}$", data)
                        if not match:
                            raise UserError(
                                "Tax ID should be exactly of 10 characters in form of 12-3456789 or 123-45-6789 for Vendors, and only Integer format is supported in Quickbooks.")

            partner_id = super(ResPartner, self).create(vals)
            return partner_id

        except Exception as e:
            _logger.info("Exception==>>>>>>>>>>>>>>{}".format(e))
            pass

    def write(self_vals, vals):
        for self in self_vals:
            if 'vat' in vals:
                if vals['vat']:
                    if 'customer_rank' not in vals and 'supplier_rank' not in vals:
                        if self.customer_rank:
                            if len(vals['vat']) > 15:
                                raise UserError(
                                    "Tax ID should be not more than 15 characters for Customers.")

                        elif self.supplier_rank:
                            data = vals['vat']
                            match = re.search(
                                "^[0-9]{3}-[0-9]{2}-[0-9]{4}$|^[0-9]{2}-[0-9]{4}$", data)
                            if not match:
                                raise UserError(
                                    "Tax ID should be exactly of 10 characters in form of 12-3456789 or 123-45-6789 for Vendors, and only Integer format is supported in Quickbooks.")

                    if 'customer_rank' in vals and 'supplier_rank' in vals:
                        if vals['customer_rank']:
                            if len(vals['vat']) > 15:
                                raise UserError(
                                    "Tax ID should be not more than 15 characters for Customers.")

                        if vals['supplier_rank']:
                            if len(vals['vat']) > 15:
                                data = vals['vat']
                                match = re.search(
                                    "^[0-9]{3}-[0-9]{2}-[0-9]{4}$|^[0-9]{2}-[0-9]{4}$", data)
                                if not match:
                                    raise UserError(
                                        "Tax ID should be exactly of 10 characters in form of 12-3456789 or 123-45-6789 for Vendors, and only Integer format is supported in Quickbooks.")

            if 'is_updated' not in vals and 'quickbooks_id' not in vals and 'is_company' not in vals:
                # print("\n\nin write of partner", self._context.get('dont_update_is_update'), vals)
                vals['is_updated'] = True

            return super(ResPartner, self).write(vals)
    
    def read_data_file(self):
        module_path = modules.get_module_path('pragmatic_quickbooks_desktop_connector')
        file_path = module_path + '/data/data.txt'
        file1=open(file_path,'r')
        data = file1.read()
        _logger.info("DATA===>>>>>>>>>>>>>>{}".format(data))
        if data:
            partners = json.loads(data)
        else:
            raise UserError("No Data In File")
        _logger.info("PARTNERS====>>>>>>>>>>>>{}".format(partners))

        self.create_customers(partners)

    def get_shipping_address(self, quickbook_id):
        # print("quickbook_id", quickbook_id)
        headers = {'content-type': "application/json"}
        params = {'to_execute_account': 5,
                  'fetch_record': 'all',
                  'list_id': quickbook_id}
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        try:
            response = requests.request('GET', company.url + '/import_customer_shipto', params=params, headers=headers,
                                        verify=False)
        except Exception as e:
            raise UserError(e)

        if response.status_code == 200:
            formatted_data = json.loads(response.text)
            shipto_list = []
            for ptr_record in formatted_data:
                existed_partner = self.search([('fq_primary_key', '=', ptr_record.get('fq_primary_key')),('quickbooks_id', '=', ptr_record.get('quickbooks_id'))])
                if not existed_partner:
                    vals = {}
                    vals.update({'name': ptr_record.get('shipto_name'), 'quickbooks_id': ptr_record.get('quickbooks_id'),
                                 'fq_primary_key': ptr_record.get('fq_primary_key'),
                                 'customer_rank': 1,'city':ptr_record.get('shipto_city'),
                                 'street':ptr_record.get('shipto_addr1'),'zip':ptr_record.get('shipto_zip'),
                                 'street2':ptr_record.get('shipto_addr2'),'type':'delivery'})
                    if ptr_record.get('shipto_state'):
                        state = self.env['res.country.state'].search(['|', ('code', '=', ptr_record.get('shipto_state')),('name', '=', ptr_record.get('shipto_state'))], limit=1)
                        if state:
                            vals.update({'state_id': state.id})
                    if ptr_record.get('shipto_country'):
                        country = self.env['res.country'].search(['|', ('code', '=', ptr_record.get('shipto_country')), ('name', '=', ptr_record.get('shipto_country'))], limit=1)
                        if country:
                            vals.update({'country_id': country.id})

                    shipto_list.append(vals)
                    _logger.info("Shipping Address .....")
            return shipto_list

    def create_customers(self, partners, list_id=None):
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        _logger.info("PARTNERS====>>>{}".format(type(partners)))
        new_partner_id = False
        # IF all Customer Imported
        if len(partners) == 0:
            raise UserError(
                "It seems that all of the Customers are already imported.")
        for partner in partners:
            _logger.info("\n\n\n\n\nPartner===>>>>>>>>>>>>>{}".format(partner))
            vals = {}
            # _logger.info("PARTNER===>>>>>>>>>>>>>{}".format(partner))
            if 'quickbooks_id' in partner and partner.get('quickbooks_id'):
                partner_id = self.search(
                    [('quickbooks_id', '=', partner.get('quickbooks_id'))], limit=1)
                if not partner_id:
                    _logger.info("Create Customer")
                    # print('Parnter dict in if : ',partner)
                    # create new partners
                    if 'parent_qbd_id' in partner and partner.get('parent_qbd_id'):
                        parent_id = self.search([('quickbooks_id', '=', partner.get('parent_qbd_id'))], limit=1)
                        if parent_id:
                            vals = self._prepare_partner_dict(
                                partner, parent_id)
                        else:
                            parent_id = self.create_parent_data(
                                partner.get('parent_qbd_id'))
                            if parent_id:
                                vals = self._prepare_partner_dict(
                                    partner, parent_id=parent_id)

                        if vals:
                            if company:
                                if company.qb_account_recievable and company.qb_account_payable:
                                    vals.update({'property_account_receivable_id': company.qb_account_recievable.id})
                                    vals.update({'property_account_payable_id': company.qb_account_payable.id})
                                else:
                                    _logger.info("Account Payable or Receivable is not set!")
                                    raise ValidationError(_("""It seems that Account Payable or Account Receivable is not set.
                                                                            Please navigate to Settings ---> Companies --->Quickbooks Tab.
                                                                            Under QB Account Configuration,please set Account Receivable and Account Payable.
                                                                             """))
                            _logger.info("CREATE VALS===>>>>>>>>>>{}".format(vals))
                            new_partner_id = self.create(vals)
                            if new_partner_id:
                                if new_partner_id.state_id:
                                    new_partner_id._onchange_state()
                                if new_partner_id.country_id:
                                    new_partner_id._onchange_country_id()
                                self.env.cr.commit()
                                # print('New Partner Commited :: ',new_partner_id.name)
                                date_parsed = parse(
                                    partner.get("last_time_modified"))
                                company.write({
                                    'last_imported_qbd_id_for_partners': date_parsed
                                })

                    else:
                        vals = self._prepare_partner_dict(partner)
                        if vals.get('quickbooks_id'):
                            ##get shipping address..
                            shipping_address = self.get_shipping_address(vals.get('quickbooks_id'))
                            if shipping_address:
                                vals.update({'child_ids': [(0, 0, x) for x in shipping_address]})
                        if vals:
                            _logger.info("CREATE VALS===>>>>>>>>>>{}".format(vals))
                            new_partner_id = self.create(vals)

                            if new_partner_id:
                                if new_partner_id.state_id:
                                    new_partner_id._onchange_state()
                                if new_partner_id.country_id:
                                    new_partner_id._onchange_country_id()
                                self.env.cr.commit()

                                # print('New Partner Commited :: ', new_partner_id.name)
                                date_parsed = parse(
                                    partner.get("last_time_modified"))
                                company.write({
                                    'last_imported_qbd_id_for_partners': date_parsed
                                })
                else:
                    # print('Parnter dict in else : ',partner)
                    # update existing partner record
                    _logger.info("Update Customer")
                    if partner_id.parent_id:
                        vals = self._prepare_partner_dict(
                            partner, partner_id.parent_id)
                    else:
                        vals = self._prepare_partner_dict(partner)
                        shipping_address = self.get_shipping_address(partner_id.quickbooks_id)
                        if shipping_address:
                            ##create shipping address and to child ids
                            for addr in shipping_address:
                                addr.update({'parent_id': partner_id.id})
                                self.env['res.partner'].create(addr)
                    _logger.info("WRITE VALS===>>>>>>>>>>.{}".format(vals))
                    partner_id.write(vals)
                    if partner_id.state_id:
                        partner_id._onchange_state()
                    if partner_id.country_id:
                        partner_id._onchange_country_id()
                    date_parsed = parse(partner.get("last_time_modified"))
                    company.write({
                        'last_imported_qbd_id_for_partners': date_parsed
                    })
            
        if list_id:
            # _logger.info("New Partner ID===>>>>>>>>>>>>>>>>>>{}".format(new_partner_id))
            return new_partner_id
        else:
            return True

    def create_parent_data(self, quickbook_id=False):
        parent_id = None
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        if quickbook_id:
            headers = {'content-type': "application/json"}
            params = {'fetch_record': 'one',
                      'list_id': quickbook_id, 'to_execute_account': 4}
            _logger.info("PARAMS====>>>>>>>>>>>>>>>>>{}".format(params))
            response = requests.request('GET', company.url + '/import_customer', params=params, headers=headers,
                                        verify=False)
            formatted_data = json.loads(response.text)
            _logger.info("FORMATTED DATA====>>>>>{}".format(formatted_data))
            for record in formatted_data:
                data = record

            if data:
                _logger.info("6666666")
                _logger.info("FORMATTED DATA====>>>>>{}".format(data))
                vals = self._prepare_partner_dict(data)
                if vals:
                    parent_id = self.create(vals)

        if parent_id:
            return parent_id

    def _prepare_partner_dict(self, partner, parent_id=False):
        vals = {}
        state = None
        country = None

        # 0 ListId (36 varchar) quickbooks_id  --Done
        # 1 ParentRefListID (36 varchar) parent_qbd_id --Done
        # 2 Name (41 varchar) name --Done
        # 3 Salutation (15 varchar) title
        # 4 JobTitle (41 varchar) function --Done
        # 5 Phone (21 varchar) phone --Done
        # 6 AltPhone (21 varchar) mobile --Done
        # 7 Email (1023 varchar) email --Done
        # 8 Notes (4095 varchar) comment --Done
        # 9 BillAddressCity (31 varchar) city --Done
        # 10 BillAddressPostalCode (13 varchar) zip --Done
        # 11 BillAddressState (21 varchar) state_id --Done
        # 12 BillAddressCountry (31 varchar) country_id --Done
        # 13 BillAddressAddr1 (41 varchar) street --Done
        # 14 BillAddressAddr2 (41 varchar)street2 --Done
        # 15 TermsRefListId (36 varchar) terms_qbd_id
        # 16 TimeModified  last_time_modified
        # 17 ResaleNumber vat
        # 18 AccountNumber ref
        # 19 CustomerTypeRefFullName category_name
        # 20 TimeCreated time_created
        # 21 SalesRepFullName

        if parent_id:
            vals.update({
                'parent_id': parent_id.id,
                'company_type': 'person',
            })
        else:
            vals.update({'company_type': 'company'})

        vals.update({
            'customer_rank': 1,
            'quickbooks_id': partner.get('quickbooks_id') if partner.get('quickbooks_id') else '',
            'name': partner.get('name') if partner.get('name') else '',
            'function': partner.get('function') if partner.get('function') else '',
            'phone': partner.get('phone') if partner.get('phone') else '',
            'mobile': partner.get('mobile') if partner.get('mobile') else '',
            'email': partner.get('email') if partner.get('email') else '',
            'comment': partner.get('comment') if partner.get('comment') else '',
            'city': partner.get('city') if partner.get('city') else '',
            'zip': partner.get('zip') if partner.get('zip') else '',
            'street': partner.get('street') if partner.get('street') else '',
            'street2': partner.get('street2') if partner.get('street2') else '',
            'vat': partner.get('vat') if partner.get('vat') else '',
            'ref': partner.get('ref') if partner.get('ref') else '',
            'qbd_date_created': partner.get('time_created') if partner.get('time_created') else False,
        })
        if 'category_name' in partner and partner.get('category_name'):
            category_name = partner.get('category_name')
            if category_name:
                category_id = self.env['res.partner.category'].search(
                    [('name', '=', category_name)], limit=1)
                if category_id:
                    vals.update({'category_id': [(6, 0, [category_id.id])]})

        if 'title' in partner and partner.get('title'):
            title = partner.get('title')
            if title:
                title_id = self.env['res.partner.title'].search(
                    [('name', '=', title)], limit=1)
                if title_id:
                    vals.update({'title': title_id.id})

        if 'terms_qbd_id' in partner and partner.get('terms_qbd_id'):
            terms_qbd_id = partner.get('terms_qbd_id')
            if terms_qbd_id:
                terms_id = self.env['account.payment.term'].search(
                    [('quickbooks_id', '=', terms_qbd_id)], limit=1)
                if terms_id:
                    vals.update({'property_payment_term_id': terms_id.id})

            # Handle country
        country_id = False
        if country := partner.get('country'):
            country_id = self.env['res.country'].search(['|', ('name', '=ilike', country), ('code', '=ilike', country)],
                                                        limit=1)
            if country_id:
                vals.update({'country_id': country_id.id})

        # Handle state
        if state := partner.get('state'):
            state_domain = ['|', ('name', '=ilike', state), ('code', '=ilike', state)]
            if country_id:
                state_domain.append(('country_id', '=', country_id.id))

            state_id = self.env['res.country.state'].search(state_domain, limit=1)

            if state_id:
                vals.update({'state_id': state_id.id})
            # If state is not found, we'll just keep the country (if it was found)

        ##if country id is availble then check the state into countries findout the state and assign
        # if country and state:
        #     print(999999999999999999999999999)
        #     country_id = self.env['res.country'].search(
        #         ['|', ('name', '=', country), ('code', '=', country)], limit=1)
        #     state_id = self.env['res.country.state'].search(
        #         ['|', ('name', '=', state), ('code', '=', state)], limit=1)
        #     if country_id and state_id:
        #         print(country_id.mapped('state_ids'),'ppppppppppppppppppppppppppppppppp')
        #         if state_id.id in country_id.mapped('state_ids').ids:
        #             print('=====================13131313')
        #             vals.update({'state_id':state_id.id, 'country_id':country_id.id})
        # elif not state and country:
        #     country_id = self.env['res.country'].search(
        #         ['|', ('name', '=', country), ('code', '=', country)], limit=1)
        #     if country_id:
        #         vals.update({'country_id': country_id.id, 'state_id':False})
        # elif not country and state:
        #     state_id = self.env['res.country.state'].search(
        #         ['|', ('name', '=', state), ('code', '=', state)], limit=1)
        #     vals.update({'state_id': state_id.id, 'country_id':False})

        #
        #
        #
        #
        # if state and country:
        #     country_id = self.env['res.country'].search(
        #         ['|', ('name', '=', country), ('code', '=', country)], limit=1)
        #     if country_id:
        #         vals.update({'country_id': country_id.id})
        #         state_id = self.env['res.country.state'].search(
        #             ['|', ('name', '=', state), ('code', '=', state)], limit=1)
        #         if state_id:
        #             if state_id.country_id.id == country_id.id:
        #                 vals.update({'state_id': state_id.id})
        #         else:
        #             state_id = self.env['res.country.state'].create(
        #                 {'name': state, 'code': state, 'country_id': country_id.id})
        #             vals.update({'state_id': state_id.id})
        #     else:
        #         country_id = self.env['res.country'].create({'name': country})
        #         vals.update({'country_id': country_id.id})
        #         state_id = self.env['res.country.state'].create(
        #             {'name': state, 'code': state, 'country_id': country_id.id})
        #         vals.update({'state_id': state_id.id})
        #
        # if not state and country:
        #     country_id = self.env['res.country'].search(
        #         ['|', ('name', '=', country), ('code', '=', country)], limit=1)
        #     if country_id:
        #         vals.update({'country_id': country_id.id})

        if 'user_name' in partner and partner.get('user_name'):
            user_name = partner.get('user_name')
            if user_name:
                user_id = self.env['res.users'].search(
                    [('name', '=', user_name)], limit=1)
                if user_id:
                    vals.update({'user_id': user_id.id})

        if vals:
            return vals

    def create_vendors(self, vendors, list_id=None):
        # print('\nVendors count : ',len(vendors))
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        # IF all Vendors Imported
        if len(vendors) == 0:
            raise UserError(
                "It seems that all of the Vendors are already imported.")
        for vendor in vendors:
            vals = {}
            if 'quickbooks_id' in vendor and vendor.get('quickbooks_id'):
                vendor_id = self.search([('quickbooks_id', '=', vendor.get(
                    'quickbooks_id')), ('customer_rank', '=', 0)], limit=1)

                if not vendor_id:
                    _logger.info("Create Vendor")
                    # print('\n\nVendor dict in ifffffff : ',vendor,'\n')
                    # create new vendor
                    vals = self._prepare_vendor_dict(vendor)
                    if vals:
                        if company:
                            if company.qb_account_recievable and company.qb_account_payable:
                                vals.update({'property_account_receivable_id': company.qb_account_recievable.id})
                                vals.update({'property_account_payable_id': company.qb_account_payable.id})
                            else:
                                _logger.info("Account Payable or Receivable is not set!")
                                raise ValidationError(_("""It seems that Account Payable or Account Receivable is not set.
                                                                        Please navigate to Settings ---> Companies --->Quickbooks Tab.
                                                                        Under QB Account Configuration,please set Account Receivable and Account Payable.
                                                                         """))
                        if 'display_name' in vals and vals.get('display_name'):
                            vals.update({'qbd_number': vals.get('display_name')})
                        new_vendor_id = self.create(vals)

                        if new_vendor_id:
                            if new_vendor_id.state_id:
                                new_vendor_id._onchange_state()
                            if new_vendor_id.country_id:
                                new_vendor_id._onchange_country_id()

                            self.env.cr.commit()
                            date_parsed = parse(
                                vendor.get("last_time_modified"))
                            company.write({
                                'last_imported_qbd_id_for_vendors': date_parsed
                            })

                else:
                    _logger.info("Update Vendor")
                    # print('\n\nVendor dict in elseeeee : ',vendor,'\n\n')
                    # update existing vendor record
                    vals = self._prepare_vendor_dict(vendor)
                    vendor_id.write(vals)
                    if vendor_id.state_id:
                        vendor_id._onchange_state()
                    if vendor_id.country_id:
                        vendor_id._onchange_country_id()

                    date_parsed = parse(
                                vendor.get("last_time_modified"))
                    company.write({
                        'last_imported_qbd_id_for_vendors': date_parsed
                    })

        if list_id:
            _logger.info("New Partner ID===>>>>>>>>>>>>>>>>>>{}".format(new_vendor_id))
            return new_vendor_id
        else:
            return True

    def _prepare_vendor_dict(self, vendor):
        vals = {}
        state = None
        country = None

        # 0 ListId (36 varchar) quickbooks_id --DONE
        # 1 Name (41 varchar) name --DONE
        # 2 Salutation (15 varchar) title --DONE
        # 3 Phone (21 varchar) phone --DONE
        # 4 AltPhone (21 varchar) mobile --DONE
        # 5 Email (1023 varchar) email --DONE
        # 6 Notes (4095 varchar) comment --DONE
        # 7 VendorAddressCity (31 varchar) city --DONE
        # 8 VendorAddressPostalCode (13 varchar) zip --DONE
        # 9 VendorAddressState (21 varchar) state_id --DONE
        # 10 VendorAddressCountry (31 varchar) country_id --DONE
        # 11 VendorAddressAddr1 (41 varchar) street --DONE
        # 12 VendorAddressAddr2 (41 varchar)street2 --DONE
        # 13 TermsRefListId (36 varchar) terms_qbd_id --DONE
        # 14 TimeModified  last_time_modified --DONE
        # 15 ResaleNumber vat
        # 16 AccountNumber ref
        # 17 VendorTypeRefFullName category_name

        vals.update({
            'company_type': 'person',
            'supplier_rank': 1,
            'customer_rank': 0,
            'quickbooks_id': vendor.get('quickbooks_id') if vendor.get('quickbooks_id') else '',
            'name': vendor.get('name') if vendor.get('name') else '',
            'phone': vendor.get('phone') if vendor.get('phone') else '',
            'mobile': vendor.get('mobile') if vendor.get('mobile') else '',
            'email': vendor.get('email') if vendor.get('email') else '',
            'comment': vendor.get('comment') if vendor.get('comment') else '',
            'city': vendor.get('city') if vendor.get('city') else '',
            'zip': vendor.get('zip') if vendor.get('zip') else '',
            'street': vendor.get('street') if vendor.get('street') else '',
            'street2': vendor.get('street2') if vendor.get('street2') else '',
            'vat': vendor.get('vat') if vendor.get('vat') else '',
            'ref': vendor.get('ref') if vendor.get('ref') else '',
        })
        if 'category_name' in vendor and vendor.get('category_name'):
            category_name = vendor.get('category_name')
            if category_name:
                category_id = self.env['res.partner.category'].search(
                    [('name', '=', category_name)], limit=1)
                if category_id:
                    vals.update({'category_id': [(6, 0, [category_id.id])]})

        if 'title' in vendor and vendor.get('title'):
            title = vendor.get('title')
            if title:
                title_id = self.env['res.partner.title'].search(
                    [('name', '=', title)], limit=1)
                if title_id:
                    vals.update({'title': title_id.id})

        if 'state' in vendor and vendor.get('state'):
            state = vendor.get('state')
        if 'country' in vendor and vendor.get('country'):
            country = vendor.get('country')

        if 'terms_qbd_id' in vendor and vendor.get('terms_qbd_id'):
            terms_qbd_id = vendor.get('terms_qbd_id')
            if terms_qbd_id:
                terms_id = self.env['account.payment.term'].search(
                    [('quickbooks_id', '=', terms_qbd_id)], limit=1)
                if terms_id:
                    vals.update(
                        {'property_supplier_payment_term_id': terms_id.id})
        if 'state' in vendor and vendor.get('state'):
            state = vendor.get('state')
            state_id = self.env['res.country.state'].search(
                ['|', ('name', '=', state), ('code', '=', state)], limit=1)
            if state_id:
                vals.update({'state_id': state_id.id})
        if 'country' in vendor and vendor.get('country'):
            if not vendor.get('state'):
                country = vendor.get('country')
                country_id = self.env['res.country'].search(
                    ['|', ('name', '=', country), ('code', '=', country)], limit=1)
                vals.update({'country_id': country_id.id, 'state_id':False})

        # if state and country:
        #     country_id = self.env['res.country'].search(
        #         ['|', ('name', '=', country), ('code', '=', country)], limit=1)
        #     if country_id:
        #         vals.update({'country_id': country_id.id})
        #         state_id = self.env['res.country.state'].search(['|', ('name', '=', state), ('code', '=', state)],
        #                                                         limit=1)
        #         if state_id:
        #             if state_id.country_id.id == country_id.id:
        #                 vals.update({'state_id': state_id.id})
        #         else:
        #             state_id = self.env['res.country.state'].create(
        #                 {'name': state, 'code': state, 'country_id': country_id.id})
        #             vals.update({'state_id': state_id.id})
        #     else:
        #         country_id = self.env['res.country'].create({'name': country})
        #         vals.update({'country_id': country_id.id})
        #         state_id = self.env['res.country.state'].create(
        #             {'name': state, 'code': state, 'country_id': country_id.id})
        #         vals.update({'state_id': state_id.id})
        #
        # if not state and country:
        #     country_id = self.env['res.country'].search(
        #         ['|', ('name', '=', country), ('code', '=', country)], limit=1)
        #     if country_id:
        #         vals.update({'country_id': country_id.id})

        return vals

    def export_partner_data(self, partner, is_parent_id=False):
        loger_dict = {}
        partner_data_list = []
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        if company.export_updated_record == False:
            if not partner:
                return False
            if is_parent_id:
                partner_dict = self.get_partner_dict(
                    partner, is_send_parent_ref=True)
            else:
                partner_dict = self.get_partner_dict(partner)
        else:
            if not partner:
                return False
            if is_parent_id:
                partner_dict = self.get_partner_dict(
                    partner, company.export_updated_record, is_send_parent_ref=True)
            else:
                partner_dict = self.get_partner_dict(partner, company.export_updated_record)

        if partner_dict:
            try:
                company = self.env['res.users'].search(
                    [('id', '=', self._uid)]).company_id
                headers = {'content-type': "application/json"}
                data = [partner_dict]

                data = {'customers_list': data}

                response = requests.request('POST', company.url + '/export_customers', data=json.dumps(data),
                                            headers=headers,
                                            verify=False)
            except Exception as ex:
                _logger.error(str(ex))
                raise UserError(str(ex))

            # print("Response Text", type(response.text), response.text)

            try:
                resp = ast.literal_eval(response.text)
                # print('Resp : ',resp)
                if isinstance(resp, dict):
                    for res in resp.get('Data'):
                        if res.get('Message'):
                            raise UserError(_('No Partner Exported'))
                        if 'odoo_id' in res and res.get('odoo_id'):
                            partner_id = self.browse(int(res.get('odoo_id')))

                            if partner_id:
                                if res.get('quickbooks_id'):
                                    partner_id.write(
                                        {'is_updated': False,'quickbooks_id': res.get('quickbooks_id')})
                        loger_dict.update({'operation': 'Export Partner',
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

    # Export Partners

    def export_partners(self, partner_id=None):
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        limit = 0
        if company.export_cus_limit:
            limit = int(company.export_cus_limit)
        if company.export_updated_record == False:
            if partner_id:
                partners = partner_id
            else:
                partners = self.search(
                    [('quickbooks_id', '=', False), ], limit=limit)
            chl_ptr_lst = []
            for partner in partners:
                ##if partner company and admin then not export just continue the loop.
                if partner.id == 3 or partner.id == 1:
                    _logger.info('Admin/Company Partner Not Exported')
                    continue
                if partner.company_type == 'company':
                    if not partner.quickbooks_id:
                        export_id = partner.export_partner_data(partner, is_parent_id=False)
                    for child_ptr in partner.child_ids:
                        if not child_ptr.quickbooks_id:
                            child_export_id = child_ptr.export_partner_data(child_ptr, is_parent_id=True)
                            chl_ptr_lst.append(child_ptr.id)
                else:
                    if partner.company_type == 'person' and partner.id not in chl_ptr_lst:
                        if partner.parent_id and not partner.parent_id.quickbooks_id:
                            partner_dict = self.export_partner_data(partner.parent_id, is_parent_id=False)
                        if not partner.quickbooks_id:
                            partner_dict = self.export_partner_data(partner, is_parent_id=True)
        else:
            # print('Export Updated Record')
            if partner_id:
                partners = partner_id
            else:
                partners = self.search([('quickbooks_id', '!=', False),('is_updated', '=', True)], limit=limit)
            chl_ptr_lst = []
            for partner in partners:
                ##if partner company and admin then not export just continue the loop.
                if partner.id == 3 or partner.id == 1:
                    _logger.info('Admin/Company Partner Not Exported')
                    continue

                if partner.company_type == 'company':
                    export_id = partner.export_partner_data(partner, is_parent_id=False)
                    for child_ptr in partner.child_ids:
                        if not child_ptr.quickbooks_id:
                            child_export_id = child_ptr.export_partner_data(child_ptr, is_parent_id=True)
                            chl_ptr_lst.append(child_ptr.id)
                        else:
                            child_export_id = child_ptr.export_partner_data(child_ptr, is_parent_id=True)
                            chl_ptr_lst.append(child_ptr.id)
                else:
                    if partner.company_type == 'person' and partner.id not in chl_ptr_lst:
                        if partner.parent_id and not partner.parent_id.quickbooks_id:
                            partner_dict = self.export_partner_data(partner.parent_id, is_parent_id=False)
                        if partner.quickbooks_id:
                            partner_dict = self.export_partner_data(partner, is_parent_id=True)


        return True
                            #     if partner_dict:
                            #         partner_data_list.append(partner_dict)
                            # partner_dict = self.get_partner_dict(partner)
                            # if partner_dict:
                            #     partner_data_list.append(partner_dict)

            # if partner_data_list:
            #     # print('\n\nPartner data List for Company : ',partner_data_list,'\n\n')
            #     # print('Total Count : ', len(partner_data_list))
            #     company = self.env['res.users'].search(
            #         [('id', '=', 2)]).company_id
            #     headers = {'content-type': "application/json"}
            #     data = partner_data_list
            #
            #     data = {'customers_list': data}
            #
            #     response = requests.request('POST', company.url + '/export_customers', data=json.dumps(data),
            #                                 headers=headers,
            #                                 verify=False)
            #
            #     # print("Response Text", type(response.text), response.text)
            #
            #     try:
            #         resp = ast.literal_eval(response.text)
            #
            #         # print('Resp : ',resp)
            #         if isinstance(resp,dict):
            #             for res in resp.get('Data'):
            #                 if res.get('Message'):
            #                     raise UserError(_('No Partner Exported'))
            #                 if 'odoo_id' in res and res.get('odoo_id'):
            #                     partner_id = self.browse(int(res.get('odoo_id')))
            #
            #                     if partner_id:
            #                         if res.get('quickbooks_id'):
            #                             partner_id.write(
            #                                 {'quickbooks_id': res.get('quickbooks_id')})
            #                 loger_dict.update({'operation': 'Export Partner',
            #                                 'odoo_id': res.get('odoo_id'),
            #                                 'qbd_id': res.get('quickbooks_id'),
            #                                 'message': res.get('messgae')
            #                                 })
            #                 qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
            #                 # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})
            #         else:
            #             raise UserError(_("No Data in Response Check Quickbook Desktop Terminal"))
            #     except Exception as ex:
            #         _logger.error(str(ex))
            #         raise UserError(str(ex))
            # print (" --------------------------------------------------- ")
            # print (len(partners))
            # print (limit)
            # print (len(partners) < limit)

        #     if len(partners) < limit:
        #         limit = limit - len(partners)
        #         partners = None
        #         partner_data_list = []
        #         # send records having comapny_type = Person
        #         partners = self.search([('quickbooks_id', '=', None), (
        #             'customer_rank', '=', 1), ('is_company', '=', False)], limit=limit)
        #         print(
        #             "Length of partnerssssssssssssssssssssssssssss --------------------------------", len(partners))
        #         print(
        #             "Length of partnerssssssssssssssssssssssssssss --------------------------------", limit, partners)
        #
        #         if partners:
        #             for partner in partners:
        #                 partner_dict = {}
        #                 if partner.company_type == 'person':
        #                     partner_dict = self.get_partner_dict(
        #                         partner, is_send_parent_ref=True)
        #
        #                     if partner_dict:
        #                         partner_data_list.append(partner_dict)
        #
        #         if partner_data_list:
        #             # print('\n\nPartner data List for Persons: ', partner_data_list, '\n\n')
        #             # print('Total Count : ',len(partner_data_list))
        #             company = self.env['res.users'].search(
        #                 [('id', '=', 2)]).company_id
        #             headers = {'content-type': "application/json"}
        #             data = partner_data_list
        #
        #             data = {'customers_list': data}
        #
        #             response = requests.request('POST', company.url + '/export_customers', data=json.dumps(data),
        #                                         headers=headers,
        #                                         verify=False)
        #
        #             try:
        #                 resp = ast.literal_eval(response.text)
        #
        #                 # print('Resp of person: ', resp)
        #                 if isinstance(resp, dict):
        #                     for res in resp.get('Data'):
        #
        #                         if 'odoo_id' in res and res.get('odoo_id'):
        #                             partner_id = self.browse(int(res.get('odoo_id')))
        #
        #                             if partner_id:
        #                                 if res.get('quickbooks_id'):
        #                                     partner_id.write(
        #                                         {'quickbooks_id': res.get('quickbooks_id')})
        #                     loger_dict.update({'operation': 'Export Partner',
        #                                     'odoo_id': res.get('odoo_id'),
        #                                     'qbd_id': res.get('quickbooks_id'),
        #                                     'message': res.get('messgae')
        #                                     })
        #                     qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
        #                     # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})
        #                 else:
        #                     raise UserError(_("No Data in Response Check Quickbook Desktop Terminal"))
        #             except Exception as ex:
        #                 _logger.error(str(ex))
        #                 raise UserError(str(ex))
        #
        # else:
        #     # print('\n\nExport Only Updated Records\n')
        #     partners = self.search([('quickbooks_id', '!=', False), (
        #         'customer_rank', '=', 1), ('is_updated', '=', True)], limit=limit)
        #     # print('Parnters',partners)
        #     if partners:
        #         for partner in partners:
        #             partner_dict = {}
        #             partner_dict = self.get_partner_dict(
        #                 partner, company.export_updated_record, is_send_parent_ref=True,)
        #
        #             if partner_dict:
        #                 partner_data_list.append(partner_dict)
        #
        #     if partner_data_list:
        #         # print('\n\nPartner data List : ', partner_data_list, '\n\n')
        #         # print('Total Count : ', len(partner_data_list))
        #         company = self.env['res.users'].search(
        #             [('id', '=', 2)]).company_id
        #         headers = {'content-type': "application/json"}
        #         data = partner_data_list
        #
        #         data = {'customers_list': data}
        #
        #         response = requests.request('POST', company.url + '/export_customers', data=json.dumps(data),
        #                                     headers=headers,
        #                                     verify=False)
        #
        #         # print("Response Text of person", type(response.text), response.text)
        #
        #         try:
        #             resp = ast.literal_eval(response.text)
        #             if isinstance(resp,dict):
        #                 for res in resp.get('Data'):
        #
        #                     if 'odoo_id' in res and res.get('odoo_id'):
        #                         partner_id = self.browse(int(res.get('odoo_id')))
        #
        #                         if partner_id:
        #                             partner_id.write({'is_updated': False})
        #
        #                     loger_dict.update({'operation': 'Export Partner',
        #                                     'odoo_id': res.get('odoo_id'),
        #                                     'qbd_id': res.get('quickbooks_id'),
        #                                     'message': res.get('messgae')
        #                                     })
        #                     qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
        #                     # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})
        #             else:
        #                 raise UserError(_("No Data in Response Check Quickbook Desktop Terminal"))
        #         except Exception as ex:
        #             _logger.error(str(ex))
        #             raise UserError(str(ex))
        #
        # return True

    def get_partner_dict(self, partner, is_send_updated=False, is_send_parent_ref=False):

        partner_dict = {}

        if is_send_updated:
            partner_dict.update({
                # partner_qbd_id (varchar 36) Only for Update Query
                'partner_qbd_id': partner.quickbooks_id
            })
        else:
            partner_dict.update({
                # partner_qbd_id (varchar 36) Only for Update Query
                'partner_qbd_id': ''
            })

        if is_send_parent_ref:
            partner_dict.update({
                # parent_ref (36 varchar)
                'parent_ref': partner.parent_id.quickbooks_id if partner.parent_id else '',
                'company': False,
            })
        else:
            partner_dict.update({
                'company': True,
            })

        # name (41 varchar) Needs Validation
        # title (15 varchar)
        # first_name (25 varchar) Needs Validation
        # last_name (25 varchar) Needs Validation
        # function (41 varchar)
        # phone (21 varchar)
        # mobile (21 varchar)
        # email (1023 varchar)
        # comment (4095 varchar)
        # city (31 varchar)
        # zip (13 varchar)
        # state_id (21 varchar)
        # country_id (31 varchar)
        # terms_qbd_id (36 varchar)
        # vat
        # ref
        # tags_id

        bad_chars = [';', ':', '!', "*", "$", "'"]
        name = partner.name
        if not isinstance(name, str):
            name = str(name)
        for i in bad_chars:
            name = name.replace(i, "")

        if len(name) > 40:
            name = name[:40]

        full_name = name.split(' ', 1)
        first_name = full_name[0][:24]
        if len(full_name) > 1:
            last_name = full_name[1][:24]
        else:
            last_name = ''

        if partner.comment:
            bad_chars = [';', ':', '!', "*", "$", "'"]
            comment = partner.comment
            for i in bad_chars:
                comment = comment.replace(i, "")
        else:
            comment = ''

        # print (" ----------------- ",partner.parent_id,partner.parent_id.name)

        partner_dict.update({
            'odoo_id': partner.id,
            'name': name,
            'company_ref_name': partner.parent_id.name if partner.parent_id else name,
            'title': partner.title.name if partner.title.name else '',
            'first_name': first_name,
            'last_name': last_name,
            'function': partner.function if partner.function else '',
            'phone': partner.phone if partner.phone else '',
            'mobile': partner.mobile if partner.mobile else '',
            'email': partner.email if partner.email else '',
            'comment': comment,
            'city': partner.city if partner.city else '',
            'zip': partner.zip if partner.zip else '',
            'state_id': partner.state_id.code if partner.state_id else '',
            'country_id': partner.country_id.code if partner.country_id else '',
            'terms_qbd_id': partner.property_payment_term_id.quickbooks_id if partner.property_payment_term_id.quickbooks_id else '',
            'vat': partner.vat if partner.vat else '',
            'ref': partner.ref if partner.ref else '',
            'category_name': partner.category_id.name if partner.category_id.name else '',
            # 'website': partner.website if partner.website else '',
        })
        # print("Partner Dict", partner_dict)

        if partner.street:
            bad_chars = [';', ':', '!', "*", "$", "'"]
            street = partner.street
            for i in bad_chars:
                street = street.replace(i, "")
            data = street  # street (41 varchar)
            partner_dict.update(
                {'street': (data[:40]) if len(data) > 40 else data})

        if partner.street2:
            bad_chars = [';', ':', '!', "*", "$", "'"]
            street2 = partner.street2
            for i in bad_chars:
                street2 = street2.replace(i, "")
            data = street2  # street2 (41 varchar)
            partner_dict.update(
                {'street2': (data[:40]) if len(data) > 40 else data})

        return partner_dict

    # Export Vendors

    def export_vendors(self, vendor_id=None):
        # print('\nIn Export Vendorsssssssss\n')
        vendor_data_list = []
        loger_dict = {}
        # ctx = self._context or {}
        #
        # ctx.update({'dont_update_is_update': False})
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        if company.export_ven_limit:
            limit = int(company.export_ven_limit)
        else:
            limit = 0

        if company.export_updated_record:
            if vendor_id:
                vendors = vendor_id
            else:
                vendors = self.search(['|', ('quickbooks_id', '!=', None), ('quickbooks_id', '!=', ''), (
                    'supplier_rank', '=', 1), ('is_updated', '=', True)], limit=limit)
        else:
            vendors = self.search(['|', ('quickbooks_id', '=', None), (
                'quickbooks_id', '=', ''), ('supplier_rank', '=', 1)], limit=limit)

        if vendors:
            for vendor in vendors:
                vendor_dict = {}
                if company.export_updated_record:
                    vendor_dict = self.get_vendor_dict(
                        vendor, company.export_updated_record)
                else:
                    vendor_dict = self.get_vendor_dict(vendor)

                if vendor_dict:
                    vendor_data_list.append(vendor_dict)

        if vendor_data_list:
            # print('\n\nVendor data List : ', vendor_data_list, '\n\n')
            # print('Total Count : ', len(vendor_data_list))
            company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
            headers = {'content-type': "application/json"}
            data = vendor_data_list

            data = {'vendors_list': data}

            response = requests.request('POST', company.url + '/export_vendors', data=json.dumps(data),
                                        headers=headers,
                                        verify=False)

            # print("Response Text ", type(response.text), response.text)

            try:
                resp = ast.literal_eval(response.text)

                if isinstance(resp,dict):
                    if company.export_updated_record == False:
                        for res in resp.get('Data'):
                            if resp.get('Message'):
                                raise UserError(_("No Vendor Exported"))
                            if 'odoo_id' in res and res.get('odoo_id'):
                                vendor_id = self.browse(int(res.get('odoo_id')))

                                if vendor_id:
                                    if res.get('quickbooks_id'):
                                        vendor_id.write(
                                            {'quickbooks_id': res.get('quickbooks_id')})
                            loger_dict.update({'operation': 'Export Vendor',
                                            'odoo_id': res.get('odoo_id'),
                                            'qbd_id': res.get('quickbooks_id'),
                                            'message': res.get('messgae')
                                            })
                            qbd_loger_id = self.env['qbd.loger'].create(loger_dict)
                            # company.write({'qbd_loger_id': [(4, qbd_loger_id.id)]})

                    else:
                        for res in resp.get('Data'):
                            if resp.get('Message'):
                                raise UserError(_("No Vendor Exported"))
                            if 'odoo_id' in res and res.get('odoo_id'):
                                vendor_id = self.browse(int(res.get('odoo_id')))

                                if vendor_id:
                                    vendor_id.write({'is_updated': False})
                            loger_dict.update({'operation': 'Export Vendor',
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

    def get_vendor_dict(self, vendor, is_send_only_updated=False):

        vendor_dict = {}

        if is_send_only_updated:
            vendor_dict.update({
                'vendor_qbd_id': vendor.quickbooks_id
            })
        else:
            vendor_dict.update({
                'vendor_qbd_id': ''
            })

        # name (41 varchar) Needs Validation
        # title (15 varchar)
        # first_name (25 varchar) Needs Validation
        # last_name (25 varchar) Needs Validation
        # phone (21 varchar)
        # mobile (21 varchar)
        # email (1023 varchar)
        # comment (4095 varchar)
        # city (31 varchar)
        # zip (13 varchar)
        # state_id (21 varchar)
        # country_id (31 varchar)
        # terms_qbd_id (36 varchar)
        # vat
        # ref
        # category_name

        bad_chars = [';', ':', '!', "*", "$", "'"]
        name = vendor.name
        for i in bad_chars:
            name = name.replace(i, "")

        if len(name) > 40:
            name = name[:40]

        full_name = name.split(' ', 1)
        # print("Full Nameeeeeeeeeeeeeeeeeeeeeeeeeee", full_name[0][:24])
        first_name = full_name[0][:24]
        if len(full_name) > 1:
            last_name = full_name[1][:24]
        else:
            last_name = ''

        if vendor.comment:
            bad_chars = [';', ':', '!', "*", "$", "'"]
            comment = vendor.comment
            for i in bad_chars:
                comment = comment.replace(i, "")
        else:
            comment = ''

        vendor_dict.update({
            'odoo_id': vendor.id,
            'name': name,
            'title': vendor.title.name if vendor.title.name else '',
            'first_name': first_name,
            'last_name': last_name,
            'phone': vendor.phone if vendor.phone else '',
            'mobile': vendor.mobile if vendor.mobile else '',
            'email': vendor.email if vendor.email else '',
            'comment': comment,
            'city': vendor.city if vendor.city else '',
            'zip': vendor.zip if vendor.zip else '',
            'state_id': vendor.state_id.code if vendor.state_id else '',
            'country_id': vendor.country_id.code if vendor.country_id else '',
            'terms_qbd_id': vendor.property_supplier_payment_term_id.quickbooks_id if vendor.property_supplier_payment_term_id.quickbooks_id else '',
            'vat': vendor.vat if vendor.vat else '',
            'ref': vendor.ref if vendor.ref else '',
            'category_name': vendor.category_id.name if vendor.category_id.name else '',
        })

        if vendor.street:
            bad_chars = [';', ':', '!', "*", "$", "'"]
            street = vendor.street
            for i in bad_chars:
                street = street.replace(i, "")
            data = street  # street (41 varchar)
            vendor_dict.update({'street': (data[:40]) if len(
                data) > 40 else data})  # street (41 varchar)

        if vendor.street2:
            bad_chars = [';', ':', '!', "*", "$", "'"]
            street2 = vendor.street2
            for i in bad_chars:
                street2 = street2.replace(i, "")
            data = street2
            vendor_dict.update(
                {'street2': (data[:40]) if len(data) > 40 else data})

        if vendor_dict:
            return vendor_dict
