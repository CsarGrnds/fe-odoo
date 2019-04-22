import requests
import urlparse
import urllib2, urllib
import logging
import base64
import json
from StringIO import StringIO

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

    REDIRECT_URI = 'https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/'
    AUTHORIZE_URL = "https://idp.comprobanteselectronicos.go.cr/auth"
    ACCESS_TOKEN_URL = "https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token"

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data_send = {
        'grant_type': 'password',
        'client_id': 'api-prod',
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


clave = '50625041800030412028600100001010000000005199999999'
QUERY_URL = 'https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/'

token_cr = token_t

headers = {
    'Authorization': "bearer " + token_cr
}


url_last = QUERY_URL + "/recepcion/" + clave
print "query ", url_last, token_cr


response = requests.post(url_last, headers=headers)
print response.headers

# aqui poner exception que hubo error
if response.status_code != 200:
    print 'POST /service {}'.format(response.status_code)

# print "respuesta ", response.json()
# response_data = response.json()



