import requests
import urlparse
import urllib2, urllib
import logging
import base64
import json
from StringIO import StringIO
import subprocess
from subprocess import *

import json
import xmltodict

# get token step 1 autenticacion para obtener token
def oaut2_autenthication_cr():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib2")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

    user_api = "cpf-03-0412-0286@stag.comprobanteselectronicos.go.cr"
    user_pass = "]_%_{!pRq[e+NI%YmN_r"

    ACCESS_TOKEN_URL = "https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token"

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data_send = {
        'grant_type': 'password',
        'client_id': 'api-stag',
        'client_secret': '',
        'username': user_api,
        'password': user_pass,
        'scope': ''
    }

    data_send['content'] = data_send

    response = requests.post(ACCESS_TOKEN_URL, data=data_send, headers=headers)
    print response.content

    # aqui poner exception que hubo error
    if response.status_code != 200:
        return 'POST /service {}'.format(response.status_code)

    # print "respuesta ", response.json()
    response_data = response.json()
    cr_token = response_data['access_token']

    return cr_token

token_t = oaut2_autenthication_cr()

print "token obtenido ", token_t
jar_path = '/home/orlando/Escritorio/proyectos/soporte/project_medical_costa/repos/develop/solt-erp-multicompany/addons/medical_ebilling_cr/data/xadessignercr.jar'
key_store_pwd = '0786'
key_store_path = '/home/orlando/Escritorio/proyectos/soporte/project_medical_costa/repos/develop/solt-erp-multicompany/addons/medical_ebilling_cr/data/030412028623.p12'
fichero_xml = '/home/orlando/.local/share/Odoo/filestore/l10ncr/1_byuser_unsigned.xml'
fichero_firmado_xml = '/home/orlando/.local/share/Odoo/filestore/l10ncr/1_byuser_signed.xml'

def send_edi_cr(token_cr, xml_sign):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib2")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True
    b = False
    with open(xml_sign) as file:
        f = file.read()
        b = bytearray(f)
        print "fichero ", b

    REDIRECT_URI = 'https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/recepcion'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': "bearer " + token_cr
    }

    jsonString = {}
    jsonString['clave'] = '50628041800030412028600100001010000000006199999999'
    jsonString['fecha'] = '2018-04-28T00:04:00'
    jsonString['emisor'] = {}
    jsonString['emisor']['tipoIdentificacion'] = "01"
    jsonString['emisor']['numeroIdentificacion'] = "136526987"
    jsonString['receptor'] = {}
    jsonString['receptor']['tipoIdentificacion'] = "02"
    jsonString['receptor']['numeroIdentificacion'] = "3001123208"
    jsonString['comprobanteXml'] = base64.b64encode(b)

    json_data = json.dumps(jsonString)

    response = requests.post(REDIRECT_URI, json=jsonString, headers=headers)
    print response.content

    # aqui poner exception que hubo error
    if response.status_code != 200:
        print response
        return 'POST /service {}'.format(response.status_code)

    print "respuesta ", response.json()
    response_data = response.json()

    return response_data


raw_xml_t = '/home/orlando/.local/share/Odoo/filestore/l10ncr/1_01_6_byuser_signed.xml'

response_cr = send_edi_cr(token_t, raw_xml_t)