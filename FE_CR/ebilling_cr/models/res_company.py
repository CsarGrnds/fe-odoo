# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, an open source suite of business apps
#    This module copyright (C) 2014-2015 Therp BV (<http://therp.nl>).
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
from openerp.tools.translate import _

docs_type = [
        ('01', 'Cedula Fisica'),
        ('02', 'Cedula Juridica'),
        ('03', 'DIMEX'),
        ('04', 'NITE'),
        ('100', 'Identificacion Extranjero'),
    ]

class Company(models.Model):
    _inherit = 'res.company'

    ebiller_id = fields.Many2one('electronic.biller.cr', 'Biller', select=True)
    establishment_code = fields.Char('Establishment code', default='001', select=True)
    branch_office_ids = fields.One2many('branch.office', 'company_id', string="Branch Offices")
    emision_points = fields.One2many('emision.point', 'company_id', string="Emision points")
    edi_doc_ids = fields.One2many('electronic.document.generic.cr', 'company_id', string="Electronic Documents")
    identification_type = fields.Selection(docs_type, string="Identification Type")
    identification_cr = fields.Char(string="Identification", size=12)
    comercial_name = fields.Char(string="Business Name", size=80)
    key_store_file = fields.Binary(string='Archivo LLave', attachment=True)
    key_store_pswd = fields.Char(string='Password de la Llave', size=300, required=False)
    mh_oauth_username = fields.Char('Usuario de API', copy=False)
    mh_oauth_password = fields.Char('Contraseña de API', copy=False)

    @api.model
    def create(self, vals):
        company = super(Company, self).create(vals)
        if vals.get('comercial_name', False):
            if company.partner_id:
                company.partner_id.write({'comercial_name': company.comercial_name})
        return company

    @api.multi
    def write(self, vals):
        res = super(Company, self).write(vals)
        if vals.get('comercial_name', False):
            for comp_t in self:
                if comp_t.partner_id:
                    comp_t.partner_id.write({'comercial_name': comp_t.comercial_name})
        return res

    @api.multi
    def unlink(self):
        for company in self:
            if company.branch_office_ids:
                raise Warning(_("You can not delete company, have Branch Offices."))
            if company.emision_points:
                raise Warning(_("You can not delete company, have emision points."))
        return super(Company, self).unlink()

    @api.model
    def cron_get_status_docs(self):
        today = fields.Date.today()
        comp_list = self.with_context(cron=True).search([])
        if comp_list:
            for company in comp_list:
                if company.edi_doc_ids:
                    for doc in company.edi_doc_ids:
                        if not doc.date_accepted or not doc.not_accepted:
                            if doc.days_for_acceptance < 8:
                                print "si este"
        return True

class branch_office(models.Model):
    _name = 'branch.office'
    _description = 'Branch Office'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', default='001', required=True, select=True)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id, select=True)
    emision_points = fields.One2many('emision.point', 'branch_office_id', string="Branch Office")
    # invoice_ids = fields.One2many('account.invoice', 'branch_office_id', 'Invoices')

    @api.multi
    def unlink(self):
        for branch_off in self:
            invoice_list = self.env['account.invoice'].search([('branch_office_id', '=', branch_off.id)])
            if invoice_list:
                raise Warning(_("You can not delete Branch Office, have invoices."))
            if branch_off.emision_points:
                raise Warning(_("You can not delete Branch Office, have emision points."))
        return super(branch_office, self).unlink()

class emision_point(models.Model):
    _name = 'emision.point'
    _description = 'Emision Point'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', default='00001', required=True, select=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id, select=True)
    branch_office_id = fields.Many2one('branch.office', string="Branch Office", select=True)
    invoice_sequence_id = fields.Many2one('ir.sequence', 'Invoice Sequence', select=True)
    invoice_number_next = fields.Integer('Invoice Next Number', default=1)
    refund_sequence_id = fields.Many2one('ir.sequence', 'Refund Sequence', select=True)
    refund_number_next = fields.Integer('Refund Next Number', default=1)
    debit_note_sequence_id = fields.Many2one('ir.sequence', 'Debit Note Sequence', select=True)
    debit_note_number_next = fields.Integer('Debit Note Next Number', default=1)
    electronic_ticket_sequence_id = fields.Many2one('ir.sequence', 'Electronic Ticket Sequence', select=True)
    electronic_ticket_number_next = fields.Integer('Electronic Ticket Next Number', default=1)
    acceptance_confirmation_sequence_id = fields.Many2one('ir.sequence', 'Acceptance Confirmation Sequence')
    acceptance_confirmation_number_next = fields.Integer('Acceptance Confirmation Next Number', default=1)
    partial_acceptance_confirmation_sequence_id = fields.Many2one('ir.sequence', 'Partial Acceptance Confirmation Sequence')
    partial_acceptance_confirmation_number_next = fields.Integer('Partial Acceptance Confirmation Next Number', default=1)
    rejection_confirmation_sequence_id = fields.Many2one('ir.sequence', 'Rejection Confirmation Sequence')
    rejection_confirmation_number_next = fields.Integer('Rejection Confirmation Next Number', default=1)
    # invoice_ids = fields.One2many('account.invoice', 'emision_point_id', 'Invoices')
    active = fields.Boolean('Active', default=True)

    @api.model
    def create(self, vals):
        seq_obj = self.env['ir.sequence']
        seq_data = {'padding': 10,
                    'number_next': 1,
                    'number_increment': 1,
                    'company_id': vals.get('company_id', False) or self.env.user.company_id.id
        }
        establishment_code = self.env.user.company_id.establishment_code
        code_branch = ''
        if vals.get('branch_office_id', False):
            code_branch = self.env['branch.office'].browse(vals['branch_office_id']).code

        if vals.get('invoice_number_next', 0):
            if vals['invoice_number_next'] > 0:
                seq_data['name'] = 'Invoice CR Sequence ' + self.env.user.company_id.name
                seq_data['number_next'] = vals['invoice_number_next'] or 1
                seq_data['code'] = establishment_code + '_' + vals['code'] + '_invoice'
                if code_branch:
                    seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals['code'] + '_invoice'
                seq_invoice_id = seq_obj.create(seq_data)
                if seq_invoice_id:
                    vals.update({'invoice_sequence_id': seq_invoice_id.id})

        if vals.get('refund_number_next', 0):
            if vals['refund_number_next'] > 0:
                seq_data['name'] = 'Refund CR Sequence ' + self.env.user.company_id.name
                seq_data['number_next'] = vals['refund_number_next'] or 1
                seq_data['code'] = establishment_code + '_' + vals['code'] + '_refund'
                if code_branch:
                    seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals['code'] + '_refund'
                seq_refund_id = seq_obj.create(seq_data)
                if seq_refund_id:
                    vals.update({'refund_sequence_id': seq_refund_id.id})

        if vals.get('electronic_ticket_number_next', 0):
            if vals['electronic_ticket_number_next'] > 0:
                seq_data['name'] = 'Electronic Ticket Sequence ' + self.env.user.company_id.name
                seq_data['number_next'] = vals['electronic_ticket_number_next'] or 1
                seq_data['code'] = establishment_code + '_' + vals['code'] + '_electronic_ticket'
                if code_branch:
                    seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals['code'] + '_electronic_ticket'
                seq_electronic_ticket_id = seq_obj.create(seq_data)
                if seq_electronic_ticket_id:
                    vals.update({'electronic_ticket_sequence_id': seq_electronic_ticket_id.id})

        if vals.get('debit_note_number_next', 0):
            if vals['debit_note_number_next'] > 0:
                seq_data['name'] = 'Debit Note CR Sequence ' + self.env.user.company_id.name
                seq_data['number_next'] = vals['debit_note_number_next'] or 1
                seq_data['code'] = establishment_code + '_' + vals['code'] + '_debit_note'
                if code_branch:
                    seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals['code'] + '_debit_note'
                seq_debit_note = seq_obj.create(seq_data)
                if seq_debit_note:
                    vals.update({'debit_note_sequence_id': seq_debit_note.id})

        if vals.get('acceptance_confirmation_number_next', 0):
            if vals['acceptance_confirmation_number_next'] > 0:
                seq_data['name'] = 'Acceptance Confirmation CR Sequence ' + self.env.user.company_id.name
                seq_data['number_next'] = vals['acceptance_confirmation_number_next'] or 1
                seq_data['code'] = establishment_code + '_' + vals['code'] + '_acceptance_confirmation'
                if code_branch:
                    seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals['code'] + '_acceptance_confirmation'
                acceptance_confirmation_sequence = seq_obj.create(seq_data)
                if acceptance_confirmation_sequence:
                    vals.update({'acceptance_confirmation_sequence_id': acceptance_confirmation_sequence.id})

        if vals.get('partial_acceptance_confirmation_number_next', 0):
            if vals['partial_acceptance_confirmation_number_next'] > 0:
                seq_data['name'] = 'Partial Acceptance Confirmation CR Sequence ' + self.env.user.company_id.name
                seq_data['number_next'] = vals['partial_acceptance_confirmation_number_next'] or 1
                seq_data['code'] = establishment_code + '_' + vals['code'] + '_partial_acceptance_confirmation'
                if code_branch:
                    seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals['code'] + '_partial_acceptance_confirmation'
                partial_acceptance_confirmation_sequence = seq_obj.create(seq_data)
                if partial_acceptance_confirmation_sequence:
                    vals.update({'partial_acceptance_confirmation_sequence_id': partial_acceptance_confirmation_sequence.id})

        if vals.get('rejection_confirmation_number_next', 0):
            if vals['rejection_confirmation_number_next'] > 0:
                seq_data['name'] = 'Rejection Confirmation CR Sequence ' + self.env.user.company_id.name
                seq_data['number_next'] = vals['rejection_confirmation_number_next'] or 1
                seq_data['code'] = establishment_code + '_' + vals['code'] + '_rejection_confirmation'
                if code_branch:
                    seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals['code'] + '_rejection_confirmation'
                rejection_confirmation_sequence = seq_obj.create(seq_data)
                if rejection_confirmation_sequence:
                    vals.update({'rejection_confirmation_sequence_id': rejection_confirmation_sequence.id})

        return super(emision_point, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(emision_point, self).write(vals)
        if vals.get('invoice_number_next', 0) or vals.get('refund_number_next', 0) or \
                vals.get('electronic_ticket_number_next', 0) or vals.get('debit_note_number_next', 0) or\
                vals.get('acceptance_confirmation_number_next', 0) or \
                vals.get('partial_acceptance_confirmation_number_next', 0) or \
                vals.get('rejection_confirmation_number_next', 0):
            seq_obj = self.env['ir.sequence']
            seq_data = {'padding': 10,
                        'number_next': 1,
                        'number_increment': 1
            }

            for em_point in self:
                establishment_code = em_point.company_id.establishment_code
                code_branch = ''
                if em_point.branch_office_id:
                    code_branch = em_point.branch_office_id.code
                seq_data.update({'company_id': em_point.company_id.id})
                if vals.get('invoice_number_next', 0):
                    if vals['invoice_number_next'] > 0:
                        if em_point.invoice_sequence_id:
                            em_point.invoice_sequence_id.write({'number_next': vals['invoice_number_next']})
                        else:
                            seq_data['name'] = 'Invoice CR Sequence ' + em_point.company_id.name
                            seq_data['number_next'] = vals['invoice_number_next'] or 1
                            seq_data['code'] = establishment_code + '_' + vals['code'] + '_invoice'
                            if code_branch:
                                seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals[
                                    'code'] + '_invoice'
                            seq_invoice_id = seq_obj.create(seq_data)
                            if seq_invoice_id:
                                em_point.invoice_sequence_id = seq_invoice_id.id

                if vals.get('refund_number_next', 0):
                    if vals['refund_number_next'] > 0:
                        if em_point.refund_sequence_id:
                            em_point.refund_sequence_id.write({'number_next': vals['refund_number_next']})
                        else:
                            seq_data['name'] = 'Refund CR Sequence ' + em_point.company_id.name
                            seq_data['number_next'] = vals['refund_number_next'] or 1
                            seq_data['code'] = establishment_code + '_' + vals['code'] + '_refund'
                            if code_branch:
                                seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals[
                                    'code'] + '_refund'
                            seq_refund_id = seq_obj.create(seq_data)
                            if seq_refund_id:
                                em_point.refund_sequence_id = seq_refund_id.id

                if vals.get('electronic_ticket_number_next', 0):
                    if vals['electronic_ticket_number_next'] > 0:
                        if em_point.electronic_ticket_sequence_id:
                            em_point.electronic_ticket_sequence_id.write({'number_next': vals['electronic_ticket_number_next']})
                        else:
                            seq_data['name'] = 'Electronic Ticket CR Sequence ' + em_point.company_id.name
                            seq_data['number_next'] = vals['electronic_ticket_number_next'] or 1
                            seq_data['code'] = establishment_code + '_' + vals['code'] + '_electronic_ticket'
                            if code_branch:
                                seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals[
                                    'code'] + '_electronic_ticket'
                            seq_electronic_ticket_id = seq_obj.create(seq_data)
                            if seq_electronic_ticket_id:
                                em_point.electronic_ticket_sequence_id = seq_electronic_ticket_id.id

                if vals.get('debit_note_number_next', 0):
                    if vals['debit_note_number_next'] > 0:
                        if em_point.debit_note_sequence_id:
                            em_point.debit_note_sequence_id.write({'number_next': vals['debit_note_number_next']})
                        else:
                            seq_data['name'] = 'Debit Note CR Sequence ' + em_point.company_id.name
                            seq_data['number_next'] = vals['debit_note_number_next'] or 1
                            seq_data['code'] = establishment_code + '_' + vals['code'] + '_debit_note'
                            if code_branch:
                                seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals[
                                    'code'] + '_debit_note'
                            seq_debit_note = seq_obj.create(seq_data)
                            if seq_debit_note:
                                em_point.debit_note_sequence_id = seq_debit_note.id

                if vals.get('acceptance_confirmation_number_next', 0):
                    if vals['acceptance_confirmation_number_next'] > 0:
                        if em_point.acceptance_confirmation_sequence_id:
                            em_point.acceptance_confirmation_sequence_id.write(
                                {'number_next': vals['acceptance_confirmation_number_next']})
                        else:
                            seq_data['name'] = 'Acceptance Confirmation CR Sequence ' + self.env.user.company_id.name
                            seq_data['number_next'] = vals['acceptance_confirmation_number_next'] or 1
                            seq_data['code'] = establishment_code + '_' + vals['code'] + '_acceptance_confirmation'
                            if code_branch:
                                seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals[
                                    'code'] + '_acceptance_confirmation'
                            acceptance_confirmation_sequence = seq_obj.create(seq_data)
                            if acceptance_confirmation_sequence:
                                vals.update({'acceptance_confirmation_sequence_id': acceptance_confirmation_sequence.id})

                if vals.get('partial_acceptance_confirmation_number_next', 0):
                    if vals['partial_acceptance_confirmation_number_next'] > 0:
                        if em_point.partial_acceptance_confirmation_sequence_id:
                            em_point.partial_acceptance_confirmation_sequence_id.write(
                                {'number_next': vals['partial_acceptance_confirmation_number_next']})
                        else:
                            seq_data['name'] = 'Partial Acceptance Confirmation CR Sequence ' + \
                                               self.env.user.company_id.name
                            seq_data['number_next'] = vals['partial_acceptance_confirmation_number_next'] or 1
                            seq_data['code'] = establishment_code + '_' + vals['code'] + '_partial_acceptance_confirmation'
                            if code_branch:
                                seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals[
                                    'code'] + '_partial_acceptance_confirmation'
                            partial_acceptance_confirmation_sequence = seq_obj.create(seq_data)
                            if partial_acceptance_confirmation_sequence:
                                vals.update({'partial_acceptance_confirmation_sequence_id':
                                                 partial_acceptance_confirmation_sequence.id})

                if vals.get('rejection_confirmation_number_next', 0):
                    if vals['rejection_confirmation_number_next'] > 0:
                        if em_point.rejection_confirmation_sequence_id:
                            em_point.rejection_confirmation_sequence_id.write(
                                {'number_next': vals['rejection_confirmation_number_next']})
                        else:
                            seq_data['name'] = 'Rejection Confirmation CR Sequence ' + self.env.user.company_id.name
                            seq_data['number_next'] = vals['rejection_confirmation_number_next'] or 1
                            seq_data['code'] = establishment_code + '_' + vals['code'] + '_rejection_confirmation'
                            if code_branch:
                                seq_data['code'] = establishment_code + '_' + code_branch + '_' + vals[
                                    'code'] + '_rejection_confirmation'
                            rejection_confirmation_sequence = seq_obj.create(seq_data)
                            if rejection_confirmation_sequence:
                                vals.update({'rejection_confirmation_sequence_id': rejection_confirmation_sequence.id})

        return res

    @api.multi
    def unlink(self):
        for em_point in self:
            invoice_list = self.env['account.invoice'].search([('emision_point_id', '=', em_point.id)])
            if invoice_list:
                raise Warning(_("You can not delete emission point, have invoices."))
        return super(emision_point, self).unlink()

class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    emision_point_inv_ids = fields.One2many('emision.point', 'invoice_sequence_id', 'Emission Point for Invoices')
    emision_point_refund_ids = fields.One2many('emision.point', 'refund_sequence_id', 'Emission Point for Refunds')
    emision_point_electronic_ticket_ids = fields.One2many('emision.point', 'electronic_ticket_sequence_id', 'Emission Point for Electronic Tickets')
    emision_point_debit_note_ids = fields.One2many('emision.point', 'debit_note_sequence_id',
                                                   'Emission Point for Debit Notes')
    emision_point_accept_confirm_seq_ids = fields.One2many('emision.point', 'acceptance_confirmation_sequence_id',
                                                   'Emission Point for Acceptance Confirmation')
    emision_point_part_accept_confirm_seq_ids = fields.One2many('emision.point', 'partial_acceptance_confirmation_sequence_id',
                                                   'Emission Point for Partial Acceptance Confirmation')
    emision_point_rejection_confirm_seq_ids = fields.One2many('emision.point', 'rejection_confirmation_sequence_id',
                                                   'Emission Point for Rejection Confirmation')

    @api.multi
    def unlink(self):
        for sequence in self:
            if sequence.emision_point_inv_ids or sequence.emision_point_refund_ids or \
                    sequence.emision_point_electronic_ticket_ids or \
                    sequence.emision_point_accept_confirm_seq_ids or \
                    sequence.emision_point_part_accept_confirm_seq_ids or \
                    sequence.emision_point_rejection_confirm_seq_ids or \
                    sequence.emision_point_debit_note_ids:
                raise Warning(_("You can not delete sequence, have Emision Point related."))
        return super(IrSequence, self).unlink()