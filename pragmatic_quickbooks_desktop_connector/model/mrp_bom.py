from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MrpBomInherit(models.Model):
    _inherit = 'mrp.bom'

    def _check_bom_exists(self, qbd_id):
        '''
            This helper method will search if the product's
            BOM exitsts in Odoo or not
        '''
        return self.search_count([('product_tmpl_id.quickbooks_id', '=', qbd_id)])

    def _get_odoo_product_id_from_qbd_id(self, qbd_id):
        '''
            Helper method to get odoo product ID from qbd id
            @params : qbd_id

        '''
        return self.env['product.product'].search([('quickbooks_id', '=', qbd_id)])

    def _create_bom(self, bom_data_dict):
        self.create(bom_data_dict)

    def create_bom_of_qbd_product(self, qbd_response):
        '''
            This method will create BOM of product
        '''
        qbd_id = qbd_response.get('bom_id')
        bom_exists = self._check_bom_exists(qbd_id)
        if not bom_exists:
            _logger.info("BOM does not exits we will create it..")
            bom_product_tmpl_id = False
            bom_product_tmpl_id = self._get_odoo_product_id_from_qbd_id(qbd_id)
            if bom_product_tmpl_id:
                bom_data_dict = {'product_tmpl_id': bom_product_tmpl_id.id,
                                 'bom_line_ids': []}
                for rec in qbd_response.get('bom_lines'):
                    product_id = self._get_odoo_product_id_from_qbd_id(
                        rec.get('ItemGroupLineItemRefListID'))
                    if not product_id:
                        raise UserError(_('{} is not present in odoo'.format(
                            rec.get('ItemGroupLineItemRefFullName', 'One of BOM product'))))
                    bom_data_dict['bom_line_ids'].append((0, 0, {'product_id': product_id.id,
                                                                 'product_qty': rec.get('ItemGroupLineQuantity', 1)}))

                if bom_data_dict:
                    _logger.info(bom_data_dict)
                    self._create_bom(bom_data_dict)
        else:
            raise UserError(_('BOM Already exists for this product.'))
