# -*- coding: utf-8 -*-
from datetime import datetime
from openerp.tools import float_round
import logging
from openerp import models, fields, api, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, ustr
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)

doc_general_type = {
    'invoice': 'Factura',
    'invoice_ext': 'Factura del exterior',
    'purchase_liq': 'Liquidación de Compra',
    'sales_note': 'Nota de Venta',
    'anticipo': 'Anticipo',
    'ticket_aereo': 'Ticket aereo',
    'alicuota': 'Alícuotas',
    'gas_no_dedu': 'Gastos No Deduci',
    'reembolso': 'Reembolso de gasto',
    'gasto_viaje': 'Gasto de Viaje',
    'gasto_deducble': 'Gasto deducible sin Factura',
    'comp_venta_ext': 'Comprobante de Venta Emitido Exterior',
    'debit_note': 'Nota de Débito',
    'invoice_refund': 'Nota de Crédito',
    'doc_inst_fin': 'Doc. Emitido Inst. Financieras',
    'doc_inst_est': 'Doc. Emitido Inst. Estado'
}

IVA_RET_PERC = [0.00, 10.00, 20.00, 30.00, 70.00, 100.00]

class report_document_generic_mh(models.AbstractModel):
    _name = 'report.medical_ebilling_cr.report_document_generic_mh'

    @api.model
    def render_html(self, docids, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name('medical_ebilling_cr.report_document_generic_mh')
        records = self.env['electronic.document.generic.cr'].browse(docids)

        if records.invoice_id.type not in ['out_invoice', 'out_refund']:
            raise ValidationError('Sólo puede imprimir COMPROBANTES DE VENTAS')

        docargs = {
            'data': data,
            'ustr': ustr,
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': records,
            'get_lines': self.get_lines,
            'get_emission_datetime': self.get_emission_datetime,
            'get_buyer_address': self.get_buyer_address,
            'get_aditional_info': self.get_aditional_info,
            'doc_type': {
                '01': 'Factura Electrónica',
                '03': 'Nota de Crédito Electrónica',
                '02': 'Nota de Débito Electrónica',
                '04': 'Tiquete Electrónico',
                '05': 'Nota de despacho',
                '06': 'Contrato',
                '07': 'Procedimiento',
                '08': 'Comprobante emitido en contigencia',
                '99': 'Otros'
            },
            'doc_ref_code': {
                 '01':'Anula documento de referencia',
                 '02':'Corrige texto de documento de referencia',
                 '03': 'Corrige monto',
                 '04': 'Referencia a otro documento',
                 '05': 'Sustituye comprobante provisional por contigencia',
                 '99': 'Otros'
            }
        }
        return Report.render('medical_ebilling_cr.report_document_generic_mh', docargs)

    @api.model
    def get_buyer_address(self, invoice_id):
        buyer_address = invoice_id.partner_id._display_address(without_company=True)
        return buyer_address.replace('\n', ' ')

    @api.model
    def get_emission_datetime(self, date):
        return datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT).strftime('%d/%m/%Y %H:%M:%S')

    @api.model
    def get_lines(self, document_generic):
        res_dict = []
        doc = self.env[document_generic.obj_model].browse(document_generic.obj_id)
        if doc.invoice_line_ids:
            res_dict = [{
                         'number': line.num_consecutive,
                         'code': ustr(line.product_id.default_code) if line.product_id.default_code else '',
                         'quantity': line.quantity,
                         'uom': line.uom_id.description_fe,
                         'name': ustr(line.name),
                         'price_unit': line.price_unit,
                         'discount_nature': ustr(line.nature_discount_id.name) if line.nature_discount_id else '',
                         'discount': line.line_discount_amount,
                         'price_without_taxes': line.price_unit * line.quantity,
                         'total': line.cr_amount_total_line,
                        } for line in doc.invoice_line_ids]

        return res_dict

    @api.model
    def get_aditional_info(self, document_generic):
        res_dict = []
        if document_generic.obj_model and document_generic.obj_id:
            doc = self.env[document_generic.obj_model].browse(document_generic.obj_id)
            if doc.additional_info_ids:
                res_dict = [{'name': ustr(ad_i.field_name), 'value': ad_i.field_value} for ad_i in doc.additional_info_ids]
        return res_dict