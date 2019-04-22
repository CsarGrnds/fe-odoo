# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import api, fields, models

CR_GROUP_TAX = [('excvat', 'Excento de IVA'),
                ('vat', 'IVA Diferente de 0%'),
                ('other', 'Other')]

class account_tax_template(models.Model):
    _name = 'account.tax.template'
    _inherit = 'account.tax.template'

    cr_group_tax_use = fields.Selection(CR_GROUP_TAX, 'Tax Use In', select=True)

    def _get_tax_vals(self, company):
        val = super(account_tax_template, self)._get_tax_vals(company)
        if self.cr_group_tax_use:
            val['cr_group_tax_use'] = self.cr_group_tax_use
        return val

class account_tax(models.Model):
    _name = 'account.tax'
    _inherit = 'account.tax'

    cr_group_tax_use = fields.Selection(CR_GROUP_TAX, 'Tax Use In', select=True, default='other')

class account_invoice_tax(models.Model):
    _inherit = 'account.invoice.tax'

    cr_group_tax_use = fields.Selection(CR_GROUP_TAX, 'Tax Use In', select=True)

class account_tax_group(models.Model):
    _inherit = "account.tax.group"

    fe_tax_code = fields.Char('FE Code', size=2, select=True)