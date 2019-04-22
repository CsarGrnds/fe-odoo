# -*- coding: utf-'8' "-*-"
import logging

from openerp import api, fields, models
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp.exceptions import ValidationError, UserError, RedirectWarning
from openerp.http import serialize_exception
from datetime import datetime, timedelta
import os
import re
from openerp.tools import config
import base64, tempfile
from xml.dom import minidom
import requests
import subprocess
from subprocess import *
from StringIO import StringIO
from mako.template import Template
import time
from threading import Thread
from lxml import etree
import xml.etree.ElementTree
from pytz import timezone

_logger = logging.getLogger(__name__)

def check_python_library(library):
    try:
        __import__(library)
    except:
        return False
    return True

EMISSION_TYPE = [
    ('1', 'Pruebas'),
    ('2', 'Producción'),
]

class electronic_biller(models.Model):
    _name = 'electronic.biller.cr'
    _description = 'Electronic Biller CR'

    def _get_providers(self):
        return [('base', 'Default'), ('medical_cr', 'Medical Costa Rica')]

    # indirection to ease inheritance
    _provider_selection = lambda self, *args, **kwargs: self._get_providers(*args, **kwargs)
    active = fields.Boolean('Activo', default=True)
    version = fields.Char('Documentation version', select=True)
    current_regulation_rs_number = fields.Char('Current Regulations - Resolution Number', size=13, select=True)
    current_regulation_rs_date = fields.Char('Current Regulations - Resolution Date', size=20, select=True)
    current_regulation_rs_date_text = fields.Char('Current Regulations - Resolution Date Text', select=True)
    name = fields.Char('Name')
    environment = fields.Selection([('test', 'Test'), ('prod', 'Production')], string='Environment', index=True, default='test')
    provider = fields.Selection(_provider_selection, string='Provider', index=True, default='base', select=True)
    company_id = fields.Many2one('res.company', 'Company', default=api.model(lambda self: self.env.user.company_id))
    company_name = fields.Char('Company Name')
    host = fields.Char('Servidor', required=True, copy=False)
    port = fields.Integer('Puerto', copy=False)
    host_test = fields.Char('Servidor test', copy=False)
    port_test = fields.Integer('Puerto test', copy=False)
    username = fields.Char('Usuario', copy=False)
    client_id_test = fields.Char('Id Cliente', copy=False, default='api-prod')
    client_id = fields.Char('Id Cliente', copy=False, default='api-prod')
    client_password = fields.Char(string='Client Password')
    password = fields.Char('Contraseña', copy=False)
    file_mode = fields.Selection([('path', 'Path del archivo'),
                                  ('base64', 'Binario'),
                                  ('text', 'Texto')], 'Forma del archivo', required=True, default='text')
    invoice_template = fields.Text('Invoices')
    refund_template = fields.Text('Credit Notes')
    debit_note_template = fields.Text('Debit Notes')
    electronic_ticket_template = fields.Text('Electronic Ticket')
    accuse_acceptance_template = fields.Text('Accuse Acceptance')
    rejection_of_document_template = fields.Text('Rejection of Documents')
    library = fields.Char('Librería', required=False,
                          help='Define la librería python que usará como canal de conexión.')
    send_doc = fields.Text('Método para enviar un documento', required=False)
    check_doc = fields.Text('Método para comprobar un documento', required=False)
    auth_endpoint_test = fields.Char(string='URL de Autenticación Pruebas(Token)',
                                     default='https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token')
    auth_endpoint_prod = fields.Char(string='URL de Autenticación Producción(Token)',
                                     default='https://idp.comprobanteselectronicos.go.cr/auth/realms/rut/protocol/openid-connect/token')

    scope = fields.Char()  # OAUth user data desired to access
    validation_endpoint = fields.Char(string='Validation URL')  # OAuth provider URL to validate tokens
    data_endpoint = fields.Char(string='Data URL')
    key_store_file = fields.Binary(string='Archivo LLave', attachment=True)
    key_store_pswd = fields.Char(string='Password de la Llave', size=300, required=False)
    key_store_path = fields.Char(string='Ruta de la llave', size=300, required=False)
    use_jar = fields.Boolean('Use Jar', default=True)
    jar_path = fields.Char('Jar Path')
    emission_type = fields.Selection(EMISSION_TYPE, 'Tipo de Emision', default='1',  required=True)
    mh_receipt_test_wsdl = fields.Char('URL Recepción - Pruebas', size=300, default='https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/',required=False)
    mh_receipt_prod_wsdl = fields.Char('URL Recepción - Producción', size=300, default='https://api.comprobanteselectronicos.go.cr/recepcion/v1/', required=False)
    mh_check_test_wsdl = fields.Char('URL Chequeo - Pruebas', size=300,
                                      default='https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/',required=False)

    mh_check_prod_wsdl = fields.Char('URL Chequeo - Producción', size=300,
                                      default='https://api.comprobanteselectronicos.go.cr/recepcion/v1/', required=False)
    version_doc = fields.Char('Versión del Documento', default='Version 4.2')

    def _display_address(self, address, without_company=False):

        if hasattr(self, '%s_display_address' % self.provider):
            return getattr(self, '%s_display_address' % self.provider)(address, without_company=without_company)

        address_format = address.country_id and address.country_id.address_format or \
              "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"
        args = {
            'state_code': address.state_id and address.state_id.code or '',
            'state_name': address.state_id and address.state_id.name or '',
            'country_code': address.country_id and address.country_id.code or '',
            'country_name': address.country_id and address.country_id.name or '',
        }
        for field in address._address_fields():
            args[field] = getattr(address, field) or ''
        if without_company:
            args['company_name'] = ''
        return address_format % args

    def get_dict_data(self, vals):
        if hasattr(self, '%s_get_dict_data' % vals['provider']):
            return getattr(self, '%s_get_dict_data' % vals['provider'])(vals)

        return {
            'name': vals['name'],
            'environment': vals['environment'],
            'provider': vals['provider'],
            'context_type': 'center',
        }

    def get_wdict_data(self, vals):
        self.ensure_one()
        if hasattr(self, '%s_get_wdict_data' % self.provider):
            return getattr(self, '%s_get_wdict_data' % self.provider)(vals)

        return {
        }

    def base_get_dict_data(self, vals):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        return {
            'name': vals['name'],
            'environment': vals['environment'],
            'provider': vals['provider'],
            'context_type': 'center',
            'instance': base_url,
            'company_name': self.env.user.company_id.name,
        }

    def base_get_wdict_data(self, vals):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        return {
            'name': vals.get('name', self.name),
            'environment': vals.get('environment', self.environment),
            'provider': vals.get('provider', self.provider),
            'context_type': 'center',
            'instance': base_url,
            'company_name': self.env.user.company_id.name,
        }

    @api.model
    def create(self, vals):
        biller_id = super(electronic_biller, self).create(vals)
        return biller_id

    @api.multi
    def write(self, vals):
        res = super(electronic_biller, self).write(vals)
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        return res

    @api.multi
    def send_document(self, doc, number):
        description = doc._name + (('.%s' % doc.type) if hasattr(doc, 'type') else '')
        description += (('.%s' % doc.tipo_factura) if hasattr(doc, 'tipo_factura') else '')
        messages = []
        safe_dict = {
            self.library: __import__(self.library),
            'datetime': datetime,
            'server': self,
            'doc': doc,
            'ebi_doc': self.generate_doc(doc),
            'doc_name': number,
            'description': description,
            'ValidationError': ValidationError,
            'hasattr': hasattr,
            'messages': messages
        }
        if self.file_mode == 'path':
            with tempfile.NamedTemporaryFile() as f:
                f.write(safe_dict['ebi_doc'].encode('utf-8'))
                f.flush()
                safe_dict['ebi_doc'] = f.name
                try:
                    exec (self.send_doc, {"__builtins__": None}, safe_dict)
                except Exception as e:
                    raise e
        else:
            try:
                exec (self.send_doc, {"__builtins__": None}, safe_dict)
            except Exception as e:
                raise e
        for message in messages:
            message.update(res_id=doc.id, model_name=doc._name)
            self.env['ebi.doc.message'].create(message)

    @api.multi
    def check_document(self, doc, number):
        description = doc._name + (('.%s' % doc.type) if hasattr(doc, 'type') else '')
        description += (('.%s' % doc.ebi_voucher_type) if hasattr(doc, 'tipo_factura') else '')
        attachments, messages = [], []
        safe_dict = {
            self.library: __import__(self.library),
            'datetime': datetime,
            'server': self,
            'doc': doc,
            'doc_name': number,
            'description': description,
            'documents': attachments,
            'ValidationError': ValidationError,
            'hasattr': hasattr,
            'messages': messages
        }
        try:
            exec (self.check_doc, {"__builtins__": None}, safe_dict)
        except Exception as e:
            raise e
        for attach_name, attachment in attachments:
            if attach_name.split('.')[-1] == 'xml':
                vals = self.xml_vals(attachment)
                if vals.get('ebi_state', '').upper() == 'AUTORIZADO' and vals.get('ebi_auth_key'):
                    doc.write(dict(vals, **{'ebi_state': 'auth'}))
                else:
                    return
            self.env['ir.attachment'].create({
                'name': attach_name,
                'type': 'binary',
                'datas': base64.encodestring(attachment),
                'datas_fname': attach_name,
                'res_model': doc._name,
                'res_id': doc.id
            })
        for message in messages:
            message.update(res_id=doc.id, model_name=doc._name, access_key=doc.ebi_access_key)
            self.env['ebi.doc.message'].create(message)

    @api.model
    def xml_vals(self, xml, doc_string=True):
        if doc_string:
            dom = minidom.parseString(xml)
        else:
            dom = minidom.parse(xml)

        def get_xml_value(dom, completeName):
            res = None
            tagName, sep, completeName = completeName.partition('.')
            elements = dom.getElementsByTagName(tagName)
            if len(elements) != 0:
                res = elements[0].childNodes[0].nodeValue
                if completeName:
                    res = get_xml_value(elements[0], completeName)
            return res

        return {
            'ebi_access_key': get_xml_value(dom, 'claveAccesoConsultada'),
            # 'num_comp': get_xml_value(dom, 'numeroComprobantes'),
            'ebi_state': get_xml_value(dom, 'autorizaciones.autorizacion.estado'),
            'ebi_auth_key': get_xml_value(dom, 'autorizaciones.autorizacion.numeroAutorizacion'),
            'ebi_auth_date': get_xml_value(dom, 'autorizaciones.autorizacion.fechaAutorizacion'),
            'ebi_environment': get_xml_value(dom, 'autorizaciones.autorizacion.ambiente'),
            # 'ebi_document': get_xml_value(dom, 'autorizaciones.autorizacion.comprobante'),
        }

    @api.model
    def oaut2_autenthication_cr(self, document_generic):
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib2")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

        user_api = document_generic.company_id.mh_oauth_username
        user_pass = document_generic.company_id.mh_oauth_password
        ACCESS_TOKEN_URL = self.auth_endpoint_test

        if self.environment == 'prod':
            ACCESS_TOKEN_URL = self.auth_endpoint_prod

        cl_id = self.client_id_test

        if self.environment == 'prod':
            cl_id = self.client_id

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data_send = {
            'grant_type': 'password',
            'client_id': cl_id,
            'client_secret': '',
            'username': user_api,
            'password': user_pass,
            'scope': ''
        }

        # print "data de token ", data_send

        data_send['content'] = data_send

        response = requests.post(ACCESS_TOKEN_URL, data=data_send, headers=headers)
        # print response.content

        # aqui poner exception que hubo error
        if response.status_code != 200:
            _logger.error("---->A ocurrido un error en la autenticacion: " + response.content)
            if response.status_code == 401:
                raise UserError(_("A ocurrido un error en la autenticación, las credenciales no están autorizadas."))
            raise UserError(_("A ocurrido un error en la autenticación: ") + response.content)

        # print "respuesta ", response.json()
        response_data = response.json()
        cr_token = response_data['access_token']

        return cr_token

    @api.model
    def _filestore(self):
        return config.filestore(self._cr.dbname)

    @api.model
    def _full_path(self, path):
        path = re.sub('[.]', '.', path)
        path = path.strip('/\\')
        return os.path.join(self._filestore(), path)

    @api.model
    def query_cr(self, document_generic):
        self.ensure_one()
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib2")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

        clave = document_generic.mh_access_key
        QUERY_URL = self.mh_check_test_wsdl

        if self.environment == 'prod':
            QUERY_URL = self.mh_check_prod_wsdl

        token_cr = self.oaut2_autenthication_cr(document_generic)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': "bearer " + token_cr
        }

        url_last = QUERY_URL + "recepcion/" + clave
        # print "query ", url_last, token_cr

        response = requests.get(url_last, headers=headers)
        # print response.content

        if response.status_code != 200:
            _logger.error("---->A ocurrido un error en la consulta del comprobante: " + response.content)
            if response.status_code in [400, 401]:
                text_excp_ = str(response.headers._store['x-error-cause'][1])
                message_title = "ERROR"
                message_msg = text_excp_
                state = 'ERROR'
                res_id = document_generic.obj_id
                model_name = document_generic.obj_model
                sequence_msg = len(document_generic.env[model_name].browse(res_id).ebi_messages_ids) + 1
                message_data = {
                    'title': message_title,
                    'message': message_msg,
                    'state': state,
                    'access_key': document_generic.mh_access_key,
                    'res_id': res_id,
                    'model_name': model_name,
                    'type': 'interno',
                    'sequence': sequence_msg,
                    'edig_id': document_generic.id,
                    'invoice_id': document_generic.invoice_id.id,
                }
                self.env['ebi.doc.message'].create(message_data)
                document_generic.message_post(body=message_title + ' - ' + message_msg)
                document_generic.invoice_id.message_post(body=message_title + ' - ' + message_msg)
                return self.env['cr.wizard.message'].generated_message(message_msg, name=message_title)

            text_excp_ = "Estado " + str(response.status_code) + " - "+ str(response.headers)
            message_title = "ERROR"
            message_msg = text_excp_
            state = 'ERROR'
            res_id = document_generic.obj_id
            model_name = document_generic.obj_model
            sequence_msg = len(document_generic.env[model_name].browse(res_id).ebi_messages_ids) + 1
            message_data = {
                'title': message_title,
                'message': message_msg,
                'state': state,
                'access_key': document_generic.mh_access_key,
                'res_id': res_id,
                'model_name': model_name,
                'type': 'interno',
                'sequence': sequence_msg,
                'edig_id': document_generic.id,
                'invoice_id': document_generic.invoice_id.id,
            }
            self.env['ebi.doc.message'].create(message_data)
            document_generic.message_post(body=message_title + ' - ' + message_msg)
            document_generic.invoice_id.message_post(body=message_title + ' - ' + message_msg)
            return self.env['cr.wizard.message'].generated_message(message_msg, name=message_title)
            # raise UserError(_("A ocurrido un error en la consulta del comprobante: ") + response.content)

        # print "respuesta ", response.json()
        _logger.error("---->Respuesta de la consulta del comprobante: " + str(response) + " ->>> Contenido: " + str(response.content))
        response_data = False
        res = False
        if response.json():
            response_data = response.json()
            if response_data.get('ind-estado', False):
                if response_data['ind-estado'] in ['rechazado', 'aceptado']:
                    respues_xml = response_data['respuesta-xml']
                    res = base64.b64decode(respues_xml)
                    document_generic.response_xml = res
                    message_doc = etree.XML(str(res))
                    # print "xml complet", message_doc

                    # root = message_doc.getroot()
                    mensaje_text_extract = res
                    message_type = ''
                    for child in message_doc.iter():
                        # print "contenido tag ", str(child.tag).split('}')
                        if 'DetalleMensaje' in str(child.tag):
                            mensaje_text_extract = child.text
                        if 'Mensaje' == str(child.tag).split('}')[1]:
                            message_type = child.text

                    text_excp_ = mensaje_text_extract
                    message_title = "ERROR"
                    message_msg = text_excp_
                    status = 'ERROR'
                    date_auth = ''

                    if int(message_type) == 1:
                        message_title = "HACIENDA: COMPROBANTE ACEPTADO"
                        status = 'ACEPTADO'
                        date_auth = ''

                    if int(message_type) == 3:
                        message_title = "HACIENDA: COMPROBANTE RECHAZADO"
                        status = 'RECHAZADO'

                    document_generic.update_status(status, date_auth, message_msg)
                else:
                    if response_data['ind-estado'] == 'error':
                        text_excp_ = "HACIENDA DEVOLVIO ERROR EN EL ENVIO, SIN DETALLE"
                        message_title = "ERROR"
                        message_msg = text_excp_
                        status = 'ERROR'
                        date_auth = ''
                        message_title = "HACIENDA: COMPROBANTE RECHAZADO CON ERROR"
                        # status = 'RECHAZADO'
                        res = document_generic.update_status(status, date_auth, message_msg)
                        # return self.env['cr.wizard.message'].generated_message(message_msg, name=message_title)

        return res

    @api.model
    def date_format_doc(self, date_t, format='%Y-%m-%dT%H:%M:%S'):
        # date = datetime.strptime(date_t, '%Y-%m-%d')
        tzinfo = timezone('America/Costa_Rica')
        start_date = datetime.strptime(date_t, '%Y-%m-%d %H:%M:%S')
        diffHoraria = int(tzinfo.localize(start_date).strftime('%z')) / 100
        start_date = start_date + timedelta(hours=diffHoraria)
        return start_date.strftime(format)

    @api.multi
    def send_signed_xml(self, document_generic, raise_error=False):
        self.ensure_one()
        fname_signed_xml = str(self.env.user.id) + '_' + str(document_generic.invoice_id.ebi_voucher_type) + '_' + str(document_generic.invoice_id.id) + '_byuser_signed.xml'
        full_path_signed_xml = self._full_path(fname_signed_xml)

        REDIRECT_URI = self.mh_receipt_test_wsdl
        if self.environment == 'prod':
            REDIRECT_URI = self.mh_receipt_prod_wsdl

        token_cr = self.oaut2_autenthication_cr(document_generic)

        try:
            byt_file = False
            with open(full_path_signed_xml) as file:
                f = file.read()
                byt_file = bytearray(f)

            headers = {
                'Content-Type': 'application/json',
                'Authorization': "bearer " + token_cr
            }

            # date_doc = document_generic.invoice_id.date_invoice
            date_doc = document_generic.invoice_id.ebi_send_date
            date_convert = self.date_format_doc(date_doc)
            # print "fecha de doc", date_convert

            jsonString = {}
            jsonString['clave'] = document_generic.invoice_id.ebi_access_key
            jsonString['fecha'] = date_convert
            jsonString['emisor'] = {}
            jsonString['emisor']['tipoIdentificacion'] = document_generic.invoice_id.company_id.partner_id.identification_type
            jsonString['emisor']['numeroIdentificacion'] = document_generic.invoice_id.company_id.partner_id.identification_cr
            jsonString['receptor'] = {}
            jsonString['receptor']['tipoIdentificacion'] = document_generic.invoice_id.identification_type
            jsonString['receptor']['numeroIdentificacion'] = document_generic.invoice_id.identification_cr
            jsonString['comprobanteXml'] = base64.b64encode(byt_file)


            response = requests.post(REDIRECT_URI + 'recepcion', json=jsonString, headers=headers)
        except (Exception,) as e:
            _logger.error(serialize_exception(e))
            _logger.info('Error %s' % str(e))
            raise UserError(_("A ocurrido un error enviando el xml "))

        print 'POST /service {}'.format(response.status_code)
        _logger.info('Respuesta Valiacion %s' % str(response))
        _logger.info('Contenido Respuesta Valiacion %s' % str(response.content))

        # aqui poner exception que hubo error
        if response.status_code != 200:
            _logger.error("---->A ocurrido un error enviando el comprobante: " + response.content)
            if response.status_code in [400, 401]:
                text_excp_ = str(response.headers._store['x-error-cause'][1])
                message_title = "ERROR"
                message_msg = text_excp_
                state = 'ERROR'
                res_id = document_generic.obj_id
                model_name = document_generic.obj_model
                sequence_msg = len(document_generic.env[model_name].browse(res_id).ebi_messages_ids) + 1
                message_data = {
                    'title': message_title,
                    'message': message_msg,
                    'state': state,
                    'access_key': document_generic.mh_access_key,
                    'res_id': res_id,
                    'model_name': model_name,
                    'type': 'interno',
                    'sequence': sequence_msg,
                    'edig_id': document_generic.id,
                    'invoice_id': document_generic.invoice_id.id,
                }
                self.env['ebi.doc.message'].create(message_data)
                document_generic.message_post(body=message_title + ' - ' + message_msg)
                document_generic.invoice_id.message_post(body=message_title + ' - ' + message_msg)
                return self.env['cr.wizard.message'].generated_message(message_msg, name=message_title)
                # raise ValidationError(
                #     _("A ocurrido un error enviando el comprobante: ") + str(response.headers._store['x-error-cause'][1]))

            # if response.status_code in [202]:
            #     raise ValidationError(
            #         _("A ocurrido un error enviando el comprobante: ") + str(
            #             response.headers))
            if response.status_code not in [202]:
                text_excp_ = "Estado " + str(response.status_code) + " - " + str(response.headers)
                message_title = "ERROR"
                message_msg = text_excp_
                state = 'ERROR'
                res_id = document_generic.obj_id
                model_name = document_generic.obj_model
                sequence_msg = len(document_generic.env[model_name].browse(res_id).ebi_messages_ids) + 1
                message_data = {
                    'title': message_title,
                    'message': message_msg,
                    'state': state,
                    'access_key': document_generic.mh_access_key,
                    'res_id': res_id,
                    'model_name': model_name,
                    'type': 'interno',
                    'sequence': sequence_msg,
                    'edig_id': document_generic.id,
                    'invoice_id': document_generic.invoice_id.id,
                }
                self.env['ebi.doc.message'].create(message_data)
                document_generic.message_post(body=message_title + ' - ' + message_msg)
                document_generic.invoice_id.message_post(body=message_title + ' - ' + message_msg)
                return self.env['cr.wizard.message'].generated_message(message_msg, name=message_title)
                # raise ValidationError(
                #     _("A ocurrido un error enviando el comprobante: ") + str(response.headers))

        _logger.error("Respuesta " + ustr(response.content))

        _logger.info('LLAMANDO SERVICIO verificar estado %s' % str(datetime.now()))
        count = 0
        timeout = False
        time.sleep(50L)
        response_query = self.query_cr(document_generic)
        if type(response_query) is dict:
            return dict(response_query)
        # print "respuesta del estado", response_query
        return response_query

    @api.multi
    def resend_document(self, document_generic, raise_error=False):
        self.ensure_one()
        response_query = self.query_cr(document_generic)
        print "respuesta del estado", response_query
        return response_query

    @api.multi
    def get_status_documents(self):
        self.ensure_one()
        response_query = self.query_cr('')
        print "respuesta del estado", response_query
        return response_query