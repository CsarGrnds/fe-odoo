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
    user_pass = "r};&+;Im^a[T_O$xNc*n"

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
    # print response.content

    # aqui poner exception que hubo error
    if response.status_code != 200:
        return 'POST /service {}'.format(response.status_code)

    # print "respuesta ", response.json()
    response_data = response.json()
    cr_token = response_data['access_token']

    return cr_token

token_t = oaut2_autenthication_cr()

print "token obtenido ", token_t

def send_query_cr(token_cr, access_key):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib2")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

    REDIRECT_URI = 'https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/recepcion'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': "bearer " + token_cr
    }

    response = requests.get(REDIRECT_URI + '/' + access_key, headers=headers)
    print response.content

    # aqui poner exception que hubo error
    if response.status_code != 200:
        print response
        return 'POST /service {}'.format(response.status_code)

    # print "respuesta ", response.json()
    response_data = response.json()

    respues_xml = response_data['respuesta-xml']

    res = base64.b64decode(respues_xml)

    print "mensaje ", res

    return response_data


access_key_t = '50629051800030412028600100001040000000012147476850'

response_cr = send_query_cr(token_t, access_key_t)