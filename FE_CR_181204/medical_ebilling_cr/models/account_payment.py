# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError, ValidationError

class account_payment(models.Model):
    _inherit = "account.payment"

    def _create_payment_entry(self, amount):
        move = super(account_payment, self)._create_payment_entry(amount)
        if move:
            if self.invoice_ids:
                for inv in self.invoice_ids:
                    if move.journal_id.id not in inv.payment_method_ids.ids:
                        inv.write({'payment_method_ids': [(4, move.journal_id.id)]})
        return move

class account_register_payments(models.TransientModel):
    _inherit = "account.register.payments"

    @api.multi
    def create_payment(self):
        res = super(account_register_payments, self).create_payment()
        invs = self._get_invoices()
        if invs:
            for inv in invs:
                if self.journal_id.id not in inv.payment_method_ids.ids:
                    inv.write({'payment_method_ids': [(4, self.journal_id.id)]})

        return res
