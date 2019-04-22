import json
from subprocess import *
import subprocess
import simplejson

jar_path = '/home/orlando/Escritorio/proyectos/soporte/project_medical_costa/repos/develop/solt-erp-multicompany/addons/medical_ebilling_cr/data/xadessignercr.jar'
key_store_pwd = '0786'
# key_store_path = '/home/orlando/Escritorio/proyectos/soporte/project_medical_costa/repos/develop/solt-erp-multicompany/addons/medical_ebilling_cr/data/p12/030412028623.p12'
key_store_path = '/home/orlando/.local/share/Odoo/filestore/crtest/bd/bdf47141134be4bf836c876346e53d299b075e55'
fichero_xml = '/home/orlando/.local/share/Odoo/filestore/l10ncr/1_01_6_byuser_unsigned.xml'
fichero_firmado_xml = '/home/orlando/.local/share/Odoo/filestore/l10ncr/1_01_6_byuser_signed.xml'

# print "Ubicacion de archivo " + key_store_path
print "--->inicia firma <---"
args = [jar_path, key_store_path, key_store_pwd]
try:
    subprocess.call(['java', '-Dfile.encoding=UTF8', '-jar', jar_path, 'sign',
                     key_store_path, key_store_pwd, fichero_xml, fichero_firmado_xml])
    # print "firmado ", signed_xml
except (Exception,) as e:
    print "Error 1", e
print "--->fin firma <---"
# enviar
# print "--->inicia enviar <---"
# user_api = "cpf-03-0412-0286@prod.comprobanteselectronicos.go.cr"
# user_pass = "]#+UiixN[]y))N}q-u}X"
# REDIRECT_URI = 'https://api.comprobanteselectronicos.go.cr/recepcion/v1/'
# args = [jar_path, key_store_path, key_store_pwd]
# try:
#     subprocess.call(['java', '-jar', jar_path, 'send',
#                      REDIRECT_URI, fichero_firmado_xml, user_api, user_pass])
#     # print "firmado ", signed_xml
# except (Exception,) as e:
#     print "Error 2", e
# print "--->fin enviar <---"

# consultar el comprobante
# print "--->inicia consulta <---"
# QUERY_URI = 'https://api.comprobanteselectronicos.go.cr/recepcion/v1/'
# args = [jar_path, key_store_path, key_store_pwd]
# try:
#     subprocess.call(['java', '-jar', jar_path, 'query',
#                      QUERY_URI, fichero_firmado_xml, user_api, user_pass])
#     # print "firmado ", signed_xml
# except (Exception,) as e:
#     print "Error 3", e
# print "--->fin consulta <---"


