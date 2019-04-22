# -*- coding: utf-8 -*-
from openerp import api, fields, models

class invoice_product_code_type(models.Model):
    _name = 'invoice.product.code.type'
    _description = 'Invoice Product Code Type'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', size=2, select=True)

class product_template(models.Model):
    _inherit = 'product.template'

    code_type_id = fields.Many2one('invoice.product.code.type', string="Code Type", select=True)

class product_product(models.Model):
    _inherit = 'product.product'

    # code_type_id = fields.Many2one('invoice.product.code.type', string="Code Type")
    default_code = fields.Char('Code', select=True, size=20)

class product_uom(models.Model):
    _inherit = 'product.uom'

    description_fe = fields.Char('Description para FE', size=20)