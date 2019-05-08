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
from datetime import datetime, timedelta
import threading
from openerp.http import serialize_exception
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, ustr
from openerp.exceptions import ValidationError, UserError, RedirectWarning
import simplejson
import time
import base64
from mako.template import Template
import logging
from lxml import etree
from subprocess import *
from StringIO import StringIO
import os
import re
from openerp.tools import config
import subprocess
from pytz import timezone
import random

type_errors = [
    ('message', 'Mensaje'), ('error', 'Error'), ('interno', 'Interno'), ('mh', 'MH')
]

import pprint
_logger = logging.getLogger(__name__)

def mod11(chain):
    multiply = 2
    total = 0
    for c in reversed(chain):
        total += int(c) * multiply
        multiply += 1
        if multiply > 7:
            multiply = 2
    result = 11 - total % 11
    return result < 10 and result or 11 - result

TEMPLATES = {
    'account.invoice.out_invoice.01': 'invoice_template',
    'account.invoice.out_invoice.02': 'debit_note_template',
    'account.invoice.out_refund.03': 'refund_template',
    'account.invoice.out_invoice.04': 'electronic_ticket_template',
    'account.invoice.in_invoice.01': 'accuse_acceptance_template',
    'account.invoice.in_invoice.02': 'accuse_acceptance_template',
    'account.invoice.in_refund.03': 'accuse_acceptance_template',
    'account.invoice.in_invoice.04': 'accuse_acceptance_template',
}

SCHEMAS = {
    '01': 'schemas/factura.xsd',
    '02': 'schemas/nota_debito.xsd',
    '03': 'schemas/nota_credito.xsd',
    '04': 'schemas/tiquete.xsd',
    '100000': 'schemas/mensajereceptor.xsd',
}

EBI_STATES = [
    ('to_check', 'Borrador'), ('draft', 'No enviado'), ('send', 'Enviado'), ('auth', 'Autorizado'),
    ('noauth', 'No autorizado'), ('cancel', 'Anulado')
]

class error_fe_p(object):
    message = ''
    column_ref = ''
    value_ref = ''
    documents = []

    def __init__(self, message_p, column_ref_p, value_ref_p, documents_p):
        self.message = message_p
        self.column_ref = column_ref_p
        self.value_ref = value_ref_p
        self.documents = documents_p

class electronic_document_generic_cr(models.Model):
    _name = 'electronic.document.generic.cr'
    _inherit = ['mail.thread']
    _description = "Electronic Document"
    _lock = threading.RLock()

    @api.one
    @api.depends('type')
    def _compute_type_name(self):
        self.document_type_name = 'Factura Electrónica'
        if self.type:
            if self.type == '01':
                self.document_type_name = 'Factura Electrónica'
            if self.type == '03':
                self.document_type_name = 'Nota de Crédito'
            if self.type == '02':
                self.document_type_name = 'Nota de Débito'
            if self.type == '04':
                self.document_type_name = 'Tiquete Electrónico'
            if self.type == '09':
                self.document_type_name = 'Aceptación del Comprobante Electrónico'
            if self.type == '10':
                self.document_type_name = 'Aceptación Parcial del Comprobante Electrónico'
            if self.type == '11':
                self.document_type_name = 'Rechazo del Comprobante Electrónico'

    @api.one
    @api.depends('create_date', 'date_accepted')
    def _compute_days_for_acceptance(self):
        if self.its_trial:
            date_create_t = fields.Datetime.from_string(self.create_date)
            date_accepted_t = False
            if self.date_accepted:
                date_accepted_t = fields.Datetime.from_string(self.date_accepted)
            if not date_accepted_t:
                date_now = fields.Datetime.now()
                self.days_for_acceptance = abs((datetime.now() - date_create_t).days)
            else:
                self.days_for_acceptance = abs((date_accepted_t - date_create_t).days)

    name = fields.Char('Name', track_visibility='onchange')
    ebi_state = fields.Selection(EBI_STATES, 'Estado del documento electronico', readonly=True, copy=False,
                                 default='to_check')
    version = fields.Char('Version', track_visibility='onchange')
    current_regulation = fields.Text('Current Regulations', track_visibility='onchange')
    ebi_access_key = fields.Char('Clave de acceso', readonly=True, copy=False, select=True, track_visibility='onchange')
    ebi_number_doc = fields.Char('Numero de documento', readonly=True, copy=False, select=True, track_visibility='onchange')
    type = fields.Selection([('01', 'Electronic Customer Invoice'),
                             ('02', 'Electronic Debit Note'),
                             ('03', 'Electronic Credit Note'),
                             ('04', 'Electronic Ticket'),
                             ('05', 'Nota de despacho'),
                             ('06', 'Contrato'),
                             ('07', 'Procedimiento'),
                             ('08', 'Comprobante emitido en contigencia'),
                             ('99', 'Otros'),
                             ('09', 'Aceptación del Comprobante Electrónico'),
                             ('10', 'Aceptación Parcial del Comprobante Electrónico'),
                             ('11','Rechazo del Comprobante Electrónico')], string='Type', index=True, track_visibility='onchange')
    origin = fields.Selection([('shop','Shop'), ('center','Center')], string='Origin', index=True, track_visibility='onchange')
    customer_vat = fields.Char('Customer Vat', select=True, track_visibility='onchange')
    customer_name = fields.Char('Customer Name', track_visibility='onchange')
    company_vat = fields.Char('Company Vat', track_visibility='onchange')
    company_name = fields.Char('Company Name', track_visibility='onchange')
    date = fields.Datetime('Emission Date', track_visibility='onchange')
    emission_hour = fields.Char('Emission Hour', track_visibility='onchange')
    error_in_einvoice = fields.Boolean('Error in einvoice', default=False, track_visibility='onchange')
    invoice_id = fields.Many2one('account.invoice', 'Invoice', select=True, track_visibility='onchange')
    ebiller_id = fields.Many2one('electronic.biller.cr', 'Biller', select=True)
    invoice_remote_id = fields.Integer('Invoice Remote', track_visibility='onchange')
    sent_to_center = fields.Boolean('Sent to Central', default=False, track_visibility='onchange')
    sent_to_provider = fields.Boolean('Send to Provider', default=False, track_visibility='onchange')
    edi_status = fields.Char('EDI Status', size=255, readonly=True, track_visibility='onchange')
    edi_msg = fields.Text('EDI Status Messages', readonly=True, track_visibility='onchange')
    edi_data = fields.Text('EDI Data', readonly=True, track_visibility='onchange')
    edi_uuid = fields.Text('EDI UUID', readonly=True, track_visibility='onchange')
    instance = fields.Text('Instance', readonly=True, track_visibility='onchange')
    external_db = fields.Text('External DB', readonly=True, track_visibility='onchange')
    external_queue = fields.Text('External Queue', readonly=True, track_visibility='onchange')
    email = fields.Char('Partner Email', track_visibility='onchange')
    mh_complete_number = fields.Char('Numero Completo', track_visibility='onchange')
    provider = fields.Char('Provider', compute='_compute_provider')
    environment = fields.Selection([('test', 'Test'), ('prod', 'Production')], string='Environment', index=True,
                                   default='test', track_visibility='onchange')
    company_id = fields.Many2one('res.company', 'Company', default=api.model(lambda self: self.env.user.company_id), track_visibility='onchange')
    obj_model = fields.Char('Object Model', size=255, select=True, track_visibility='onchange')
    obj_id = fields.Integer('Object Id', select=True, track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', 'Partner', select=True, track_visibility='onchange')
    invoice_condition_id = fields.Many2one('invoice.condition', string="Invoice Condition", select=True, track_visibility='onchange')
    payment_method_ids = fields.Many2many('account.invoice.payment.method', 'edi_payment_method_rel', 'edi_id',
                                          'method_id', 'Payment Methods', track_visibility='onchange')
    ebi_messages_ids = fields.One2many('ebi.doc.message', 'edig_id', 'Mensajes', readonly=True, track_visibility='onchange')
    mh_sequence = fields.Char('Sequence', required=False, track_visibility='onchange')
    mh_access_key = fields.Char('MH Access Key', track_visibility='onchange')
    security_code = fields.Char('Security Code', track_visibility='onchange')
    ebi_voucher_situation = fields.Selection([
        ('1', 'Normal'),
        ('2', 'Contingencia: sustituyen comprobante físico emitido por contingencia'),
        ('3', 'Sin internet'), ],         'Voucher Situation', default='1', select=True, track_visibility='onchange')
    ebi_auth_date = fields.Datetime(string='Fecha de autorización', track_visibility='onchange')
    raw_xml = fields.Text('Raw XML', track_visibility='onchange')
    signed_xml = fields.Text('Signed XML', track_visibility='onchange')
    response_xml = fields.Text('Respuesta XML del Ministerio', track_visibility='onchange')
    document_type_name = fields.Char(compute='_compute_type_name', string='Document Type Name')
    create_date = fields.Datetime('Create Date', readonly=False)
    date_accepted = fields.Datetime('Acceptance Date', track_visibility='onchange')
    not_accepted = fields.Boolean('Not Accepted', default=False, track_visibility='onchange')
    days_for_acceptance = fields.Float(compute='_compute_days_for_acceptance', string='Days for Acceptance')

    @api.multi
    @api.depends('ebiller_id')
    def _compute_provider(self):
        for edid in self:
            if edid.ebiller_id:
                edid.provider = edid.ebiller_id.provider

    def _parseJSON(self, obj):
        if isinstance(obj, dict):
            newobj = {}
            for key, value in obj.iteritems():
                key = str(key)
                newobj[key] = self._parseJSON(value)
        elif isinstance(obj, list):
            newobj = []
            for value in obj:
                newobj.append(self._parseJSON(value))
        elif isinstance(obj, unicode):
            newobj = str(obj)
        else:
            newobj = obj
        return newobj

    def get_dict_from_value(self):
        self.ensure_one()
        result_value_t = simplejson.loads(self.edi_data)
        result_value_r = self._parseJSON(result_value_t)
        return result_value_r

    def get_document_data(self):
        if self.ebiller_id:
            if self.ebiller_id.provider:
                if hasattr(self, '%s_get_document_data' % self.ebiller_id.provider):
                    return getattr(self, '%s_get_document_data' % self.ebiller_id.provider)()

        invoice_dict = {}

        if self.invoice_id:
            invoice_dict['customer'] = self.invoice_id.partner_id.name
            invoice_dict['subtotal'] = self.invoice_id.amount_untaxed
            invoice_dict['tax'] = self.invoice_id.amount_tax
            invoice_dict['total'] = self.invoice_id.amount_total
            invoice_dict['lines'] = []
            if self.invoice_id.invoice_line_ids:
                for line in self.invoice_id.invoice_line_ids:
                    line_dict = {}
                    line_dict['name'] = line.name
                    line_dict['quantity'] = line.quantity
                    line_dict['price_unit'] = line.price_unit
                    line_dict['price_subtotal'] = line.price_subtotal
                    invoice_dict['lines'].append(line_dict)

        return invoice_dict

    def get_document_data_obj(self, invoice_id):
        if self.ebiller_id:
            if self.ebiller_id.provider:
                if hasattr(self, '%s_get_document_data_obj' % self.ebiller_id.provider):
                    return getattr(self, '%s_get_document_data_obj' % self.ebiller_id.provider)(invoice_id)

        invoice_dict = {}

        if invoice_id:
            invoice_dict['customer'] = invoice_id.partner_id.name
            invoice_dict['currency'] = invoice_id.currency_id.name
            invoice_dict['subtotal'] = invoice_id.amount_untaxed
            invoice_dict['tax'] = invoice_id.amount_tax
            invoice_dict['total'] = invoice_id.amount_total
            invoice_dict['lines'] = []
            if invoice_id.invoice_line_ids:
                for line in invoice_id.invoice_line_ids:
                    line_dict = {}
                    line_dict['name'] = line.name.strip()
                    line_dict['main_code'] = ''
                    line_dict['aux_code'] = ''
                    if line.product_id:
                        line_dict['main_code'] = line.product_id.default_code
                        line_dict['aux_code'] = line.product_id.barcode
                    line_dict['quantity'] = line.quantity
                    line_dict['price_unit'] = line.price_unit
                    line_dict['price_subtotal'] = line.price_subtotal
                    line_dict['price_without_taxes'] = line.price_unit * line.quantity

                    # if line.invoice_line_tax_id:
                    #     line_dict['tax_lines'] = []
                    #     taxes = line.invoice_line_tax_id.compute_all(line.price_unit, invoice_id.currency_id.id, line.quantity, line.product_id.id,invoice_id.partner_id.id)['taxes']
                    #     for tax in taxes:
                    #         percent_code = "-1"
                    #         if tax['type'] == "percent":
                    #             percent = tax['tax_percent']
                    #             if percent == 0:
                    #                 percent_code = "0"
                    #             if percent == 12:
                    #                 percent_code = "2"
                    #             if int(percent) == 14:
                    #                 percent_code = "3"
                    #         if tax['type'] == "none":
                    #             percent_code = "6"
                    #
                    #         tax_vals = {
                    #             'code': tax['tax_code'],
                    #             'percentage_code': percent_code,
                    #             'rate': "%d" % (tax['tax_percent'] or 0),
                    #             'base_amount': "%.2f" % (tax['tax_base'] or 0),
                    #             'value': "%.2f" % (tax['amount'] or 0)
                    #         }
                    #
                    #         line_dict['tax_lines'].append(tax_vals)

                    invoice_dict['lines'].append(line_dict)

        return invoice_dict

    @api.model
    def automatic_send(self):
        _logger.info('Beginning cron for sync Shop e-billings')
        invoice_ids = self.env['account.invoice'].search([('type', 'in', ['out_invoice', 'out_refund']), ('sent_to_center', '=', False), ('sent_to_provider', '=', False), ('edig_id', '=', False)], order='id', limit=10)
        for invoice in invoice_ids:
            invoice.action_electronic_send()
        return True

    @api.model
    def set_electronic_document(self, invoice_remote_id, edi_uuid, vals_edi):
        if invoice_remote_id and edi_uuid:
            edi_doc = self.search([('invoice_id', '=', invoice_remote_id), ('edi_uuid', '=', edi_uuid)])
            if edi_doc:
                edi_doc.write(vals_edi)
        return True

    @api.model
    def create_electronic_document(self, edi_vals, eprovider):
        with self._lock:
            edi_doc = self.search(
                [('invoice_id', '=', edi_vals['invoice_remote_id']), ('edi_uuid', '=', edi_vals['edi_uuid'])])
            if eprovider:
                edi_vals['provider'] = eprovider
            if not edi_doc:
                if edi_vals:
                    edi_doc = self.create(edi_vals)
            if edi_doc:
                vals_edi = {}
                vals_edi['sent_to_center'] = True

                send_doc = edi_doc.send_document()

                if send_doc:
                    edi_doc.write({'sent_to_provider': True})
                    vals_edi['sent_to_provider'] = True
                    # RabbitMQClient(self).publish_message(edi_doc.external_queue, {
                    #     'db_name': edi_doc.external_db,
                    #     'model': 'electronic.document.generic',
                    #     'method': 'set_electronic_document',
                    #     'arg': [edi_vals['invoice_remote_id'], edi_vals['edi_uuid'], vals_edi]
                    # })
                    return True
        return False

    def validate_document(self):
        self.ensure_one()
        if self.ebiller_id:
            if self.ebiller_id.provider:
                if hasattr(self, '%s_validate_document' % self.ebiller_id.provider):
                    return getattr(self, '%s_validate_document' % self.ebiller_id.provider)()

        return True

    def sign_document(self):
        self.ensure_one()
        if self.ebiller_id:
            if self.ebiller_id.provider:
                if hasattr(self, '%s_sign_document' % self.ebiller_id.provider):
                    return getattr(self, '%s_sign_document' % self.ebiller_id.provider)()

        return True

    def generate_attachements(self):
        if hasattr(self, '%s_generate_attachements' % self.provider):
            return getattr(self, '%s_generate_attachements' % self.provider)()

        # if self.sent_to_provider:

        return True

    def send_document(self):
        self.ensure_one()
        validate_res = self.validate_document()
        if validate_res:
            sign_doc = self.sign_document()
            if sign_doc:
                if self.ebiller_id:
                    if self.ebiller_id.provider:
                        if hasattr(self, '%s_send_document' % self.ebiller_id.provider):
                            return getattr(self, '%s_send_document' % self.ebiller_id.provider)(sign_doc)

        return True

    @api.multi
    def mh_validate_document_info(self):
        self.ensure_one()
        errors = []
        if not self.company_id:
            company_msg = _('Company is required')
            errors.append(company_msg)
        if not self.customer_vat:
            customer_vat = _('VAT Customer is required')
            errors.append(customer_vat)
        if not self.company_name:
            company_name_msg = _('Company Name is required')
            errors.append(company_name_msg)
        if not self.company_id.partner_id.identification_cr:
            company_vat_msg = _('Company VAT is required')
            errors.append(company_vat_msg)
        if not self.partner_id.email:
            partner_email_msg = _('Correo del Cliente/Proveedor es requerido')
            errors.append(partner_email_msg)

        if not self.environment:
            environment_msg = _('Environment is required')
            errors.append(environment_msg)

        if not self.company_id.emision_points:
            establishment_msg = _('Emission Point is required')
            errors.append(establishment_msg)
        if not self.company_id.establishment_code:
            establishment_msg = _('Establishment Code is required')
            errors.append(establishment_msg)

        if not self.invoice_id.ebi_access_key:
            establishment_msg = ustr(_('La Clave de acceso es requerida.'))
            errors.append(establishment_msg)

        if len(self.invoice_id.ebi_access_key) < 50:
            establishment_msg = ustr(_('La Clave de acceso debe tener longitud 50.'))
            errors.append(establishment_msg)

        if not self.invoice_id.ebi_number_doc:
            establishment_msg = ustr(_('El Consecutivo del documento es requerido.'))
            errors.append(establishment_msg)

        if not self.invoice_id.ebi_number_doc:
            establishment_msg = ustr(_('El Consecutivo del documento es requerido.'))
            errors.append(establishment_msg)

        if self.invoice_id.ebi_number_doc:
            if len(self.invoice_id.ebi_number_doc) < 20:
                establishment_msg = ustr(_('El Consecutivo del documento debe tener longitud 20.'))
                errors.append(establishment_msg)

        if not self.invoice_id.ebi_send_date:
            establishment_msg = ustr(u'La Fecha de emisión es requerida.')
            errors.append(establishment_msg)

        if not self.invoice_id.invoice_condition_id:
            if self.invoice_id.type not in ['in_invoice', 'in_refund']:
                establishment_msg = ustr(u'La Condición Venta es requerida.')
                errors.append(establishment_msg)

        if self.invoice_id.payment_term_id:
            if len(self.invoice_id.payment_term_id.name) > 10:
                establishment_msg = ustr(u'El término de pago debe tener longitud 10.')
                errors.append(establishment_msg)

        if not self.invoice_id.payment_method_ids:
            if self.invoice_id.ebi_voucher_type in ['01', '04'] and self.invoice_id.type not in ['in_invoice', 'in_refund']:
                establishment_msg = ustr(u'Los Métodos de pago son requeridos.')
                errors.append(establishment_msg)

        if self.invoice_id.payment_method_ids:
            if len(self.invoice_id.payment_method_ids) > 4:
                establishment_msg = ustr(u'Se puede incluir máximo de 4 medios de pago.')
                errors.append(establishment_msg)
            for pmt in self.invoice_id.payment_method_ids:
                if not pmt.fe_code:
                    establishment_msg = ustr(u'El Código de FE es requerido en el Método de pago con descripción: ' + pmt.name)
                    errors.append(establishment_msg)

        if not self.invoice_id.invoice_line_ids:
            establishment_msg = ustr(u'Las Líneas de detalle son requeridas.')
            errors.append(establishment_msg)

        if self.invoice_id.invoice_line_ids:
            if len(self.invoice_id.invoice_line_ids) > 1000:
                establishment_msg = ustr(u'Se puede incluir un máximo de 1000 líneas en el documento.')
                errors.append(establishment_msg)
            for line in self.invoice_id.invoice_line_ids:
                if not line.product_id:
                    establishment_msg = ustr(u'El producto es requerido en la línea con descripcion: ' + line.name)
                    errors.append(establishment_msg)

                if line.product_id:
                    if line.product_id.default_code:
                        if len(line.product_id.default_code) > 20:
                            establishment_msg = ustr(u'El código del producto puede incluir un máximo de 20 caract.')
                            errors.append(establishment_msg)

                        if not line.product_id.code_type_id:
                            establishment_msg = ustr(
                                u'El tipo de código producto es requerido en la línea con descripcion: ' + line.name)
                            errors.append(establishment_msg)

                    if not line.product_id.uom_id:
                        establishment_msg = ustr(u'La Unidad de Medida es requerida en la línea con descripción: ' + line.name)
                        errors.append(establishment_msg)

                if not line.quantity:
                    establishment_msg = ustr(u'La Cantidad es requerida en la línea con descripción: ' + line.name)
                    errors.append(establishment_msg)

                if not line.name:
                    establishment_msg = ustr(u'La Descripción es requerida en las líneas.')
                    errors.append(establishment_msg)

                if line.name:
                    if len(line.name) > 160:
                        establishment_msg = ustr(u'La Descripción puede incluir un máximo de 160 caract. en la línea con descripción: ' + line.name)
                        errors.append(establishment_msg)

                if not line.invoice_line_tax_ids:
                    establishment_msg = ustr(u'Debe tener al menos un impuesto la línea detalle: ' + line.name)
                    errors.append(establishment_msg)

                if line.invoice_line_tax_ids:
                    for tax in line.invoice_line_tax_ids:
                        if not tax.cr_group_tax_use:
                            establishment_msg = ustr(u'El campo uso de impuesto es requerido en el Impuesto con descripción: ' + tax.name)
                            errors.append(establishment_msg)

                        if not tax.tax_group_id:
                            establishment_msg = ustr(u'El campo Grupo de impuestos es requerido en el Impuesto con descripción: ' + tax.name)
                            errors.append(establishment_msg)

                        if tax.tax_group_id:
                            if not tax.tax_group_id.fe_tax_code:
                                establishment_msg = ustr(u'El Código de FE es requerido en el grupo de Impuesto con descripción: ' + tax.tax_group_id.name)
                                errors.append(establishment_msg)

        if self.invoice_id.ebi_voucher_type in ['02', '03']:
            if not self.invoice_id.ebi_ref_voucher_code:
                establishment_msg = ustr(u'El Código de Comprobante es requerido.')
                errors.append(establishment_msg)
            if not self.invoice_id.reason_doc_mod:
                establishment_msg = ustr(u'La Razón de modificación es requerida.')
                errors.append(establishment_msg)

        if self.invoice_id.ebi_voucher_type == '02':
            if not self.invoice_id.debit_note_invoice_id:
                establishment_msg = ustr(u'El Documento Origen es requerido.')
                errors.append(establishment_msg)
            if self.invoice_id.debit_note_invoice_id:
                if not self.invoice_id.debit_note_invoice_id.ebi_number_doc:
                    establishment_msg = ustr(u'El Secuencial del Documento Origen es requerido.')
                    errors.append(establishment_msg)

                if not self.invoice_id.debit_note_invoice_id.ebi_voucher_type:
                    establishment_msg = ustr(u'El Tipo del Documento Origen es requerido.')
                    errors.append(establishment_msg)

                if not self.invoice_id.debit_note_invoice_id.ebi_send_date:
                    establishment_msg = ustr(u'La Fecha de emisión del Documento Origen es requerido.')
                    errors.append(establishment_msg)

        if self.invoice_id.ebi_voucher_type == '03':
            if not self.invoice_id.refund_invoice_id:
                establishment_msg = ustr(u'El Documento Origen es requerido.')
                errors.append(establishment_msg)

            if self.invoice_id.refund_invoice_id:
                if not self.invoice_id.refund_invoice_id.ebi_number_doc:
                    establishment_msg = ustr(u'El Secuencial del Documento Origen es requerido.')
                    errors.append(establishment_msg)

                if not self.invoice_id.refund_invoice_id.ebi_voucher_type:
                    establishment_msg = ustr(u'El Tipo del Documento Origen es requerido.')
                    errors.append(establishment_msg)

                if not self.invoice_id.refund_invoice_id.ebi_send_date:
                    establishment_msg = ustr(u'La Fecha de emisión del Documento Origen es requerido.')
                    errors.append(establishment_msg)

        # emisor
        if not self.company_id.partner_id.country_id:
            establishment_msg = ustr(u'El País del Emisor es requerido.')
            errors.append(establishment_msg)

        if not self.company_id.partner_id.name:
            establishment_msg = ustr(_('El Nombre del Emisor es requerido.'))
            errors.append(establishment_msg)

        if len(self.company_id.partner_id.name) > 80:
            establishment_msg = ustr(u'El Nombre del Emisor debe tener longitud 80 caract.')
            errors.append(establishment_msg)

        if not self.company_id.partner_id.identification_type:
            establishment_msg = ustr(u'El tipo de identificación del Emisor es requerido.')
            errors.append(establishment_msg)

        if not self.company_id.partner_id.identification_cr:
            establishment_msg = ustr(u'La identificación del Emisor es requerida.')
            errors.append(establishment_msg)

        if self.company_id.comercial_name:
            if len(self.company_id.comercial_name) > 80:
                establishment_msg = ustr(u'El Nombre del Emisor debe tener longitud máxima de 80 caract.')
                errors.append(establishment_msg)

        if not self.company_id.partner_id.state_id:
            establishment_msg = ustr(_('La Provincia del Emisor es requerida.'))
            errors.append(establishment_msg)

        if not self.company_id.partner_id.city_id:
            establishment_msg = ustr(u'La Cantón del Emisor es requerido.')
            errors.append(establishment_msg)

        if not self.company_id.partner_id.district_id:
            establishment_msg = ustr(_('El Distrito del Emisor es requerido.'))
            errors.append(establishment_msg)

        if not self.company_id.partner_id.otras_senas:
            establishment_msg = ustr(u'El Campo Otras Señas del Emisor es requerido.')
            errors.append(establishment_msg)

        # receptor
        _logger.debug("verificando identificacion receptor ---> " + self.invoice_id.identification_type + " <---")
        if self.invoice_id.identification_type != '100':
            _logger.debug("verificando identificacion receptor entrando a condicion ---> " + self.invoice_id.identification_type + " <---")
            if not self.invoice_id.partner_id.country_id:
                establishment_msg = ustr(u'El País del Receptor es requerido.')
                errors.append(establishment_msg)

            if not self.invoice_id.partner_id.state_id:
                establishment_msg = ustr(_('La Provincia del Receptor es requerida.'))
                errors.append(establishment_msg)

            if not self.invoice_id.partner_id.city_id:
                establishment_msg = ustr(u'La Cantón del Receptor es requerido.')
                errors.append(establishment_msg)

            if not self.invoice_id.partner_id.district_id:
                establishment_msg = ustr(_('El Distrito del Receptor es requerido.'))
                errors.append(establishment_msg)

            if not self.invoice_id.partner_id.otras_senas:
                establishment_msg = ustr(u'El Campo Otras Señas del Receptor es requerido.')
                errors.append(establishment_msg)

        if not self.invoice_id.partner_id.name:
            establishment_msg = ustr(_('El Nombre del Receptor es requerido.'))
            errors.append(establishment_msg)

        if len(self.invoice_id.partner_id.name) > 80:
            establishment_msg = ustr(_('El Nombre del Receptor debe tener longitud de 80 caract.'))
            errors.append(establishment_msg)

        if not self.invoice_id.identification_type:
            establishment_msg = ustr(_('El tipo de Identificacion del Receptor es requerido.'))
            errors.append(establishment_msg)

        if not self.invoice_id.identification_cr:
            establishment_msg = ustr(_('La Identificacion del Receptor es requerida.'))
            errors.append(establishment_msg)

        if self.invoice_id.comercial_name:
            if len(self.invoice_id.comercial_name) > 80:
                establishment_msg = ustr(_('El Nombre del Receptor debe tener longitud de 80 caract.'))
                errors.append(establishment_msg)

        if not self.invoice_id.total_comprobante:
            establishment_msg = ustr(u'El Campo Total del Comprobante es requerido.')
            errors.append(establishment_msg)

        if not self.type:
            type_msg = _('Type is required')
            errors.append(type_msg)
        if errors:
            raise ValidationError(_("Han ocurrido los siguientes errores:"'\n') + '\n'.join(errors))
        return True

    @api.multi
    def costarica_supplier_generate_doc(self):
        self.ensure_one()
        doc = self.env[self.obj_model].browse(self.obj_id)
        name = doc._name + (('.%s' % doc.type) if hasattr(doc, 'type') else '')
        name += (('.%s' % doc.ebi_voucher_type) if hasattr(doc, 'ebi_voucher_type') else '')

        field_template = TEMPLATES[name]
        # print "plantilla ", name, field_template
        try:
            template = Template(getattr(self.ebiller_id, field_template))
        except Exception as e:
            raise e
        tipo_ident = {'c': '05', 'r': '04', 'p': '06'}

        def diff_days(date1, date2=None):
            date1 = fields.Date.from_string(date1)
            date2 = fields.Date.from_string(date2 or date1.strftime('%Y-%m-%d'))
            return (date2 - date1).days

        def date_format(date, format="%Y-%m-%dT%H:%M:%S"):
            tzinfo = timezone('America/Costa_Rica')
            if date:
                start_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                diffHoraria = int(tzinfo.localize(start_date).strftime('%z')) / 100
                start_date = start_date + timedelta(hours=diffHoraria)
                # date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                return start_date.strftime(format)
            return False
        result = False
        try:
            doc = self.env[self.obj_model].browse(self.obj_id)
            # print "--->", doc.debit_note_invoice_id.id
            doc.ebi_send_date = fields.Datetime.now()
            self.mh_validate_document_info()
            result = template.render(tipo_ident=lambda ident: tipo_ident.get(ident, 'NONE'), doc=doc,
                                     date_format=date_format, diff_days=diff_days, ustr=ustr, str=str)
            doc.xml_file = result
        except Exception as e:
            raise e

        return result

    @api.model
    def _filestore(self):
        return config.filestore(self._cr.dbname)

    @api.model
    def _full_path(self, path):
        path = re.sub('[.]', '.', path)
        path = path.strip('/\\')
        return os.path.join(self._filestore(), path)

    @api.multi
    def build_document(self):
        self.ensure_one()
        raw_xml_t = self.costarica_supplier_generate_doc()
        self.write({'raw_xml': raw_xml_t})
        jar_path = self.ebiller_id.jar_path
        key_store_pwd = self.company_id.key_store_pswd
        domain = [
            ('res_model', '=', 'res.company'),
            ('res_field', '=', 'key_store_file'),
            ('res_id', '=', self.company_id.id),
        ]
        key_attach_id = self.env['ir.attachment'].sudo().search(domain)
        key_store_path = key_attach_id._full_path(key_attach_id.store_fname)
        # key_store_path = '/home/orlando/Escritorio/proyectos/soporte/project_medical_costa/repos/develop/solt-erp-multicompany/addons/medical_ebilling_cr/data/030412028623.p12'
        fname_xml = str(self.env.user.id) + '_' + str(self.invoice_id.ebi_voucher_type) + '_' + str(self.invoice_id.id) + '_byuser_unsigned.xml'
        full_path_xml = self._full_path(fname_xml)
        # print "full path", full_path_xml
        file_xml = open(full_path_xml, 'w+')
        file_xml.write(raw_xml_t.encode('utf-8'))
        file_xml.close()

        fname_signed_xml = str(self.env.user.id) + '_' + str(self.invoice_id.ebi_voucher_type) + '_' + str(self.invoice_id.id) + '_byuser_signed.xml'
        full_path_signed_xml = self._full_path(fname_signed_xml)
        file_signed_xml = open(full_path_signed_xml, 'w+')
        file_signed_xml.write(raw_xml_t.encode('utf-8'))
        file_signed_xml.close()

        _logger.error("Ubicacion de archivo p12 " + key_store_path)
        _logger.error("Ubicacion de archivo jar " + str(jar_path))
        # esto es para jar xadessignercr.jar
        args = [jar_path, 'sign', key_store_path, key_store_pwd, full_path_xml, full_path_signed_xml]
        # esto es para jar firmar-xades.jar
        # args = [jar_path, key_store_path, key_store_pwd, full_path_xml, full_path_signed_xml]
        _logger.error("Ubicacion de los argumentos " + str(args))
        try:
            # subprocess.call(['java', '-Dfile.encoding=UTF8', '-jar'] + args, stdout=PIPE, stderr=PIPE)
            subprocess.call(['java', '-Dfile.encoding=UTF8', '-jar'] + args)
            # signed_xml = process.communicate()[0]
            file_signed_xml = open(full_path_signed_xml, 'r')
            signed_xml = file_signed_xml.read()
            _logger.error("Firmado " + ustr(signed_xml))
        except (Exception,) as e:
            _logger.error(serialize_exception(e))
            raise UserError(_("A ocurrido un error firmando el xml, verifique la configuracion del emisor"))
        if not signed_xml:
            raise UserError(_("A ocurrido un error firmando el xml, verifique la configuracion del emisor"))
        _logger.error("ARCHIVO XML FIRMADO " + ustr(signed_xml))
        self.write({'signed_xml': signed_xml})
        return signed_xml

    @api.multi
    def build_access_key(self):
        self.ensure_one()
        access_key = ''
        doc = self.env[self.obj_model].browse(self.obj_id)
        # if doc.type in ['out_invoice', 'out_refund']:
            # doc = self.env[self.obj_model].browse(self.obj_id)
        alt_t = random.randrange(99999999)
        # print "numero alt ", alt_t
        access_key = "".join((
            '506',
            datetime.strptime(self.date, DEFAULT_SERVER_DATETIME_FORMAT).strftime("%d%m%y"),
            str(self.company_vat).zfill(12),
            self.mh_complete_number,
            self.ebi_voucher_situation,
            str(alt_t).zfill(8)
        ))
            # access_key += str(mod11(access_key))
        # if doc.type in ['in_invoice', 'in_refund']:
        #     access_key = doc.supplier_ebi_access_key
        print "clave de acceso ", access_key
        self.write({'mh_access_key': access_key})
        doc.ebi_access_key = access_key

    @api.multi
    def validate_with_errors(self, xml_, xsd_):
        validation = xsd_.validate(xml_)
        return (validation, xsd_.error_log, )

    def _get_state_refund_to_report(self):
        return ['open', 'paid']

    def xsd_error_as_simple_string(self, error):
        """
        Returns a string based on an XSD error object with the format
        LINE:COLUMN:LEVEL_NAME:DOMAIN_NAME:TYPE_NAME:MESSAGE.
        """
        parts = [
            error.line,
            error.column,
            error.level_name,
            error.domain_name,
            error.type_name,
            error.message
        ]
        return ':'.join([str(item) for item in parts])

    def xsd_error_as_dict(self, error):
        parts = {
            'line': error.line,
            'column': error.column,
            'level_name': error.level_name,
            'domain_name': error.domain_name,
            'type_name': error.type_name,
            'message': error.message
        }
        return parts

    def xsd_error_log_as_simple_strings(self, error_log):
        """
        Returns a list of strings representing all the errors of an XSD
        error log object.
        """
        return [self.xsd_error_as_simple_string(e) for e in error_log]

    def get_voucher_field_ids(self, voucher_tree_type):
        list_all_types = [['export_ats_voucher_reporter_tree', 'reporter_ids'],
                          ['export_ats_voucher_purchase_details_tree', 'purchase_details_ids'],
                          ['export_ats_voucher_payment_types_tree', 'purchase_payment_types_ids'],
                          ['export_ats_voucher_retention_tree', 'purchase_retention_ids'],
                          ['export_ats_voucher_refunds_tree', 'purchase_refunds_ids'],
                          ['export_ats_voucher_sales_partners_tree', 'sales_partners_ids'],
                          ['export_ats_voucher_sales_establishment_tree', 'sales_establishment_ids'],
                          ['export_ats_voucher_cancel_voucher_tree', 'cancel_voucher_ids']]
        for voucher_type in list_all_types:
            if voucher_type[0] == voucher_tree_type:
                return voucher_type[1]
        return False

    def get_string_for_field(self, column_ref_name):

        if self._columns:
            if self._columns.get(column_ref_name, ''):
                return self._columns[column_ref_name].string

    def get_voucher_type_by_column(self, column):
        list_all_types = ['export_ats_voucher_reporter_tree',
                          'export_ats_voucher_purchase_details_tree',
                          'export_ats_voucher_payment_types_tree',
                          'export_ats_voucher_retention_tree',
                          'export_ats_voucher_refunds_tree',
                          'export_ats_voucher_sales_partners_tree',
                          'export_ats_voucher_sales_establishment_tree',
                          'export_ats_voucher_cancel_voucher_tree']
        types_finds = []
        for voucher_type in list_all_types:
            all_columns_t = self.get_fields_by_tree_all(voucher_type)
            if all_columns_t:
                for f_dict in all_columns_t:
                    if f_dict.keys()[0] == column:
                        if voucher_type not in types_finds:
                            types_finds.append(voucher_type)
        return types_finds

    def get_message_type(self, message):
        match = message.split("'")
        mes_ret = message
        if match:
            valor = match[1]
            valor_inst = ''
            if len(match)>=3:
                valor_inst = match[3]

            mes_ret = "El campo " + valor + " contiene un valor incorrecto [ Valor: " + valor_inst + " ]."

        error_ats_inst = error_fe_p(mes_ret, valor, valor_inst, [])
            # return error_ats_inst
            # return "El campo " + valor + " contiene un valor incorrecto [ Valor: " + valor_inst + " ]."
        return error_ats_inst

    def get_message_type_enumeration(self, message):
        match = message.split("'")
        print "split del valor ", match
        mes_ret = message
        if match:
            valor = match[1]
            valor_inst = ''
            values_domain = ''
            if len(match)>=5:
                valor_inst = match[5]

            mes_ret = "El campo " + valor + " contiene un valor incorrecto [ Valor: " + valor_inst + " ]."
            if message.index("is not an element of the set"):
                values_domain = message[message.index("is not an element of the set") + len("is not an element of the set"):]
                mes_ret += " Debe contener uno de los siguientes valores: " + values_domain + " ]."

        error_ats_inst = error_fe_p(mes_ret, valor, valor_inst, [])
            # return error_ats_inst
            # return "El campo " + valor + " contiene un valor incorrecto [ Valor: " + valor_inst + " ]."
        return error_ats_inst

    def get_message_type_cvc_elt(self, message):
        match = message.split("'")
        print "split del valor ", match
        mes_ret = message
        if match:
            valor = match[1]
            valor_inst = ''
            values_domain = ''
            if len(match)>=2:
                valor_inst = match[2]

            mes_ret = "El campo " + valor + " contiene un valor incorrecto [ Valor: " + valor_inst + " ]."

        error_ats_inst = error_fe_p(mes_ret, valor, valor_inst, [])
            # return error_ats_inst
            # return "El campo " + valor + " contiene un valor incorrecto [ Valor: " + valor_inst + " ]."
        return error_ats_inst

    def get_message_maxlent(self, message):
        match = message.split("'")
        mes_ret = message
        valor = ''
        if match:
            valor = match[1]
            mes_ret = "El campo " + valor + " tiene " +match[5]+ " caracteres esto es incorrecto, realmente debe tener hasta " + match[7] + " caracteres."
        error_ats_inst = error_fe_p(mes_ret, valor, "", [])
        return error_ats_inst

    def get_message_minlent(self, message):
        match = message.split("'")
        mes_ret = message
        valor = ''
        if match:
            valor = match[1]
            mes_ret = "El campo " + valor + " tiene " +match[5]+ " caracteres esto es incorrecto, realmente debe minino hasta " + match[7] + " caracteres."
        error_ats_inst = error_fe_p(mes_ret, valor, "", [])
        return error_ats_inst

    def get_message_mininclusive(self, message):
        match = message.split("'")
        mes_ret = message
        valor = ''
        if match:
            valor = match[1]
            mes_ret = "El campo " + valor + " tiene el valor " +match[5]+ "  es menor que el valor minimo permitido " + match[7] + "."
        error_ats_inst = error_fe_p(mes_ret, valor, "", [])
        return error_ats_inst

    def get_message_elem_content(self, message):
        match = message.split("(")
        mes_ret = message
        valor = ''
        if match:
            valor = match[1]
            mes_ret = "El campo " + valor.split(" )")[0] + " esta en posicion incorrecta en el xml."
        error_ats_inst = error_fe_p(mes_ret, valor, "", [])
        return error_ats_inst

    def get_message_pattern_valid(self, message):
        match = message.split("'")
        mes_ret = message
        valor = ''
        valor_inst = ""
        if match:
            valor = match[1]
            valor_inst = ''
            if len(match)>=5:
                valor_inst = match[5]
            mes_ret = "El campo " + valor + " contiene un valor incorrecto [ Valor: " + valor_inst + " ]."
        error_ats_inst = error_fe_p(mes_ret, valor, valor_inst, [])
        return error_ats_inst

    def get_message_length_valid(self, message):
        match = message.split("'")
        mes_ret = message
        valor = ''
        if match:
            valor = match[1]
            mes_ret = "El campo " + valor + " tiene " + match[
                5] + " caracteres esto es incorrecto, realmente debe tener hasta " + match[7] + " caracteres."
        error_ats_inst = error_fe_p(mes_ret, valor, "", [])
        return error_ats_inst

    @api.multi
    def get_text_exceptions(self, list_exceptions):
        text_complete = ""
        text_complete_list = []
        error_complete_list = []
        if list_exceptions:
            # for e in list_exceptions:
            e = list_exceptions[0]
            f_e = self.xsd_error_as_dict(e)
            # print "error dict ", f_e
            show_message = f_e.get('message', '-')
            print "error othh ", f_e
            if f_e.get('type_name', ''):
                if f_e['type_name'] == 'SCHEMAV_CVC_MAXLENGTH_VALID':
                    show_message = self.get_message_maxlent(f_e.get('message', '-'))
                if f_e['type_name'] == 'SCHEMAV_CVC_LENGTH_VALID':
                    show_message = self.get_message_length_valid(f_e.get('message', '-'))
                if f_e['type_name'] == 'SCHEMAV_CVC_MININCLUSIVE_VALID':
                    show_message = self.get_message_mininclusive(f_e.get('message', '-'))
                if f_e['type_name'] == 'SCHEMAV_CVC_MINLENGTH_VALID':
                    show_message = self.get_message_minlent(f_e.get('message', '-'))
                if f_e['type_name'].__contains__('SCHEMAV_CVC_DATATYPE_VALID'):
                    show_message = self.get_message_type(f_e.get('message', '-'))
                if f_e['type_name'] == 'SCHEMAV_CVC_ENUMERATION_VALID':
                    show_message = self.get_message_type_enumeration(f_e.get('message', '-'))
                if f_e['type_name'] == 'SCHEMAV_CVC_ELT_1':
                    show_message = self.get_message_type_cvc_elt(f_e.get('message', '-'))
                if f_e['type_name'] == 'SCHEMAV_ELEMENT_CONTENT':
                    show_message = self.get_message_elem_content(f_e.get('message', '-'))
                if f_e['type_name'] == 'SCHEMAV_CVC_PATTERN_VALID':
                    show_message = self.get_message_pattern_valid(f_e.get('message', '-'))
                if show_message:
                    # print "mensaje x ", show_message
                    if show_message.message not in text_complete_list:
                        text_complete += show_message.message + "\n"
                        text_complete_list.append(show_message.message)
                        error_complete_list.append(show_message)
            if error_complete_list:
                text_complete = ""
                for error_s in error_complete_list:
                    # print "error real", error_s
                    if error_s.column_ref:
                        # docts = self.find_voucher_by_field(error_s.column_ref, error_s.value_ref)
                        # if docts:
                        #     text_complete += error_s.message + "\n"
                        #     text_complete += "Datos con problemas:" + "\n"
                        #     for name_doc, doc_l in docts.iteritems():
                        #         text_complete += "\t\t\t"+name_doc+":" + "\n"
                        #         for doc_r in doc_l:
                        #             text_complete += "\t\t\t\t\t\t" + doc_r.number+ "\n"
                        #         text_complete += "\n\n"
                        # else:
                        text_complete += error_s.message + "\n"

        return text_complete

    @api.multi
    def validate_xml(self):
        # self.mh_validate_document_info()
        _logger.info('Validacion de esquema')
        # print "xml firmado ", self.signed_xml
        _logger.debug("xml firmado para verificar ---> " + self.signed_xml.encode('utf-8') + " <---")
        shema_index = self.type
        if self.invoice_id.type in ['in_invoice', 'in_refund']:
            shema_index = '100000'
        print "esquema ", SCHEMAS[shema_index]
        file_path = os.path.join(os.path.dirname(__file__), SCHEMAS[shema_index])
        schema_file = open(file_path)
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        str_signed_xml = self.signed_xml.encode('utf-8')
        # print "xml ", str_signed_xml
        signed_xml_doc = etree.XML(str(str_signed_xml.replace('<?xml version="1.0" encoding="UTF-8"?>', '')))
        try:
            # print "si si si ", signed_xml_doc
            xmlschema.assertValid(signed_xml_doc)
        except etree.XMLSchemaParseError, xspe:
            print "XMLSchemaParseError occurred!"
        except etree.XMLSyntaxError, xse:
            print "XMLSyntaxError occurred!"
            print xse
        except etree.DocumentInvalid, di:
            print "DocumentInvalid occurred!"
            error = xmlschema.error_log.last_error
            if error:
                # All the error properties (from libxml2) describing what went wrong
                print 'domain_name: ' + error.domain_name
                print 'domain: ' + str(error.domain)
                print 'filename: ' + error.filename  # '<string>' cos var is a string of xml
                print 'level: ' + str(error.level)
                print 'level_name: ' + error.level_name  # an integer
                print 'line: ' + str(error.line)  # a unicode string that identifies the line where the error occurred.
                print 'message: ' + error.message  # a unicode string that lists the message.
                print 'type: ' + str(error.type)  # an integer
                print 'type_name: ' + error.type_name

        list_errors = self.validate_with_errors(signed_xml_doc, xmlschema)
        # print list_errors
        # except DocumentInvalid as e:
        if list_errors:
            if list_errors[1]:
                # error_str = self.xsd_error_log_as_simple_strings(list_errors[1])
                text_excp_ = self.get_text_exceptions(list_errors[1])
                message_title = "ERROR"
                message_msg = text_excp_
                state = 'ERROR'
                res_id = self.obj_id
                model_name = self.obj_model
                sequence_msg = len(self.env[model_name].browse(res_id).ebi_messages_ids) + 1
                message_data = {
                    'title': message_title,
                    'message': message_msg,
                    'state': state,
                    'access_key': self.mh_access_key,
                    'res_id': res_id,
                    'model_name': model_name,
                    'type': 'interno',
                    'sequence': sequence_msg,
                    'edig_id': self.id,
                    'invoice_id': self.invoice_id.id,
                }
                self.env['ebi.doc.message'].create(message_data)
                self.message_post(body=message_title + ' - ' + message_msg)
                self.invoice_id.message_post(body=message_title + ' - ' + message_msg)
                return self.env['cr.wizard.message'].generated_message(message_msg, name=message_title)
        return True

    @api.one
    def verify_document_its_self(self):
        if self.obj_model and self.obj_id:
            doc_inst = self.env[self.obj_model].browse(self.obj_id)
            emission_point_field = 'emision_point_id'
            emission_point_value = doc_inst.emision_point_id.id

            doc_search = self.env[self.obj_model].search([('ebi_access_key', '=', self.mh_access_key),
                                                          (emission_point_field, '=', emission_point_value),
                                                          ('ebi_voucher_type', '=', doc_inst.ebi_voucher_type),
                                                          ('company_id', '=', doc_inst.company_id.id)])
            if doc_search:
                if len(doc_search.ids) >= 2:
                    return False
                if len(doc_search.ids) == 1:
                    if doc_search.ebi_access_key == self.mh_access_key:
                        supplier = self.company_id.ebiller_id
                        if not supplier:
                            action = self.env.ref('multi_ebilling_base.action_ebiller')
                            raise RedirectWarning(u'No se ha configurado un proveedor de facturación electrónica',
                                                  action.id, u'Ir al panel de configuración')
                        return supplier.resend_document(self, raise_error=False)
        return True

    @api.one
    def send_document_email(self):
        self.ensure_one()
        signed_xml = ustr(self.signed_xml)
        response_t_xml = ustr(self.response_xml)

        template_ref_x = 'medical_ebilling_cr.email_template_document_generic_cr'
        if self.type in ['09', '10', '11']:
            template_ref_x = 'medical_ebilling_cr.email_template_accept_rechazo_cr'

        mail_id = self.env.ref(template_ref_x).send_mail(self.id, raise_exception=False)
        mail = self.env['mail.mail'].browse(mail_id)
        mh_document_xml = 'comprobante_%s.xml' % self.mh_access_key
        buf = StringIO()
        buf.write(signed_xml)
        xml_param = base64.b64encode(bytes(buf.getvalue().encode('utf-8')))

        mail_message_id = mail.mail_message_id.id

        data_att_dict = {
            'name': mh_document_xml,
            'datas_fname': mh_document_xml,
            'datas': xml_param,
            'res_model': 'mail.message',
            'res_id': mail_message_id,
        }

        ctx = self.env.context.copy()
        ctx.update({'type': 'binary', 'default_type': 'binary'})

        attach_id = self.env['ir.attachment'].with_context(ctx).create(data_att_dict)
        mail.write({'attachment_ids': [(4, attach_id.id)]})

        mh_res_document_xml = 'respuesta_%s.xml' % self.mh_access_key
        buf_res = StringIO()
        buf_res.write(response_t_xml)
        xml_res_param = base64.b64encode(bytes(buf_res.getvalue().encode('utf-8')))

        attach_res_id = self.env['ir.attachment'].with_context(ctx).create({
            'name': mh_res_document_xml,
            'datas_fname': mh_res_document_xml,
            'datas': xml_res_param,
            'res_model': 'mail.message',
            'res_id': mail_message_id,
        })
        mail.write({'attachment_ids': [(4, attach_res_id.id)]})
        mail.send(raise_exception=False)
        return True

    @api.one
    def btn_send_mail(self):
        self.ensure_one()
        try:
            self.send_document_email()
            message_title = "Comprobante - Correo Enviado"
            message_msg = 'El Correo ha sido Enviado'
            state = 'CORREO ENVIADO'
            res_id = self.obj_id
            model_name = self.obj_model
            sequence_msg = len(self.invoice_id.ebi_messages_ids) + 1
            message_data = {
                'title': message_title,
                'message': message_msg,
                'state': state,
                'access_key': self.ebi_access_key,
                'res_id': res_id,
                'model_name': model_name,
                'type': 'interno',
                'sequence': sequence_msg,
                'edig_id': self.id,
                'invoice_id': self.invoice_id.id,
            }
            self.invoice_id.message_post(body=message_title + ' - ' + message_msg)
            self.env['ebi.doc.message'].create(message_data)
        except Exception as e:
            message_title = "ERROR ENVIANDO CORREO"
            message_msg = str(e)
            state = 'ERROR'
            res_id = self.obj_id
            model_name = self.obj_model
            sequence_msg = len(self.invoice_id.ebi_messages_ids) + 1
            message_data = {
                'title': message_title,
                'message': message_msg,
                'state': state,
                'access_key': self.ebi_access_key,
                'res_id': res_id,
                'model_name': model_name,
                'type': 'error',
                'sequence': sequence_msg,
                'edig_id': self.id,
                'invoice_id': self.invoice_id.id,
            }
            self.invoice_id.message_post(body=message_title + ' - ' + message_msg)
            self.env['ebi.doc.message'].create(message_data)

    @api.multi
    def update_status(self, status, date_auth, msg='', value=0):
        self.ensure_one()
        res_id = self.obj_id
        model_name = self.obj_model
        if status == 'ACEPTADO':
            self.write({
                'state': 'done',
                'edi_status': status,
                'ebi_state': 'auth',
                'edi_msg': msg,
                'value': value,
                'date_authorization': date_auth,
            })

            message_title = "ACEPTADO"
            message_msg = msg
            state = 'ACEPTADO'
            if not msg:
                message_msg = _('El documento electrónico ha sido aceptado.')
            sequence_msg = len(self.env[model_name].browse(res_id).ebi_messages_ids) + 1
            message_data = {
                'title': message_title,
                'message': message_msg,
                'state': state,
                'access_key': self.mh_access_key,
                'res_id': res_id,
                'model_name': model_name,
                'type': 'mh',
                'sequence': sequence_msg,
                'edig_id': self.id,
                'invoice_id': self.invoice_id.id,
            }

            self.env['ebi.doc.message'].create(message_data)
            self.message_post(body=message_title + ' - ' + message_msg)
            self.invoice_id.message_post(body=message_title + ' - ' + message_msg)
            self.env[model_name].browse(res_id).write({'ebi_state': 'auth',
                                                       'ebi_auth_date': fields.Datetime.now()})
            # self.btn_send_mail()

        if status == 'RECHAZADO':
            self.write({
                'state': 'cancel',
                'edi_status': status,
                'edi_msg': msg,
                'value': value,
            })

            message_title = "RECHAZADO"
            message_msg = msg
            state = 'RECHAZADO'
            if not msg:
                message_msg = _('El documento electrónico ha sido rechazado.')
            sequence_msg = len(self.env[model_name].browse(res_id).ebi_messages_ids) + 1
            message_data = {
                'title': message_title,
                'message': message_msg,
                'state': state,
                'ebi_state': 'noauth',
                'access_key': self.mh_access_key,
                'res_id': res_id,
                'model_name': model_name,
                'type': 'mh',
                'sequence': sequence_msg,
                'edig_id': self.id,
                'invoice_id': self.invoice_id.id,
            }

            self.env['ebi.doc.message'].create(message_data)
            self.message_post(body=message_title + ' - ' +message_msg)
            self.invoice_id.message_post(body=message_title + ' - ' +message_msg)
            self.env[model_name].browse(res_id).write({'ebi_state': 'noauth'})
            return self.env['cr.wizard.message'].generated_message(message_msg, name=message_title)

        if status == 'ERROR':
            message_title = "ERROR"
            message_msg = msg
            state = 'ERROR'
            res_id = self.obj_id
            model_name = self.obj_model
            sequence_msg = len(self.env[model_name].browse(res_id).ebi_messages_ids) + 1
            message_data = {
                'title': message_title,
                'message': message_msg,
                'state': status.upper(),
                'access_key': self.mh_access_key,
                'res_id': res_id,
                'model_name': model_name,
                'type': 'error',
                'sequence': sequence_msg,
                'edig_id': self.id,
                'invoice_id': self.invoice_id.id,
            }
            self.message_post(body=message_title + ' - ' +message_msg)
            self.invoice_id.message_post(body=message_title + ' - ' +message_msg)

            self.env['ebi.doc.message'].create(message_data)

            self.write({
                'state': 'error',
                'edi_status': status,
                'ebi_state': 'send',
                'edi_msg': msg,
                'value': value
            })
            return self.env['cr.wizard.message'].generated_message(message_msg, name=message_title)

class ebi_additional_information(models.Model):
    _name = 'ebi.additional.information'
    _description = u'Información adicional de los documentos electrónicos'

    field_name = fields.Char('Nombre', required=False)
    field_value = fields.Char('Descripción', required=True)
    res_id = fields.Integer('Id de documento relacionado', required=True)
    model_name = fields.Char('Nombre del modelo relacionado', required=True)

class ebi_doc_message_manager(models.Model):
    _name = 'ebi.doc.message.manager'
    _description = 'Mensajes capturados'
    _order = 'create_date desc'

    create_date = fields.Datetime('Fecha', readonly=True)
    res_id = fields.Integer('Id de documento relacionado', required=True)
    model_name = fields.Char('Nombre del modelo relacionado', required=True)
    lines_id = fields.One2many('ebi.doc.message', 'manager_id', 'Electronic Doc.')
    invoice_id = fields.Many2one('account.invoice', 'Factura')
    edig_id = fields.Many2one('electronic.document.generic.cr', 'Electronic Doc.')
    company_id = fields.Many2one('res.company', 'Company', default=api.model(lambda self: self.env.user.company_id))

class ebi_doc_message(models.Model):
    _name = 'ebi.doc.message'
    _description = u'Mensajes capturados por el intregrador de facturación electrónica'
    _order = 'sequence desc'

    title = fields.Char('Título', required=True)
    message = fields.Char('Mensaje', required=True)
    sequence = fields.Integer('Secuencia')
    state = fields.Char('Estado')
    extended_message = fields.Text('Información adicional')
    access_key = fields.Char('Clave de acceso')
    create_date = fields.Datetime('Fecha', readonly=True)
    res_id = fields.Integer('Id de documento relacionado', required=True)
    model_name = fields.Char('Nombre del modelo relacionado', required=True)
    edig_id = fields.Many2one('electronic.document.generic.cr', 'Electronic Doc.')
    invoice_id = fields.Many2one('account.invoice', 'Factura')
    manager_id = fields.Many2one('ebi.doc.message.manager', 'Manager')
    type = fields.Selection(type_errors, 'Type', default='message')
    company_id = fields.Many2one('res.company', 'Company', default=api.model(lambda self: self.env.user.company_id))