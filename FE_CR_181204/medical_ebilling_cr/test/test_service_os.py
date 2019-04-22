import json
from subprocess import *
import simplejson

raw_xml_t = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<FacturaElectronica xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/facturaElectronica" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Clave>506220418114490214000000000214</Clave>
    <NumeroConsecutivo>False</NumeroConsecutivo>
    <FechaEmision>22/04/2018</FechaEmision>
    <Emisor>
        <Nombre>My Company</Nombre>
        <Identificacion>
            <Tipo>100</Tipo>
            <Numero>114490214</Numero>
        </Identificacion>
        <NombreComercial>Administrator</NombreComercial>
        <Ubicacion>
            <Provincia>False</Provincia>
            <Canton>False</Canton>
            <Distrito>False</Distrito>
            <Barrio>False</Barrio>
            <OtrasSenas>False</OtrasSenas>
        </Ubicacion>
        <Telefono>
            <CodigoPais>False</CodigoPais>
            <NumTelefono>False</NumTelefono>
        </Telefono>
        <CorreoElectronico>info@yourcompany.com</CorreoElectronico>
    </Emisor>
    <Receptor>
        <Nombre>c1</Nombre>
        <Identificacion>
            <Tipo>100</Tipo>
            <Numero>114490212</Numero>
        </Identificacion>
        <NombreComercial>c1</NombreComercial>
        <Ubicacion>
            <Provincia>False</Provincia>
            <Canton>False</Canton>
            <Distrito>False</Distrito>
            <Barrio>False</Barrio>
            <OtrasSenas>False</OtrasSenas>
        </Ubicacion>
        <Telefono>
            <CodigoPais>False</CodigoPais>
            <NumTelefono>False</NumTelefono>
        </Telefono>
        <CorreoElectronico>pepe@gmail.com</CorreoElectronico>
    </Receptor>
    <CondicionVenta>01</CondicionVenta>
    <PlazoCredito>False</PlazoCredito>
        <MedioPago>False</MedioPago>
    <DetalleServicio>
         <LineaDetalle>
              <NumeroLinea>1</NumeroLinea>
                <Codigo>
                    <Tipo>False</Tipo>
                    <Codigo>001</Codigo>
                </Codigo>
              <Cantidad>1.0</Cantidad>
              <UnidadMedida>Unidad(es)</UnidadMedida>
              <UnidadMedidaComercial>False</UnidadMedidaComercial>
              <Detalle>p1</Detalle>
              <PrecioUnitario>5.0</PrecioUnitario>
              <MontoTotal>5.0</MontoTotal>
              <SubTotal>5.0</SubTotal>
                  <Impuesto>
                        <Codigo>False</Codigo>
                        <Tarifa>13.0</Tarifa>
                        <Monto>0.65</Monto>
                  </Impuesto>
              <MontoTotalLinea>0.0</MontoTotalLinea>
         </LineaDetalle>
    </DetalleServicio>
    <ResumenFactura>
        <CodigoMoneda>CRC</CodigoMoneda>
        <TipoCambio>1.0</TipoCambio>
        <TotalServGravados>0.0</TotalServGravados>
        <TotalServExentos>0.0</TotalServExentos>
        <TotalMercanciasGravadas>0.0</TotalMercanciasGravadas>
        <TotalMercanciasExentas>0.0</TotalMercanciasExentas>
        <TotalGravado>0.0</TotalGravado>
        <TotalExento>0.0</TotalExento>
        <TotalVenta>0.0</TotalVenta>
        <TotalDescuentos>0.0</TotalDescuentos>
        <TotalVentaNeta>0.0</TotalVentaNeta>
        <TotalImpuesto>0.0</TotalImpuesto>
        <TotalComprobante>0.0</TotalComprobante>
    </ResumenFactura>
    <Normativa>
        <NumeroResolucion>DGT-R-48-2016</NumeroResolucion>
        <FechaResolucion>20-02-2017 13:22:22</FechaResolucion>
    </Normativa>

</FacturaElectronica>"""
# print raw_xml_t
raw_xml = raw_xml_t
# if self.ebiller_id.use_jar:
# jar_path = '/opt/soltein/repos/erpmultitest/10_quality/solt-erp-multicompany/addons/multi_ec_ebilling/data/signFile.jar'
jar_path = '/home/orlando/Escritorio/proyectos/soporte/project_medical_costa/repos/develop/solt-erp-multicompany/addons/medical_ebilling_cr/data/firmar-xades.jar'
key_store_pwd = '0786'
# key_store_path = '/opt/soltein/repos/erpmultitest/10_quality/solt-erp-multicompany/addons/multi_ec_ebilling/tests/jose_miguel_martinez_torres.p12'
key_store_path = '/home/orlando/Escritorio/proyectos/soporte/project_medical_costa/repos/develop/solt-erp-multicompany/addons/medical_ebilling_cr/data/030412028623.p12'

# f = open(jar_path,'r')
# print f
#
# b = open(key_store_path,'r')
# print b

print "Ubicacion de archivo " + key_store_path

args = [jar_path, raw_xml_t, key_store_path, key_store_pwd]
# try:
import os
res = os.execlp('java',
                 '-Dfile.encoding=UTF8',
                 '-jar',
                 jar_path,
                 raw_xml_t,
                 key_store_path,
                 key_store_pwd)
print "firmado ", res
# except (Exception,) as e:
#     print e
