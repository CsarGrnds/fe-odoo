# -*- encoding: utf-8 -*-
from openerp import models, fields, api

class account_journal(models.Model):
    _inherit = 'account.journal'

    fe_code = fields.Char('FE Code', size=2)