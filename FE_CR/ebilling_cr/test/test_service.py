import json
from subprocess import *
import subprocess
import simplejson

raw_xml_t = """<?xml version="1.0" encoding="utf-8"?>
<FacturaElectronica xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/facturaElectronica">
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
        <NombreComercial />
        <Ubicacion>
            <Provincia>1</Provincia>
            <Canton>01</Canton>
            <Distrito>01</Distrito>
            <Barrio>01</Barrio>
            <OtrasSenas />
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
            <UnidadMedidaComercial />
            <Detalle>Servicios profesionales</Detalle>
            <PrecioUnitario>150000.00000</PrecioUnitario>
            <MontoTotal>150000.00000</MontoTotal>
            <NaturalezaDescuento />
            <SubTotal>150000.00000</SubTotal>
            <MontoTotalLinea>150000.00000</MontoTotalLinea>
        </LineaDetalle>
    </DetalleServicio>
    <ResumenFactura>
        <CodigoMoneda>USD</CodigoMoneda>
        <TipoCambio>576.74000</TipoCambio>
        <TotalServGravados>0.00000</TotalServGravados>
        <TotalServExentos>150000.00000</TotalServExentos>
        <TotalMercanciasGravadas>0.00000</TotalMercanciasGravadas>
        <TotalMercanciasExentas>0.00000</TotalMercanciasExentas>
        <TotalGravado>0.00000</TotalGravado>
        <TotalExento>150000.00000</TotalExento>
        <TotalVenta>150000.00000</TotalVenta>
        <TotalDescuentos>0.00000</TotalDescuentos>
        <TotalVentaNeta>150000.00000</TotalVentaNeta>
        <TotalImpuesto>0.00000</TotalImpuesto>
        <TotalComprobante>150000.00000</TotalComprobante>
    </ResumenFactura>
    <Normativa>
        <NumeroResolucion>DGT-R-48-2016</NumeroResolucion>
        <FechaResolucion>20-02-2017 13:22:22</FechaResolucion>
    </Normativa>
    <Otros>
        <OtroTexto codigo="obs">BNCR $ 200-</OtroTexto>
    </Otros>
</FacturaElectronica>"""
# print raw_xml_t
raw_xml = raw_xml_t
jar_path = '/home/orlando/Escritorio/proyectos/soporte/project_medical_costa/repos/develop/solt-erp-multicompany/addons/medical_ebilling_cr/data/firmar-xades.jar'
key_store_pwd = '0786'
key_store_path = '/home/orlando/Escritorio/proyectos/soporte/project_medical_costa/repos/develop/solt-erp-multicompany/addons/medical_ebilling_cr/data/030412028623.p12'
fichero_xml = '/home/orlando/.local/share/Odoo/filestore/l10ncr/1_byuser_unsigned.xml'
fichero_firmado_xml = '/home/orlando/.local/share/Odoo/filestore/l10ncr/1_byuser_signed.xml'

# print "Ubicacion de archivo " + key_store_path

args = [jar_path, raw_xml_t, key_store_path, key_store_pwd]
try:
    subprocess.call(['java', '-jar',
                     jar_path, key_store_path,
                     key_store_pwd, fichero_xml, fichero_firmado_xml])
    # print "firmado ", signed_xml
except (Exception,) as e:
    print e
