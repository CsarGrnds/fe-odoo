import requests
import urlparse
import urllib2, urllib
import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib2")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

user_api = "cpf-03-0412-0286@prod.comprobanteselectronicos.go.cr"
user_pass = "]#+UiixN[]y))N}q-u}X"

REDIRECT_URI = 'https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/'
AUTHORIZE_URL = "https://idp.comprobanteselectronicos.go.cr/auth"
ACCESS_TOKEN_URL = "https://idp.comprobanteselectronicos.go.cr/auth/realms/rut/protocol/openid-connect/token"

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

print response.text
# print response.content

if response.status_code != 200:
    print 'GET /service {}'.format(response.status_code)