from odoo import api, fields, models, _

class StockQuant_Inherit(models.Model):
    _inherit = "stock.quant"

    def write(self, vals):
        if self.product_id.product_tmpl_id.qty_updated:
            self.product_id.product_tmpl_id.write({
                'qty_updated': False
            })
        return super(StockQuant_Inherit, self).write(vals)