# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import threading
from openerp.exceptions import ValidationError, except_orm, RedirectWarning
from openerp.addons.medical_ebilling_cr.tools.validation_cr import cedula_01_validation, cedula_02_validation, dimex_validation, nite_validation
from openerp.tools import ustr
import simplejson
import datetime

import logging
import pprint
_logger = logging.getLogger(__name__)

EBI_STATES = [
    ('to_check', 'Borrador'), ('draft', 'No enviado'), ('send', 'Enviado'), ('auth', 'Autorizado'),
    ('noauth', 'No autorizado'), ('cancel', 'Anulado')
]

docs_type = [
        ('01', 'Cedula Fisica'),
        ('02', 'Cedula Juridica'),
        ('03', 'DIMEX'),
        ('04', 'NITE'),
        ('100', 'Identificacion Extranjero'),
    ]

class EbiError(except_orm):
    def __init__(self, msg):
        super(EbiError, self).__init__('EbiError', msg)

class AccountInvoicePaymentMethod(models.Model):
    _name = 'account.invoice.payment.method'
    _description = 'Account Invoice Payment Method'

    name = fields.Char('Description', size=512, required=True)
    code = fields.Char('Code', size=2, required=True)
    active = fields.Boolean('Active', default=True)

class invoice_condition(models.Model):
    _name = 'invoice.condition'
    _description = 'Invoice Condition'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', size=2, required=True, select=True)
    active = fields.Boolean('Active', default=True)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def invoice_print_fe(self):
        self.ensure_one()
        return self.env['report'].get_action(self.edig_id, 'medical_ebilling_cr.report_document_generic_mh')

    @api.model
    def get_default_paym_meth(self):
        l_ch = []
        journal_cash = self.env['account.journal'].search([('type', '=', 'cash')])
        if journal_cash:
            l_ch.append(journal_cash.ids[0])
        return l_ch

    @api.model
    def _get_default_branch_office(self):
        branch_office_ids = [aux for aux in self.company_id.branch_office_ids if aux.active]
        branch_office_id_t = False
        if branch_office_ids:
            branch_office_id_t = branch_office_ids[0] if branch_office_ids else False

        return branch_office_id_t

    @api.model
    def _get_default_emssion_point(self):
        branch_office_ids = [aux for aux in self.company_id.branch_office_ids if aux.active]
        emision_point_t = False
        if branch_office_ids:
            branch_office_tmp = branch_office_ids[0].id if branch_office_ids else False
            point = [aux_p for aux_p in self.company_id.emision_points if aux_p.active and aux_p.branch_office_id.id == branch_office_tmp]
            if point:
                emision_point_t = point[0] if point else False
        else:
            point = [aux for aux in self.env.user.company_id.emision_points if aux.active]
            if point:
                emision_point_t = point[0].id if point else False

        return emision_point_t

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.discount', 'tax_line_ids.amount', 'currency_id', 'company_id', 'date_invoice',
                 'type')
    def _amount_total_cr(self):
        total_serv_grav_sum = 0.0
        total_serv_exentos_sum = 0.0
        total_merc_grav_sum = 0.0
        total_merc_exentas_sum = 0.0
        total_impuesto_sum = 0.0
        amount_disct = 0.0

        for tax in self.tax_line_ids:
            for line in tax.invoice_id.invoice_line_ids:
                price_unit = line.price_unit
                if tax.tax_id in line.invoice_line_tax_ids:
                    if line.product_id:
                        if line.product_id.type == 'service':
                            if tax.tax_id.cr_group_tax_use == 'vat':
                                total_serv_grav_sum += tax.tax_id.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['base']
                            if tax.tax_id.cr_group_tax_use == 'excvat':
                                total_serv_exentos_sum += tax.tax_id.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['base']

                        if line.product_id.type in ['product', 'consu']:
                            if tax.tax_id.cr_group_tax_use == 'vat':
                                total_merc_grav_sum += tax.tax_id.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['base']
                            if tax.tax_id.cr_group_tax_use == 'excvat':
                                total_merc_exentas_sum += tax.tax_id.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['base']
                    else:
                        if tax.tax_id.cr_group_tax_use == 'vat':
                            total_serv_grav_sum += tax.tax_id.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['base']
                        if tax.tax_id.cr_group_tax_use == 'excvat':
                            total_serv_exentos_sum += tax.tax_id.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['base']

        for line in self.tax_line_ids:
            if line.tax_id.cr_group_tax_use == 'vat':
                total_impuesto_sum += line.amount

        for line in self.invoice_line_ids:
            price_unit = line.price_unit
            discount_porcentage = line.discount / 100
            discount = price_unit * discount_porcentage
            if self.type in ('out_invoice', 'out_refund'):
                amount_disct += round(discount * line.quantity, 2)
            else:
                amount_disct += discount * line.quantity

        self.total_serv_grav = total_serv_grav_sum
        self.total_serv_exentos = total_serv_exentos_sum
        self.total_merc_grav = total_merc_grav_sum
        self.total_merc_exentas = total_merc_exentas_sum
        self.total_gravado = total_serv_grav_sum + total_merc_grav_sum
        self.total_exento = total_serv_exentos_sum + total_merc_exentas_sum
        self.total_venta = total_serv_grav_sum + total_merc_grav_sum + total_serv_exentos_sum + total_merc_exentas_sum
        self.total_descuento = amount_disct
        self.total_venta_net = (total_serv_grav_sum + total_merc_grav_sum + total_serv_exentos_sum + total_merc_exentas_sum) - amount_disct
        self.total_impuesto = total_impuesto_sum
        self.total_comprobante = total_impuesto_sum + ((total_serv_grav_sum + total_merc_grav_sum + total_serv_exentos_sum + total_merc_exentas_sum) - amount_disct)

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id')
    def cr_compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_tax = sum(line.amount for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            amount_total_company_signed = self.currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = self.currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

        amount_tax = amount_tax_all = 0.0

        for line in self.tax_line_ids:
            amount_tax_all += line.amount
            if line.tax_id.cr_group_tax_use == 'vat':
                amount_tax += line.amount
        self.amount_tax = amount_tax
        self.amount_total = self.amount_untaxed + amount_tax_all

    @api.one
    @api.depends('emision_point_id', 'branch_office_id', 'num_sequential', 'ebi_voucher_type', 'company_id')
    def _get_complete_number(self):
        if self.emision_point_id and self.num_sequential:
            first_segment = self.company_id.establishment_code
            if self.branch_office_id:
                first_segment = self.branch_office_id.code
            complete_number = '%s%s%s%s' % (first_segment, self.emision_point_id.code, self.ebi_voucher_type, self.num_sequential)
            self.ebi_number_doc = complete_number

    @api.one
    @api.depends('emision_point_id', 'branch_office_id', 'num_sequential', 'ebi_voucher_type', 'ebi_confirmation_type', 'company_id')
    def _get_complete_acceptance_number(self):
        if self.emision_point_id and self.num_sequential:
            first_segment = self.company_id.establishment_code
            if self.branch_office_id:
                first_segment = self.branch_office_id.code
            ebi_voucher_type_t = self.ebi_voucher_type
            if self.type in ['in_invoice', 'in_refund']:
                if self.ebi_confirmation_type == '1':
                    ebi_voucher_type_t = '05'
                if self.ebi_confirmation_type == '2':
                    ebi_voucher_type_t = '06'
                if self.ebi_confirmation_type == '3':
                    ebi_voucher_type_t = '07'
            complete_number = '%s%s%s%s' % (first_segment, self.emision_point_id.code, ebi_voucher_type_t, self.num_sequential)
            self.ebi_acceptance_number_doc = complete_number

    @api.one
    @api.depends('payment_method_ids')
    def _get_complete_name_payments(self):
        paym_nam = []
        if self.payment_method_ids:
           for paym in self.payment_method_ids:
               paym_nam.append(ustr(paym.name))
        self.complete_name_payments = ', '.join(paym_nam)

    comercial_name = fields.Char(string="Business Name", size=80, track_visibility='onchange')
    complete_name_payments = fields.Char(string="Business Name", compute=_get_complete_name_payments, track_visibility='onchange')
    edig_id = fields.Many2one('electronic.document.generic.cr', 'Electronic Doc.', select=True, track_visibility='onchange')
    sent_to_center = fields.Boolean('Sent to central', default=False, select=True, track_visibility='onchange')
    sent_to_provider = fields.Boolean('Send to Provider', default=False, select=True, track_visibility='onchange')
    ebi_state = fields.Selection(EBI_STATES, 'Estado del documento electronico', readonly=True, copy=False,
                                 default='to_check', track_visibility='onchange')
    ebi_send_date = fields.Datetime('Fecha Emision', readonly=True, copy=False, select=True, track_visibility='onchange')
    ebi_doc_mod_send_date = fields.Datetime('Fecha Emis. Doc. que mod.', readonly=False, copy=False, select=True, track_visibility='onchange')
    emission_hour = fields.Char('Emission Hour', select=True, track_visibility='onchange')
    ebi_last_check_date = fields.Datetime('Última comprobación', readonly=True, copy=False, select=True, track_visibility='onchange')
    ebi_access_key = fields.Char('Clave de acceso', readonly=True, copy=False, select=True, track_visibility='onchange')
    ebi_number_doc = fields.Char('Numero consecutivo factura', compute=_get_complete_number, track_visibility='onchange')
    ebi_acceptance_number_doc = fields.Char('Numero consecutivo Mensaje', compute=_get_complete_acceptance_number, track_visibility='onchange')
    #ebi_num_comp = fields.Integer('numeroComprobantes')
    ebi_auth_key = fields.Char('Número de Autorización', readonly=True, copy=False, select=True, track_visibility='onchange')
    ebi_auth_date = fields.Datetime('Fecha de Autorización', readonly=True, copy=False, select=True, track_visibility='onchange')
    ebi_environment = fields.Char('Ambiente', readonly=True, copy=False, select=True, track_visibility='onchange')
    #ebi_document = fields.Text('autorizaciones.autorizacion.comprobante')
    additional_info_ids = fields.One2many('ebi.additional.information', 'res_id', 'Informacion Adicional', domain=[('model_name', '=', 'account.invoice')], select=True)
    ebi_messages_ids = fields.One2many('ebi.doc.message', 'invoice_id', 'Mensajes')
    xml_file = fields.Text('FE XML', track_visibility='onchange')
    ebi_voucher_type = fields.Selection([
                             ('01','Electronic Customer Invoice'),
                             ('02','Electronic Debit Note'),
                             ('03', 'Electronic Credit Note'),
                             ('04','Electronic Ticket')], 'Voucher Type', default='01', select=True, track_visibility='onchange')

    ebi_ref_voucher_type = fields.Selection([
                                            ('01', 'Electronic Customer Invoice'),
                                            ('02', 'Electronic Debit Note'),
                                            ('03', 'Electronic Credit Note'),
                                            ('04', 'Electronic Ticket'),
                                            ('05', 'Nota de despacho'),
                                            ('06', 'Contrato'),
                                            ('07', 'Procedimiento'),
                                            ('08', 'Comprobante emitido en contigencia'),
                                            ('99', 'Otros'),], 'Ref Voucher Type', default='01', select=True, track_visibility='onchange')

    ebi_ref_voucher_code = fields.Selection([
                             ('01','Anula documento de referencia'),
                             ('02','Corrige texto de documento de referencia'),
                             ('03', 'Corrige monto'),
                             ('04','Referencia a otro documento'),
                             ('05','Sustituye comprobante provisional por contigencia'),
                             ('99','Otros'),], 'Ref Voucher Code', default='01', select=True, track_visibility='onchange')

    ebi_voucher_situation = fields.Selection([
                             ('1','Normal'),
                             ('2','Contingencia: sustituyen comprobante físico emitido por contingencia'),
                             ('3', 'Sin internet'),],
                            'Voucher Situation', default='1', select=True, track_visibility='onchange')

    ebi_confirmation_type = fields.Selection([
                            ('1', 'Aceptación Total'),
                            ('2', 'Aceptación Parcial'),
                            ('3', 'Rechazo'), ],
                            'Tipo de Mensaje de Confirmación', default='1', select=True, track_visibility='onchange')

    ebi_confirmation_message = fields.Text('Detalle del Mensaje de Confirmación', select=True, track_visibility='onchange')

    date_doc_mod = fields.Date('Date Doc. modify', select=True, track_visibility='onchange')
    reason_doc_mod = fields.Text('Reason Doc. modify', size=180, select=True, track_visibility='onchange')

    branch_office_id = fields.Many2one('branch.office', string="Branch Office", select=True, track_visibility='onchange')
    emision_point_id = fields.Many2one('emision.point', string="Emission Point", select=True, track_visibility='onchange')

    invoice_condition_ids = fields.Many2many('invoice.condition', 'invoice_condition_rel', 'invoice_id',
                                          'condition_id', string="Invoice Condition")
    invoice_condition_id = fields.Many2one('invoice.condition', string="Invoice Condition", select=True)
    invoice_condition_code = fields.Char(string="Invoice Condition Code", select=True)
    invoice_condition_other_name = fields.Char('Description', select=True)
    invoice_condition_other_code = fields.Char('Code', size=2, select=True)

    payment_method_ids = fields.Many2many('account.journal', 'invoice_payment_journal_rel', 'invoice_id',
                                          'method_id', 'Payment Methods', domain=[('type', 'in', ('bank', 'cash'))],) #default = get_default_paym_meth
    payment_method_id = fields.Many2one('account.invoice.payment.method', 'Payment Method', select=True)
    payment_method_code = fields.Char(string="Invoice Payment Method Code", select=True)
    payment_method_other_name = fields.Char('Description', size=512)
    payment_method_other_code = fields.Char('Code', size=2, select=True)

    num_sequential = fields.Char('Sequential', select=True, track_visibility='onchange')
    num_sequential_doc_mod = fields.Char('Num. Doc. modifies', size=50, select=True, track_visibility='onchange')
    plazo_cred = fields.Char('Credit Term', size=10, select=True)
    total_serv_grav = fields.Float('Total Servicios Gravados', compute=_amount_total_cr, track_visibility='onchange')
    total_serv_exentos = fields.Float('Total Servicios Exentos', compute=_amount_total_cr, track_visibility='onchange')
    total_merc_grav = fields.Float('Total Mercancias Gravadas', compute=_amount_total_cr, track_visibility='onchange')
    total_merc_exentas = fields.Float('Total Mercancias Exentas', compute=_amount_total_cr, track_visibility='onchange')
    total_gravado = fields.Float('Total Gravado', compute=_amount_total_cr, track_visibility='onchange')
    total_exento = fields.Float('Total Exento', compute=_amount_total_cr, track_visibility='onchange')
    total_venta = fields.Float('Total Venta', compute=_amount_total_cr, track_visibility='onchange')
    total_descuento = fields.Float('Total Descuentos', compute=_amount_total_cr, track_visibility='onchange')
    total_venta_net = fields.Float('Total Venta Net', compute=_amount_total_cr, track_visibility='onchange')
    total_impuesto = fields.Float('Total Impuesto', compute=_amount_total_cr, track_visibility='onchange')
    total_comprobante = fields.Float('Total Comprobante', compute=_amount_total_cr, track_visibility='onchange')

    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute=cr_compute_amount, track_visibility='onchange')
    refund_invoice_id = fields.Many2one('account.invoice', string="Origin Invoice", select=True, track_visibility='onchange')
    debit_note_invoice_id = fields.Many2one('account.invoice', string="Origin Invoice", select=True, track_visibility='onchange')
    identification_type = fields.Selection(docs_type, string="Identification Type", select=True, track_visibility='onchange')
    identification_cr = fields.Char(string="Identification", size=12, select=True, track_visibility='onchange')

    supplier_ebi_access_key = fields.Char('Clave de acceso', size=50, copy=False, select=True, track_visibility='onchange')
    supplier_reference = fields.Char(string='Nro de Factura', states={'draft': [('readonly', False)]})
    currency_fe_code = fields.Char(string='Código de Moneda', states={'draft': [('readonly', False)]})
    currency_fe_rate = fields.Float(string='Tipo de Cambio', states={'draft': [('readonly', False)]})
    has_electronic_emission = fields.Boolean('Es un comprobante Electrónico?', default=False,
                                             track_visibility='onchange')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', oldname='payment_term', help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. If you keep the payment term and the due date empty, it means direct payment. "
             "The payment term may compute several due dates, for example 50% now, 50% in one month.", readonly=False)

    @api.multi
    def name_get(self):
        res = []
        for invoice in self:
            name = invoice.number
            if self.env.context.get('invoice_mod_ref', False):
                name = invoice.number + " / " + invoice.date_invoice + " / " + invoice.num_sequential
            res.append((invoice.id, name))
        return res

    @api.multi
    @api.constrains('identification_cr')
    def _check_identification_rule(self):
        def is_number_cr(s):
            try:
                float(s)
                return True
            except ValueError:
                return False

        for invoice in self:
            if invoice.identification_type and invoice.identification_cr:
                if invoice.identification_type != '100':
                    if len(invoice.identification_cr) > 12:
                        raise Warning('Invalid identification.')


                    if not is_number_cr(invoice.identification_cr):
                        raise Warning('Invalid identification.')

                    if invoice.identification_type == '01':
                        if len(invoice.identification_cr) > 9:
                            raise Warning('Cedula Fisica Invalida.')
                        numcc = invoice.identification_cr
                        firts_one = numcc[0:1]
                        if int(firts_one) == 0:
                            raise Warning('Cedula Fisica Invalida.')
                        #
                        # cedula_01 = cedula_01_validation(invoice.identification_cr)
                        # if not cedula_01:
                        #     raise Warning('Cedula Fisica Invalida.')

                    if invoice.identification_type == '02':
                        if len(invoice.identification_cr) > 10:
                            raise Warning('Cedula Juridica Invalida.')
                        #
                        # cedula_02 = cedula_02_validation(invoice.identification_cr)
                        # if not cedula_02:
                        #     raise Warning('Cedula Juridica Invalida.')

                    if invoice.identification_type == '03':
                        if len(invoice.identification_cr) > 12:
                            raise Warning('DIMEX Invalido.')
                        numcc = invoice.identification_cr
                        firts_one = numcc[0:1]
                        if int(firts_one) == 0:
                            raise Warning('DIMEX Invalido.')
                        #
                        # dimex_res = dimex_validation(invoice.identification_cr)
                        # if not dimex_res:
                        #     raise Warning('DIMEX Invalido.')

                    if invoice.identification_type == '04':
                        if len(invoice.identification_cr) > 10:
                            raise Warning('NITE Invalido.')

                        # nite_res = nite_validation(invoice.identification_cr)
                        # if not nite_res:
                        #     raise Warning('NITE Invalido.')

    @api.multi
    @api.constrains('ebi_voucher_type')
    def _check_ebi_voucher_type(self):
        for invoice in self:
            if invoice.type == 'out_invoice':
                if invoice.ebi_voucher_type not in ['01', '02', '04']:
                    raise Warning('Invalid Voucher Type for Sale Invoice.')
            if invoice.type == 'out_refund':
                if invoice.ebi_voucher_type not in ['03']:
                    raise Warning('Invalid Voucher Type for Sale Invoice Refund.')

            if invoice.type == 'in_invoice':
                if invoice.ebi_voucher_type in ['03']:
                    raise Warning('Tipo de Comprobate incorrecto para Factura de Proveedor.')
            if invoice.type == 'in_refund':
                if invoice.ebi_voucher_type not in ['03']:
                    raise Warning(u'Tipo de Comprobate incorrecto, solo puede seleccionar Nota de Crédito.')

    @api.multi
    @api.constrains('payment_method_ids')
    def _check_payment_method_ids(self):
        for invoice in self:
            if invoice.payment_method_ids:
                if len(invoice.payment_method_ids) > 4:
                    raise Warning('Solo puede poner hasta 4 metodos de pago.')

    @api.multi
    @api.constrains('supplier_ebi_access_key')
    def _check_supplier_ebi_access_key(self):
        for invoice in self:
            if invoice.type in ['in_invoice', 'in_refund']:
                if self.has_electronic_emission:
                    if len(invoice.supplier_ebi_access_key) < 50:
                        raise Warning('Solo puede poner 50 caracteres en el campo Clave de Acceso.')

    # @api.model
    # def _refund_cleanup_lines(self, lines):
    #     result = super(AccountInvoice, self)._refund_cleanup_lines(lines)
    #     if not result:
    #         result = []
    #     for line in result:
    #         if line[2]:
    #             if lines[0].invoice_id.type == 'out_invoice':
    #                 if line[2].get('discount', False):
    #                     line[2]['discount'] = 0.0
    #                     line[2]['naturaleza_descuento'] = ''
    #     return result

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        values = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice=date_invoice, date=date, description=description, journal_id=journal_id)
        if not values:
            values = {}

        if invoice.ebi_state not in ['send', 'auth', 'noauth'] or not invoice.ebi_send_date:
            if invoice.type in ['out_refund', 'out_invoice']:
                raise EbiError(u'La factura origen debe ser enviada electrónicamente.')

        values.update({
            'date_doc_mod': invoice.date_invoice,
            'ebi_doc_mod_send_date': invoice.ebi_send_date,
            'refund_invoice_id': invoice.id,
            'ebi_voucher_type': '03',
            'ebi_ref_voucher_type': '01',
            'ebi_ref_voucher_code': '01',
            'identification_type': invoice.identification_type or invoice.partner_id.identification_type,
            'identification_cr': invoice.identification_cr or invoice.partner_id.identification_cr,
            'reason_doc_mod': values.get('name', ''),
            'comercial_name': invoice.comercial_name,
            'emision_point_id': invoice.emision_point_id.id,
            'branch_office_id': invoice.branch_office_id.id if invoice.branch_office_id else False,
            'invoice_condition_id': invoice.invoice_condition_id.id,
            'plazo_cred': invoice.plazo_cred,
            'payment_method_id': invoice.payment_method_id.id,
            'payment_term_id': invoice.payment_term_id.id or False,
        })

        if not invoice.emision_point_id:
            raise EbiError(u'La factura origen debe estar asociada a un tpv en la compañía.')

        if not invoice.num_sequential:
            if invoice.type in ['out_refund', 'out_invoice']:
                raise EbiError(u'La factura origen debe tener asignado un secuencial.')

        if invoice.emision_point_id and invoice.num_sequential:
            first_segment = invoice.company_id.establishment_code
            if invoice.branch_office_id:
                first_segment = invoice.branch_office_id.code
            complete_number = '%s-%s-%s-%s' % (first_segment, invoice.emision_point_id.code, invoice.ebi_voucher_type, invoice.num_sequential)
            if not complete_number:
                if invoice.type in ['out_refund', 'out_invoice']:
                    raise EbiError(u'La factura origen debe ser enviada electrónicamente.')
            values.update({
                'origin': 'Factura #%s (%s)' % (complete_number or 'S/N', invoice.id),
                'num_sequential_doc_mod': complete_number,
            })

        return values

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        super(AccountInvoice, self)._onchange_partner_id()
        if self.partner_id:
            self.identification_type = self.partner_id.identification_type
            self.identification_cr = self.partner_id.identification_cr
            self.comercial_name = self.partner_id.comercial_name or self.partner_id.name
        if self.company_id:
            branch_office_ids = [aux for aux in self.company_id.branch_office_ids if aux.active]
            if branch_office_ids:
                self.branch_office_id = branch_office_ids[0].id if branch_office_ids else False

                branch_office_tmp = branch_office_ids[0].id if branch_office_ids else False
                point = [aux_p for aux_p in self.company_id.emision_points if
                         aux_p.active and aux_p.branch_office_id.id == branch_office_tmp]
                if point:
                    self.emision_point_id = point[0].id if point else False
            else:
                point = [aux for aux in self.env.user.company_id.emision_points if aux.active]
                if point:
                    self.emision_point_id = point[0].id if point else False

    @api.onchange('ebi_voucher_type')
    def onchange_ebi_voucher_type(self):
        #verify if invoice != debit note
        if self.ebi_voucher_type != '02':
            self.debit_note_invoice_id = False
        if self.emision_point_id and self.type == 'out_invoice' and self.ebi_voucher_type == '02':
            if self.debit_note_invoice_id:
                self.date_doc_mod = self.debit_note_invoice_id.date_invoice
                self.ebi_doc_mod_send_date = self.debit_note_invoice_id.ebi_send_date
                if self.debit_note_invoice_id.emision_point_id and self.debit_note_invoice_id.num_sequential:
                    first_segment = self.debit_note_invoice_id.company_id.establishment_code
                    if self.debit_note_invoice_id.branch_office_id:
                        first_segment = self.debit_note_invoice_id.branch_office_id.code
                    complete_number = '%s-%s-%s-%s' % (first_segment, self.debit_note_invoice_id.emision_point_id.code, self.debit_note_invoice_id.ebi_voucher_type, self.debit_note_invoice_id.num_sequential)
                    # complete_number = '%s-%s-%s' % (self.debit_note_invoice_id.company_id.establishment_code, self.debit_note_invoice_id.emision_point_id.code, self.debit_note_invoice_id.num_sequential)
                    self.origin = 'Factura #%s (%s)' % (complete_number or 'S/N', self.debit_note_invoice_id.id)
                    self.num_sequential_doc_mod = complete_number

    @api.onchange('debit_note_invoice_id')
    def onchange_debit_note_invoice_id(self):
        self.onchange_ebi_voucher_type()

    @api.onchange('invoice_condition_id')
    def onchange_invoice_condition_id(self):
        self.invoice_condition_code = ''
        if self.invoice_condition_id:
            self.invoice_condition_code = self.invoice_condition_id.code

    @api.onchange('payment_method_id')
    def onchange_payment_method_id(self):
        self.payment_method_code = ''
        if self.payment_method_id:
            self.payment_method_code = self.payment_method_id.code
            if self.payment_method_id.code == '02':
                self.plazo_cred = self.payment_term_id.name

    @api.onchange('payment_term_id', 'date_invoice')
    def _onchange_payment_term_date_invoice(self):
        super(AccountInvoice, self)._onchange_payment_term_date_invoice()
        if self.payment_term_id:
            if self.invoice_condition_code == '02':
                self.plazo_cred = self.payment_term_id.name

    @api.onchange('ebi_confirmation_type')
    def _onchange_ebi_confirmation_type(self):
        self.ebi_confirmation_message = ''
        if self.ebi_confirmation_type:
            if self.ebi_confirmation_type == '1':
                self.ebi_confirmation_message = 'Aceptación Total'
            if self.ebi_confirmation_type == '2':
                self.ebi_confirmation_message = 'Aceptación Parcial'
            if self.ebi_confirmation_type == '3':
                self.ebi_confirmation_message = 'Rechazo'

    @api.one
    def btn_ebi_draft(self):
        if self.ebi_state not in ['send', 'draft']:
            raise EbiError(u'La factura que intenta enviar a borrador debe estar enviada/No enviada.')
        self.write({
            'ebi_state': 'to_check',
            'ebi_send_date': False,
            'ebi_access_key': False,
            'ebi_auth_key': False,
            'ebi_auth_date': False,
            'ebi_environment': False,
            'xml_file': False,
        })

        self.edig_id.write({
            'date': False,
            'mh_access_key': False,
            'raw_xml': False,
            'signed_xml': False,
            'ebi_state': 'to_check',
        })

    @api.multi
    def btn_ebi_send(self):
        if self.state not in ('open', 'paid'):
            raise EbiError('La factura que intenta emitir electrónicamente debe estar validada.')
        if self.ebi_state != 'draft':
            raise EbiError('La factura que intenta emitir electrónicamente ya ha sido emitida, compruebe el estado de la misma.')
        supplier = self.company_id.ebiller_id
        if not supplier:
            action = self.env.ref('multi_ebilling_base.action_ebiller')
            raise RedirectWarning(u'No se ha configurado un proveedor de facturación electrónica', action.id, u'Ir al panel de configuración')
        self.check_date()
        # self.check_before_sent()
        send_res = supplier.send_signed_xml(self.edig_id, raise_error=False)
        if self.ebi_state != 'auth':
            self.write({
                'ebi_state': 'send',
                # 'ebi_send_date': fields.Datetime.now(),
                'ebi_environment': "PRUEBAS" if supplier.environment == 'test' else 'PROD'
            })
            self.edig_id.write({
                'ebi_state': 'send',
            })
        else:
            self.btn_ebi_send_mail()

        self.write({
            'ebi_environment': "PRUEBAS" if supplier.environment == 'test' else 'PROD'
        })

        if type(send_res) is dict:
            return send_res

    @api.multi
    def btn_ebi_re_send(self):
        if self.state not in ('open', 'paid'):
            raise EbiError('La factura que intenta emitir electrónicamente debe estar validada.')
        # if self.ebi_state != 'draft':
        #     raise EbiError('La factura que intenta emitir electrónicamente ya ha sido emitida, compruebe el estado de la misma.')
        supplier = self.company_id.ebiller_id
        if not supplier:
            action = self.env.ref('multi_ebilling_base.action_ebiller')
            raise RedirectWarning(u'No se ha configurado un proveedor de facturación electrónica', action.id, u'Ir al panel de configuración')
        self.check_date()
        # self.check_before_sent()
        res_re_send = self.edig_id.verify_document_its_self()
        if self.ebi_state != 'auth':
            self.write({
                'ebi_state': 'send',
                'ebi_send_date': fields.Datetime.now(),
                'ebi_environment': "PRUEBAS" if supplier.environment == 'test' else 'PROD'
            })

            self.edig_id.write({
                'ebi_state': 'send',
            })

        self.write({
            'ebi_environment': "PRUEBAS" if supplier.environment == 'test' else 'PROD'
        })

        if res_re_send:
            res_re_send = res_re_send[0]
            if type(res_re_send) is dict:
                print "si aqui devolvio"
                return dict(res_re_send)

#   Validar el documento electronico

    @api.multi
    def btn_ebi_check(self):
        if self.state not in ('open', 'paid'):
            raise EbiError(u'La factura que intenta comprobar electrónicamente debe estar validada.')
        supplier = self.company_id.ebiller_id
        if not supplier:
            action = self.env.ref('medical_ebilling_cr.action_ebiller')
            raise RedirectWarning(u'No se ha configurado un proveedor de facturación electrónica', action.id,
                                  u'Ir al panel de configuración')
        if not self.edig_id:
            ctx = self.env.context.copy()
            if self.type in ['out_refund', 'out_invoice']:
                if self.ebi_voucher_type == 02:
                    ctx.update({'document_type_process': 'debit_out_refund'})
            self.with_context(ctx).action_electronic_send()

        if self.edig_id:
            self.write({'currency_fe_code': self.currency_id.name, 'currency_fe_rate': self.currency_id.rate})
            ebi_voucher_type_t = self.ebi_voucher_type
            if self.type in ['in_invoice', 'in_refund']:
                if self.ebi_confirmation_type == '1':
                    ebi_voucher_type_t = '09'
                if self.ebi_confirmation_type == '2':
                    ebi_voucher_type_t = '10'
                if self.ebi_confirmation_type == '3':
                    ebi_voucher_type_t = '11'
            self.edig_id.write({'date': fields.Datetime.now(), 'mh_sequence': self.num_sequential,
                                'mh_complete_number': self.get_complete_number()[0],
                                'type': ebi_voucher_type_t,
                                'company_vat': self.company_id.partner_id.identification_cr})
            self.check_date()
            # self.check_before_sent()
            self.edig_id.build_access_key()
            self.edig_id.build_document()
            validate_res = self.edig_id.validate_xml()
            self.write({
                'ebi_last_check_date': fields.Datetime.now()
            })
            if type(validate_res) is dict:
                self.write({'ebi_state': 'to_check'})
                self.edig_id.write({'ebi_state': 'to_check'})
                return validate_res
            else:
                self.write({'ebi_state': 'draft'})
                self.edig_id.write({'ebi_state': 'draft'})
        return True

    @api.multi
    def btn_ebi_all_operations(self):
        if self.state not in ('open', 'paid'):
            raise EbiError(u'La factura que intenta comprobar electrónicamente debe estar validada.')
        supplier = self.company_id.ebiller_id
        if not supplier:
            action = self.env.ref('medical_ebilling_cr.action_ebiller')
            raise RedirectWarning(u'No se ha configurado un proveedor de facturación electrónica', action.id,
                                  u'Ir al panel de configuración')
        if not self.edig_id:
            ctx = self.env.context.copy()
            if self.type in ['out_refund', 'out_invoice']:
                if self.ebi_voucher_type == 02:
                    ctx.update({'document_type_process': 'debit_out_refund'})
            self.with_context(ctx).action_electronic_send()

        if self.edig_id:
            ebi_voucher_type_t = self.ebi_voucher_type
            if self.type in ['in_invoice', 'in_refund']:
                if self.ebi_confirmation_type == '1':
                    ebi_voucher_type_t = '09'
                if self.ebi_confirmation_type == '2':
                    ebi_voucher_type_t = '10'
                if self.ebi_confirmation_type == '3':
                    ebi_voucher_type_t = '11'
            self.edig_id.write({'date': fields.Datetime.now(), 'mh_sequence': self.num_sequential,
                                'mh_complete_number': self.get_complete_number()[0],
                                'type': ebi_voucher_type_t,
                                'company_vat': self.company_id.partner_id.identification_cr})
            self.check_date()
            # self.check_before_sent()
            self.edig_id.build_access_key()
            self.edig_id.build_document()
            validate_res = self.edig_id.validate_xml()
            self.write({
                'ebi_last_check_date': fields.Datetime.now()
            })
            if type(validate_res) is dict:
                self.write({'ebi_state': 'to_check'})
                self.edig_id.write({'ebi_state': 'to_check'})
                return validate_res
            else:
                self.write({'ebi_state': 'draft'})
                self.edig_id.write({'ebi_state': 'draft'})

            res_send = self.btn_ebi_send()
            if type(res_send) is dict:
                return res_send

    @api.multi
    def btn_ebi_send_mail(self):
        if self.state not in ('open', 'paid'):
            raise EbiError(u'La factura que intenta enviar debe estar validada.')
        if self.ebi_state != 'auth':
            raise EbiError(u'La factura que intenta enviar debe constar como autorizada.')
        supplier = self.company_id.ebiller_id
        if not supplier:
            action = self.env.ref('medical_ebilling_cr.action_ebiller')
            raise RedirectWarning(u'No se ha configurado un proveedor de facturación electrónica', action.id, u'Ir al panel de configuración')

        return self.edig_id.btn_send_mail()

    @api.one
    def btn_ebi_cancel(self):
        if self.state not in ('open', 'paid'):
            raise EbiError(u'La factura que intenta anular electrónicamente debe estar validada.')
        if self.ebi_state != 'auth':
            raise EbiError(u'La factura que intenta anular electrónicamente debe constar como autorizada.')
        e_supplier = self.company_id.ebiller_id
        if not e_supplier:
            action = self.env.ref('solt_ebilling_base.action_ebiller')
            raise RedirectWarning(u'No se ha configurado un proveedor de facturación electrónica', action.id,
                                  u'Ir al panel de configuración')
        e_supplier.cancel_document(self)

    @api.multi
    def action_move_create(self):
        count = 1
        for inv in self:
            if inv.type in ('in_invoice', 'in_refund') and inv.supplier_reference:
                if self.search([('type', '=', inv.type), ('ebi_voucher_type', '=', inv.ebi_voucher_type), ('supplier_reference', '=', inv.supplier_reference), ('company_id', '=', inv.company_id.id), ('commercial_partner_id', '=', inv.commercial_partner_id.id), ('id', '!=', inv.id)]):
                    raise ValidationError(_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/refund."))

            if not inv.journal_id.sequence_id:
                raise ValidationError(_('Please define sequence on the journal related to this invoice.'))

            if not inv.invoice_line_ids:
                raise ValidationError(_('No Invoice Lines!, Please create some invoice lines.'))

            if inv.amount_total == 0.0:
                raise ValidationError(_("You cant open invoice with total amount equal to zero!"))

            if not inv.total_comprobante:
                raise ValidationError(_(u'Debe llevar impuestos las líneas de la factura.'))

            for inv_line in inv.invoice_line_ids:
                if inv_line.price_subtotal == 0.0:
                    raise ValidationError(_("You cant open invoice with total amount equal to zero in some line!"))

            # for inv_line in inv.invoice_line_ids:
            #     inv_line.write({'num_consecutive': count})
            #     count += count

        res = super(AccountInvoice, self).action_move_create()

        for inv in self:
            tipo_factura = inv.ebi_voucher_type
            vals_inv = {}
            if inv.amount_total != 0:
                if inv.type == 'out_invoice':
                    if inv.emision_point_id:
                        if tipo_factura == '01':
                            if inv.emision_point_id.invoice_sequence_id:
                                if not inv.num_sequential:
                                    vals_inv['num_sequential'] = inv.emision_point_id.invoice_sequence_id._next()
                        if tipo_factura == '02':
                            if inv.emision_point_id.debit_note_sequence_id:
                                if not inv.num_sequential:
                                    vals_inv['num_sequential'] = inv.emision_point_id.debit_note_sequence_id._next()
                        if tipo_factura == '04':
                            if inv.emision_point_id.electronic_ticket_sequence_id:
                                if not inv.num_sequential:
                                    vals_inv['num_sequential'] = inv.emision_point_id.electronic_ticket_sequence_id._next()
                if inv.type == 'out_refund':
                    if inv.emision_point_id:
                        if inv.emision_point_id.refund_sequence_id:
                            if not inv.num_sequential:
                                vals_inv['num_sequential'] = inv.emision_point_id.refund_sequence_id._next()

                if inv.type in ['in_invoice', 'in_refund']:
                    if self.has_electronic_emission:
                        if inv.emision_point_id:
                            if inv.emision_point_id.acceptance_confirmation_sequence_id:
                                if not inv.num_sequential:
                                    vals_inv['num_sequential'] = inv.emision_point_id.acceptance_confirmation_sequence_id._next()
            vals_inv.update({'currency_fe_code': inv.currency_id.name, 'currency_fe_rate': inv.currency_id.rate})
            print "valores de la factura", vals_inv
            if vals_inv:
                inv.write(vals_inv)
        return res

    @api.multi
    def check_date(self):
        date_invoice_c = self.date_invoice
        LIMIT_TO_SEND = 8
        NOT_SENT = u'Error de Envío'
        MESSAGE_TIME_LIMIT = u' '.join([
            u'Los comprobantes electrónicos deben',
            u'enviarse con máximo %s días desde su emisión.' % LIMIT_TO_SEND]
        )
        dt = datetime.datetime.strptime(date_invoice_c, '%Y-%m-%d')
        days = (datetime.datetime.now() - dt).days
        if days > LIMIT_TO_SEND:
            raise ValidationError(NOT_SENT + ', ' +  MESSAGE_TIME_LIMIT)

    @api.multi
    def invoice_validate(self):
        for inv in self:
            if not inv.journal_id.sequence_id:
                raise ValidationError(_('Please define sequence on the journal related to this invoice.'))

            if not inv.emision_point_id:
                valid_p_m = False
                if self.has_electronic_emission:
                    valid_p_m = True
                if self.type in ['out_invoice', 'out_refund']:
                    valid_p_m = True
                if valid_p_m:
                    raise ValidationError(_('Por favor definir el terminal de punto de venta para la empresa.'))

            if not inv.invoice_line_ids:
                raise ValidationError(_('No Invoice Lines!, Please create some invoice lines.'))

            if inv.amount_total == 0.0:
                raise ValidationError(_("You cant open invoice with total amount equal to zero!"))

            for inv_line in inv.invoice_line_ids:
                if inv_line.price_subtotal == 0.0:
                    raise ValidationError(_("You cant open invoice with total amount equal to zero in some line!"))

        return super(AccountInvoice, self).invoice_validate()

    @api.one
    def get_complete_number(self):
        complete_number = 'S/N'
        if self.emision_point_id:
            if self.emision_point_id and self.num_sequential:
                first_segment = self.company_id.establishment_code
                if self.branch_office_id:
                    first_segment = self.branch_office_id.code
                complete_number = '%s%s%s%s' % (
                    first_segment, self.emision_point_id.code,
                    self.ebi_voucher_type, self.num_sequential)
        return complete_number

    @api.multi
    def action_electronic_send(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        if self.type in ['out_refund', 'out_invoice']:
            if self.ebi_voucher_type == 02:
                ctx.update({'document_type_process': 'debit_out_refund'})

        obj_name = self._name
        vals_edi = {}
        if not self.edig_id and self.amount_total and self.state not in ['draft', 'cancel']:
            if self.company_id:
                if self.company_id.ebiller_id:
                    vals_edi['name'] = self.number
                    vals_edi['origin'] = 'center'
                    vals_edi['type'] = self.ebi_voucher_type
                    if self.type in ['in_invoice', 'in_refund']:
                        if self.ebi_confirmation_type == '1':
                            vals_edi['type'] = '09'
                        if self.ebi_confirmation_type == '2':
                            vals_edi['type'] = '10'
                        if self.ebi_confirmation_type == '3':
                            vals_edi['type'] = '11'
                    vals_edi['mh_sequence'] = self.num_sequential
                    vals_edi['ebi_voucher_situation'] = self.ebi_voucher_situation
                    vals_edi['email'] = self.partner_id.email
                    vals_edi['customer_vat'] = self.partner_id.identification_cr
                    vals_edi['customer_name'] = ustr(self.partner_id.name)
                    vals_edi['company_vat'] = self.company_id.partner_id.identification_cr
                    vals_edi['company_name'] = ustr(self.company_id.name)
                    vals_edi['invoice_remote_id'] = self.id
                    vals_edi['date'] = fields.Datetime.now()
                    base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                    vals_edi['instance'] = base_url
                    vals_edi['obj_model'] = obj_name
                    vals_edi['obj_id'] = self.id
                    vals_edi['external_db'] = self._cr.dbname
                    #vals_edi['external_queue'] = RabbitMQClient(self).get_queue_name()
                    edi_data_dict = self.env['electronic.document.generic.cr'].get_document_data_obj(self)
                    edi_data = simplejson.dumps(edi_data_dict)
                    vals_edi['edi_data'] = edi_data
                    dbuuid = self.env['ir.config_parameter'].get_param('database.uuid')
                    vals_edi['edi_uuid'] = vals_edi['external_db'] + '-' + str(self.id) + '-' + dbuuid.upper()
                    vals_edi['origin'] = 'shop'
                    vals_edi['ebiller_id'] = self.company_id.ebiller_id.id
                    vals_edi['invoice_remote_id'] = False
                    vals_edi['invoice_id'] = self.id
                    vals_edi['instance'] = False
                    vals_edi['external_db'] = False
                    vals_edi['external_queue'] = False
                    vals_edi['partner_id'] = self.partner_id.id
                    complete_number = self.get_complete_number()[0]
                    vals_edi['mh_complete_number'] = complete_number
                    vals_edi['type'] = self.ebi_voucher_type
                    if self.type in ['in_invoice', 'in_refund']:
                        if self.ebi_confirmation_type == '1':
                            vals_edi['type'] = '09'
                        if self.ebi_confirmation_type == '2':
                            vals_edi['type'] = '10'
                        if self.ebi_confirmation_type == '3':
                            vals_edi['type'] = '11'
                    # print "data edi ", vals_edi
                    edig_id = self.env['electronic.document.generic.cr'].create(vals_edi)
                    vals_w_invoice = {'edig_id': edig_id.id}
                    self.write(vals_w_invoice)
                else:
                    raise ValidationError(_('The company has not biller config.'))

        if self.edig_id:
            self.edig_id.build_access_key()
            # self.edig_id.build_document()
            first_message_title = "Comprobante Generado"
            first_message_msg = "El Comprobante Electronico ha sido Generado"
            state = 'Generado'
            access_key = self.ebi_access_key
            res_id = self.id
            model_name = self._name
            sequence_msg = len(self.ebi_messages_ids) + 1
            message_data = {
                'title': first_message_title,
                'message': first_message_msg,
                'state': state,
                'access_key': access_key,
                'res_id': res_id,
                'model_name': model_name,
                'type': 'interno',
                'sequence': sequence_msg,
                'edig_id': self.edig_id.id,
                'invoice_id': self.id,
            }
            self.message_post(body=first_message_msg)
            self.env['ebi.doc.message'].create(message_data)

    @api.multi
    def register_payment(self, payment_line, writeoff_acc_id=False, writeoff_journal_id=False):
        res = super(AccountInvoice, self).register_payment(payment_line, writeoff_acc_id=writeoff_acc_id, writeoff_journal_id=writeoff_journal_id)
        move = False
        if payment_line:
            move = payment_line.move_id
        if move:
            for inv in self:
                if move.journal_id.id not in inv.payment_method_ids.ids:
                    inv.write({'payment_method_ids': [(4, move.journal_id.id)]})
        return res

class tax_exoneration_type(models.Model):
    _name = 'tax.exoneration.type'
    _description = 'Tax Exoneration Type'

    name = fields.Char('Name', required=True, select=True)
    code = fields.Char('Code', size=2, required=True, select=True)

class AccountInvoiceNatureDiscount(models.Model):
    _name = 'account.invoice.nature.discount'
    _description = 'Invoice Nature Discount'

    name = fields.Char('Description', size=80, required=True)
    code = fields.Char('Code', size=2)
    active = fields.Boolean('Active', default=True)

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.one
    @api.depends('price_subtotal', 'invoice_line_tax_ids', 'invoice_line_tax_ids.amount', 'invoice_id')
    def _cr_compute_amount_line(self):
        subtotal_partial = self.price_subtotal
        amount_tax = 0.0
        if self.invoice_line_tax_ids:
            currency = self.invoice_id and self.invoice_id.currency_id or None
            price = self.price_subtotal
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, 1)
            for tax_c in taxes['taxes']:
                # print "impuestos de linea ", tax_c
                tax = self.env['account.tax'].browse(tax_c['id'])
                if tax.cr_group_tax_use == 'vat':
                    amount_tax += tax_c['amount']
        self.cr_amount_total_line = subtotal_partial + amount_tax

    @api.one
    @api.depends('invoice_id')
    def _compute_number_line(self):
        index_line = 1
        if self.invoice_id:
            if self.invoice_id.invoice_line_ids:
                index_lines = [xl.id for xl in self.invoice_id.invoice_line_ids]
                index_lines.sort()
                index_line = index_lines.index(self.id) + 1
        self.num_consecutive = index_line

    nature_discount_id = fields.Many2one('account.invoice.nature.discount', string="Naturaleza Descuento")
    naturaleza_descuento = fields.Char('Naturaleza Descuento')
    cr_amount_total_line = fields.Monetary(string='Total', compute='_cr_compute_amount_line')
    line_discount_amount = fields.Float(digits=(16, 2), compute='_compute_line_discount_amount')
    num_consecutive = fields.Integer('numeroconsecutivo', compute='_compute_number_line')

    @api.multi
    @api.constrains('nature_discount_id', 'discount')
    def _check_nature_discount_id(self):
        for line in self:
            if line.nature_discount_id and not line.discount:
                raise Warning('Defina el porcentaje de descuento.')

            if not line.nature_discount_id and line.discount:
                raise Warning('Defina la naturaleza del descuento.')

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
                 'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id')
    def _compute_line_discount_amount(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * ((self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id,
                                                          partner=self.invoice_id.partner_id)
        self.line_discount_amount = taxes['total_excluded'] if taxes else self.quantity * price

    @api.onchange('nature_discount_id')
    def onchange_nature_discount_id(self):
        if self.nature_discount_id:
            self.naturaleza_descuento = self.nature_discount_id.code

    @api.multi
    def fe_get_taxes(self):
        group = {}
        for invoice_tax in self.invoice_line_tax_ids:
            currency = self.invoice_id and self.invoice_id.currency_id or None
            price = self.price_subtotal
            taxes = invoice_tax.compute_all(price, currency, 1)
            tax_m = 0.0
            for tax_c in taxes['taxes']:
                tax_m += tax_c['amount']

            tax_id = invoice_tax
            key = tax_id.tax_group_id.fe_tax_code
            group[key] = group.get(key, {
                'code': tax_id.tax_group_id.fe_tax_code,
                'amount_tax': group.get(key, {}).get('amount_tax', 0.0) + tax_m,
                'amount': group.get(key, {}).get('amount', 0.0) + invoice_tax.amount,
            })

        return group.itervalues()

class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    exoneration_id = fields.Many2one('account.tax.exoneration.type', string="Exoneration Type")
    num_doc_exoneration = fields.Char(string="Num. Doc. Exoneration", size=17)
    company_exoneration = fields.Char(string="Company Exoneration", size=100)
    date_doc_exoneration = fields.Datetime('Date Doc. Exoneration')
    amount_exoneration = fields.Float('Amount Exoneration')
    percent_exoneration = fields.Float('Percent Exoneration')