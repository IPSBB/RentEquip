from odoo import api, fields, models, _
import ast
import json
import requests

class QBDPaymentMethod(models.Model):
    _name = "qbd.payment.method"
    _description = "QBD Payment Method"

    name = fields.Char('Name')
    quickbooks_id = fields.Char("Quickbook id ", copy=False)

    def create_qbd_payment_methods(self,payment_methods_data):
        print("\n\n")
        if payment_methods_data:
            for payment_method in payment_methods_data:
                vals = {}

                if type(payment_method)==str:
                    continue

                if 'payment_type' in payment_method and payment_method.get('payment_type'):
                    qbd_payment_method_id = self.search([('name','=',payment_method.get('payment_type'))],limit=1)


                    if not qbd_payment_method_id:
                        vals.update({
                            'name': payment_method.get('payment_type'),
                            'quickbooks_id': payment_method.get('quickbooks_id')
                        })

                        if vals:
                            self.create(vals)
                    else:
                        vals.update({
                            'quickbooks_id': payment_method.get('quickbooks_id')
                        })
                        qbd_payment_method_id.write(vals)
        return True
    

    # @api.multi
    # def export_qbd_payment_methods(self):
    #     print('Export QBD Payment Method hereeeeeeeeeeeeeeeeeeeeee')
    #     payment_method_data = []
    #     qbd_payment_methods = self.search([('quickbooks_id','=',None)])
    #
    #     if qbd_payment_methods:
    #         for payment_method in qbd_payment_methods:
    #             payment_method_dict= {}
    #             payment_method_dict.update({
    #                 'odoo_id':payment_method.id,
    #                 'name':payment_method.name
    #             })
    #
    #             if payment_method_dict:
    #                 payment_method_data.append(payment_method_dict)
    #
    #     if payment_method_data:
    #         print('\nPayment Method data : ',payment_method_data)
    #         print('Total Count ',len(payment_method_data))
    #         company = self.env['res.users'].search([('id', '=', 2)]).company_id
    #         headers = {'content-type': "application/json"}
    #         data = payment_method_data
    #
    #         data = {'payment_method_list': data}
    #
    #         response = requests.request('POST', company.url + '/export_payments_method', data=json.dumps(data),
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
    #                 payment_method_id = self.browse(int(res.get('odoo_id')))
    #
    #                 if payment_method_id:
    #                     payment_method_id.write({'quickbooks_id': res.get('quickbooks_id')})
    #
    #     return True