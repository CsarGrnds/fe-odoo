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
    # logging.basicConfig()
    # logging.getLogger().setLevel(logging.DEBUG)
    # requests_log = logging.getLogger("requests.packages.urllib2")
    # requests_log.setLevel(logging.DEBUG)
    # requests_log.propagate = True

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
    # print response.content

    # aqui poner exception que hubo error
    if response.status_code != 200:
        return 'POST /service {}'.format(response.status_code)

    # print "respuesta ", response.json()
    response_data = response.json()
    cr_token = response_data['access_token']

    return cr_token

token_t = oaut2_autenthication_cr()

# print "token obtenido ", token_t

class comprobante_fe(object):
    clave = ''
    fecha = ''
    emisor = ''
    receptor = ''
    comprobanteXml = ''

    def __init__(self, clave, fecha, emisor, receptor, comprobanteXml):
        self.clave = clave
        self.fecha = fecha
        self.emisor = emisor
        self.receptor = receptor
        self.comprobanteXml = comprobanteXml

def send_edi_cr(token_cr, xml_sign):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib2")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

    # REDIRECT_URI = 'https://api.comprobanteselectronicos.go.cr/recepcion/v1'
    REDIRECT_URI = 'https://api.comprobanteselectronicos.go.cr/recepcion/v1/recepcion'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': "bearer " + token_cr
    }

    buf = StringIO()
    buf.write(xml_sign)

    # print "bytea -->", bytearray(xml_sign, 'utf-8')
    # xml_param = base64.standard_b64encode(bytes(xml_sign.encode('utf-8')))
    xml_param = base64.standard_b64encode(xml_sign.encode('utf-8'))

    jsonString = {}
    jsonString['clave'] = '50612101700020586086000100001010000000161100000642'
    jsonString['fecha'] = '2018-04-23T00:00:00-0600'
    jsonString['emisor'] = {}
    jsonString['emisor']['tipoIdentificacion'] = "01"
    jsonString['emisor']['numeroIdentificacion'] = "136526987"
    jsonString['receptor'] = {}
    jsonString['receptor']['tipoIdentificacion'] = "02"
    jsonString['receptor']['numeroIdentificacion'] = "3001123208"
    jsonString['comprobanteXml'] = xml_param
    # jsonString = {
    #     'clave': '50612101700020586086000100001010000000161100000642',
    #     'fecha': '2018-04-23T00:00:00-0600',
    #     'emisor': {
    #                   'tipoIdentificacion': "01",
    #                   'numeroIdentificacion': "136526987"
    #               },
    #     'receptor': {
    #                     'tipoIdentificacion': "02",
    #                     'numeroIdentificacion': "3001123208"
    #                 },
    #     'comprobanteXml': xml_param
    #
    # }



    otro_json = '{"clave":%s , "fecha": %s, "emisor": {"tipoIdentificacion":%s,"numeroIdentificacion":%s}, "receptor": {"tipoIdentificacion":%s,"numeroIdentificacion":%s}, "comprobanteXml":%s}' % ("50612101700020586086000100001010000000161100000642", "2018-04-23T00:00:00-0600", "01", "136526987", "02", "3001123208", xml_param)

    # print "json del xml ", otro_json

    json_data = json.dumps(jsonString)

    # print "de la class ", json_data


    response = requests.post(REDIRECT_URI, json=json_data, headers=headers)
    print response.content

    # aqui poner exception que hubo error
    if response.status_code != 200:
        print response
        return 'POST /service {}'.format(response.status_code)

    print "respuesta ", response.json()
    response_data = response.json()

    return response_data

# get token step 2 obtener token y enviar al tribunet
raw_xml_t = """<?xml version="1.0" encoding="utf-8" standalone="no"?><FacturaElectronica xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/facturaElectronica" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Clave>50612101700020586086000100001010000000161100000642</Clave>
    <NumeroConsecutivo>00100001010000000162</NumeroConsecutivo>
    <FechaEmision>2017-12-07T11:47:42.539375-06:00</FechaEmision>
    <Emisor>
        <Nombre>Jhon Moreira Baltodano</Nombre>
        <Identificacion>
            <Tipo>01</Tipo>
            <Numero>136526987</Numero>
        </Identificacion>
        <NombreComercial>SolutionsCR</NombreComercial>
        <Ubicacion>
            <Provincia>4</Provincia>
            <Canton>09</Canton>
            <Distrito>01</Distrito>
            <Barrio>01</Barrio>
            <OtrasSenas>SanJose, Guadalupe</OtrasSenas>
        </Ubicacion>
        <Telefono>
            <CodigoPais>506</CodigoPais>
            <NumTelefono>88768987</NumTelefono>
        </Telefono>
        <Fax>
            <CodigoPais>506</CodigoPais>
            <NumTelefono>00000000</NumTelefono>
        </Fax>
        <CorreoElectronico>jonh.m.10@gmail.com</CorreoElectronico>
    </Emisor>
    <Receptor>
        <Nombre>Dental Care</Nombre>
        <Identificacion>
            <Tipo>02</Tipo>
            <Numero>3001123208</Numero>
        </Identificacion>
        <NombreComercial/>
        <Ubicacion>
            <Provincia>1</Provincia>
            <Canton>01</Canton>
            <Distrito>01</Distrito>
            <Barrio>01</Barrio>
            <OtrasSenas/>
        </Ubicacion>
        <Telefono>
            <CodigoPais>506</CodigoPais>
            <NumTelefono>88888888</NumTelefono>
        </Telefono>
        <Fax>
            <CodigoPais>506</CodigoPais>
            <NumTelefono>506</NumTelefono>
        </Fax>
        <CorreoElectronico>info@dentalcare.com</CorreoElectronico>
    </Receptor>
    <CondicionVenta>02</CondicionVenta>
    <PlazoCredito>15</PlazoCredito>
    <MedioPago>04</MedioPago>
    <DetalleServicio>
        <LineaDetalle>
            <NumeroLinea>1</NumeroLinea>
            <Codigo>
                <Tipo>04</Tipo>
                <Codigo>3</Codigo>
            </Codigo>
            <Cantidad>1.000</Cantidad>
            <UnidadMedida>Unid</UnidadMedida>
            <UnidadMedidaComercial/>
            <Detalle>Servicios profesionales</Detalle>
            <PrecioUnitario>1.0</PrecioUnitario>
            <MontoTotal>1.0</MontoTotal>
            <NaturalezaDescuento/>
            <SubTotal>1.0</SubTotal>
            <MontoTotalLinea>1.0</MontoTotalLinea>
        </LineaDetalle>
    </DetalleServicio>
    <ResumenFactura>
        <CodigoMoneda>CRC</CodigoMoneda>
        <TipoCambio>1.0</TipoCambio>
        <TotalServGravados>0.00000</TotalServGravados>
        <TotalServExentos>1.00000</TotalServExentos>
        <TotalMercanciasGravadas>0.00000</TotalMercanciasGravadas>
        <TotalMercanciasExentas>0.00000</TotalMercanciasExentas>
        <TotalGravado>0.00000</TotalGravado>
        <TotalExento>1.00000</TotalExento>
        <TotalVenta>1.00000</TotalVenta>
        <TotalDescuentos>1.00000</TotalDescuentos>
        <TotalVentaNeta>1.00000</TotalVentaNeta>
        <TotalImpuesto>0.00000</TotalImpuesto>
        <TotalComprobante>1.00000</TotalComprobante>
    </ResumenFactura>
    <Normativa>
        <NumeroResolucion>DGT-R-48-2016</NumeroResolucion>
        <FechaResolucion>15-03-2018 16:29:50</FechaResolucion>
    </Normativa>
    <Otros>
        <OtroTexto codigo="obs">BNCR $ 1-</OtroTexto>
    </Otros>
<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="xmldsig-77150f93-a941-4bd0-a7b2-f81fd5c0c736">
<ds:SignedInfo>
<ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
<ds:Reference Id="xmldsig-77150f93-a941-4bd0-a7b2-f81fd5c0c736-ref0" URI="">
<ds:Transforms>
<ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
</ds:Transforms>
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>T5nM3VYfaBg6xe1KWPvEgfNhXKmt8CDKhuV2//7nENM=</ds:DigestValue>
</ds:Reference>
<ds:Reference URI="#xmldsig-77150f93-a941-4bd0-a7b2-f81fd5c0c736-keyinfo">
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>TngDIPlamcyE7FBFG+SnFVcMtElkJmL0cPhYxHdZSqo=</ds:DigestValue>
</ds:Reference>
<ds:Reference Type="http://uri.etsi.org/01903#SignedProperties" URI="#xmldsig-77150f93-a941-4bd0-a7b2-f81fd5c0c736-signedprops">
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>VffKoIq3/G3XvdJAU4MM2FUhJHbQfC2oirCGQSGhJAw=</ds:DigestValue>
</ds:Reference>
</ds:SignedInfo>
<ds:SignatureValue Id="xmldsig-77150f93-a941-4bd0-a7b2-f81fd5c0c736-sigvalue">
UET+k2d0HZcjwbKfZz89UsRbAYsyg5vJ/sSH0LZTPiIeH5/tcWqla4Vio2RkrTsuAxr/wn2rBQ0B
KacYtuXaF4myuN4w47ku1gjyeJA/7fYdekUH1L9Zz/8HrQ/VHF4UoQgl/H9ecuqMXWuAkzTLfTvM
XSzdEVi9NvwPp6iHHKWfYTFpQ7Mdd3hWUOldvXhbUn2fSQvaAYIvNfRrv6fcsDSFSfjiYAEODy8H
e+ovIqgcgtUMyAL2udxquJqfoqxKm4hzILzPLO2HsmJjUQpjxhEIZo+hXH+3qTTmjdvgug3hYp4T
2PQlHnsmglqFhjeoGTMQRdR3ug+wPqkX8aplhA==
</ds:SignatureValue>
<ds:KeyInfo Id="xmldsig-77150f93-a941-4bd0-a7b2-f81fd5c0c736-keyinfo">
<ds:X509Data>
<ds:X509Certificate>
MIIFQzCCAyugAwIBAgIGAWFUSyVeMA0GCSqGSIb3DQEBCwUAMFgxCzAJBgNVBAYTAkNSMR8wHQYD
VQQKDBZNSU5JU1RFUklPIERFIEhBQ0lFTkRBMQwwCgYDVQQLDANER1QxGjAYBgNVBAMMEUNBIFBF
UlNPTkEgRklTSUNBMB4XDTE4MDIwMjAyMTQyNloXDTIwMDIwMjAyMTQyNlowgZ8xGTAXBgNVBAUT
EENQRi0wMy0wNDEyLTAyODYxFTATBgNVBAQMDEZPTlNFQ0EgU0VBUzEUMBIGA1UEKgwLU09OSUEg
RUxFTkExCzAJBgNVBAYTAkNSMRcwFQYDVQQKDA5QRVJTT05BIEZJU0lDQTEMMAoGA1UECwwDQ1BG
MSEwHwYDVQQDDBhTT05JQSBFTEVOQSBGT05TRUNBIFNFQVMwggEiMA0GCSqGSIb3DQEBAQUAA4IB
DwAwggEKAoIBAQCQhmJtXj/gopuXt4YU8Owc88KYTxl3aoGCjyptyQXs4qYgjuVdks2NWnd4ktmp
ztnAb3m32H690a264G9LpTBQNNqfDFrvC4D4W6vgZVJ95UIlynZ38DhJd2w1LID5+nF3Ep+lKXOk
Px3mPEkeOWAIrmHS+JSd2eqrw9jy6wwBAfSJpj1VlMQ4D6VFPiqL8AYnCG7L+Z7qT/lZRHhS/YN0
GXgK191fPVNJiLYrH9vMrYD3JhR2sPps72ZOosM/ORqV8ToYyCz35nBoOkZ3CtfThduLP1iP+ule
/f1IyA2zN+d9NKlLE9HCiKViXNLLLPWQosdQk1U3FANByTtsY5Z5AgMBAAGjgcowgccwHwYDVR0j
BBgwFoAUE/ZqQQ3toiRF0ciUqEGDfGIla1kwHQYDVR0OBBYEFG0wodtU2QxlKxfbfVq2jU63GUND
MAsGA1UdDwQEAwIGwDATBgNVHSUEDDAKBggrBgEFBQcDBDBjBggrBgEFBQcBAQRXMFUwUwYIKwYB
BQUHMAKGR2h0dHBzOi8vcGtpLmNvbXByb2JhbnRlc2VsZWN0cm9uaWNvcy5nby5jci9wcm9kL2lu
dGVybWVkaWF0ZS1wZi1wZW0uY3J0MA0GCSqGSIb3DQEBCwUAA4ICAQAl1VRD98M1by0lCuFOz8t6
15gvre1szTr9SStjZQqLWp0DbKF0TeJIpVTxlXmzH36Dn/PB6cEt6LfgizXXLV5EmQqjToOEWNbl
5L26iTs9q5YYUrNXCJ8det3g/7Tm8T31VaUlbUt6Zlmjs6k794DctRK+RZkfdXZevQNQ0ifUgBXM
Q3s8Tl9K3vh1d3louv8y8PSzbAKXeCF//EZDazXHb8orUC2YXZypRgpfXCAQYP+DIopZbtydNNJH
Z84VtOvVZktUxR1ufKnQS9cCnCahLp93psyYE4427sT2+TwL9ZKUdD5/BeLDlmR2RQEDiynrdG/w
ti/J2pGu1FUlUtBgGbvC2mwuMtxR4eA+npYqZzp2stO5FTRi5OEGymgwAKZ7s+35lzoYENPKsab/
s/nlkS0o1+rdMzTnryp2C46JrWiBm7K2Hf4b0PqSkBhc8gsN23GXNj4Wg+rwciG44dHdtltEZDm6
ND3RaRuNp2Vo77buOS7NyKn6D6glLPITIkm6j1aXeCDHrxq9nPBY3HDwUZlA5tM3qTW+6zF3M3ZX
uNuCz0yXcsCMtlNR3FAfBeVB3ujv2HLG4+zA7G/7epTq7ayT/8aYS9DlpJKDCY3mJOHHV44lQQoL
slpxKR8+hQULrQ5seNAKiQuH/+q3uihXGZPPNIfw39coIKx2RxHkPA==
</ds:X509Certificate>
</ds:X509Data>
<ds:KeyValue>
<ds:RSAKeyValue>
<ds:Modulus>
kIZibV4/4KKbl7eGFPDsHPPCmE8Zd2qBgo8qbckF7OKmII7lXZLNjVp3eJLZqc7ZwG95t9h+vdGt
uuBvS6UwUDTanwxa7wuA+Fur4GVSfeVCJcp2d/A4SXdsNSyA+fpxdxKfpSlzpD8d5jxJHjlgCK5h
0viUndnqq8PY8usMAQH0iaY9VZTEOA+lRT4qi/AGJwhuy/me6k/5WUR4Uv2DdBl4CtfdXz1TSYi2
Kx/bzK2A9yYUdrD6bO9mTqLDPzkalfE6GMgs9+ZwaDpGdwrX04Xbiz9Yj/rpXv39SMgNszfnfTSp
SxPRwoilYlzSyyz1kKLHUJNVNxQDQck7bGOWeQ==
</ds:Modulus>
<ds:Exponent>AQAB</ds:Exponent>
</ds:RSAKeyValue>
</ds:KeyValue>
</ds:KeyInfo>
<ds:Object><xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#" Target="#xmldsig-77150f93-a941-4bd0-a7b2-f81fd5c0c736"><xades:SignedProperties Id="xmldsig-77150f93-a941-4bd0-a7b2-f81fd5c0c736-signedprops"><xades:SignedSignatureProperties><xades:SigningTime>2018-04-10T18:28:23.754-05:00</xades:SigningTime><xades:SigningCertificate><xades:Cert><xades:CertDigest><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>cJVyOqt12EL5DgnLnjzQzcTWjy+MSSthzRNq608Mndk=</ds:DigestValue></xades:CertDigest><xades:IssuerSerial><ds:X509IssuerName>CN=CA PERSONA FISICA,OU=DGT,O=MINISTERIO DE HACIENDA,C=CR</ds:X509IssuerName><ds:X509SerialNumber>1517537666398</ds:X509SerialNumber></xades:IssuerSerial></xades:Cert><xades:Cert><xades:CertDigest><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>NzB0r3n5yNlK1dC9msmXtfCHvFbS1s1H4RpQUJ6oa+I=</ds:DigestValue></xades:CertDigest><xades:IssuerSerial><ds:X509IssuerName>CN=CA RAIZ MINISTERIO DE HACIENDA,OU=DGT,O=MINISTERIO DE HACIENDA,C=CR</ds:X509IssuerName><ds:X509SerialNumber>1487214526</ds:X509SerialNumber></xades:IssuerSerial></xades:Cert><xades:Cert><xades:CertDigest><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>Of5KHU6gBs6L7f0Qjul5r1yROpASEoiiN51kLFGSmRc=</ds:DigestValue></xades:CertDigest><xades:IssuerSerial><ds:X509IssuerName>CN=CA RAIZ MINISTERIO DE HACIENDA,OU=DGT,O=MINISTERIO DE HACIENDA,C=CR</ds:X509IssuerName><ds:X509SerialNumber>1487214316</ds:X509SerialNumber></xades:IssuerSerial></xades:Cert></xades:SigningCertificate><xades:SignaturePolicyIdentifier><xades:SignaturePolicyId><xades:SigPolicyId><xades:Identifier>https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/Resolucion%20Comprobantes%20Electronicos%20%20DGT-R-48-2016.pdf</xades:Identifier></xades:SigPolicyId><xades:SigPolicyHash><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=</ds:DigestValue></xades:SigPolicyHash></xades:SignaturePolicyId></xades:SignaturePolicyIdentifier></xades:SignedSignatureProperties><xades:SignedDataObjectProperties><xades:CommitmentTypeIndication><xades:CommitmentTypeId><xades:Identifier>http://uri.etsi.org/01903/v1.2.2#ProofOfOrigin</xades:Identifier><xades:Description>Indicates that the signer recognizes to have created, approved and sent the signed data object</xades:Description></xades:CommitmentTypeId><xades:AllSignedDataObjects/></xades:CommitmentTypeIndication></xades:SignedDataObjectProperties></xades:SignedProperties></xades:QualifyingProperties></ds:Object>
</ds:Signature></FacturaElectronica>"""

response_cr = send_edi_cr(token_t, raw_xml_t)

print "respuesta de envio ", response_cr



