import csv
from xml.dom import minidom
import xmlrpclib

# select e.identification_id, e.passport_id , sum(p.num_dias) from hr_payroll p
# join hr_employee e on e.id = p.employee_id
# join hr_contract_period c on c.id = p.period_id
# where c.fiscalyear_id = 2
# group by e.identification_id, e.passport_id


comp1 = open('/home/angel/odoo/9.0/odoo-9.0rc20180523/repository/feature_cr_fe/solt-med-odoo-src/addons/medical_l10n_cr_toponyms/carga/update_data_canton.csv')
reader1 = csv.reader(comp1, delimiter='|')

url = 'http://localhost:8073'
common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
db = 'medical_fe_cr'
username = 'admin'
password = 'admin'
uid = common.authenticate(db, username, password, {})
models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))

invoice_ids = []
for ind, row in enumerate(reader1):
    if ind == 0:
        continue
    partner_id = False
    if row[0] and row[2] and row[4] and row[6]:
        state_id = models.execute_kw(db, uid, password, 'res.country.state', 'search', [
            [('code', '=', row[0]), ('name', '=', row[1])]
        ])
        if not state_id:
            state_id = models.execute_kw(db, uid, password, 'res.country.state', 'create', [
                {
                    'code': row[0],
                    'country_id': 51,
                    'name': row[1]
                }
            ])
        else:
            state_id = state_id[0]
        print "***********STATE*************", state_id

        city_id = models.execute_kw(db, uid, password, 'res.country.state.city', 'search', [
            [('code', '=', row[2]), ('state_id', '=', state_id), ('name', '=', row[3])]
        ])
        if not city_id:
            city_id = models.execute_kw(db, uid, password, 'res.country.state.city', 'create', [
                {
                    'state_id': state_id,
                    'code': row[2],
                    'name': row[3]
                }
            ])
        else:
            city_id = city_id[0]
        print "***********FIND CANTON*************", city_id

        district_id = models.execute_kw(db, uid, password, 'res.country.district', 'search', [
            [('code', '=', row[4]), ('city_id', '=', city_id), ('name', '=', row[5])]
        ])
        if not district_id:
            district_id = models.execute_kw(db, uid, password, 'res.country.district', 'create', [
                {
                    'code': row[4],
                    'city_id': city_id,
                    'name': row[5]
                }
            ])
        else:
            district_id = district_id[0]
        print "***********FIND DISTRICT*************", district_id

        barrio_id = models.execute_kw(db, uid, password, 'res.country.neighborhood', 'search', [
            [('code', '=', row[6]), ('district_id', '=', district_id), ('name', '=', row[7])]
        ])

        if not barrio_id:
            barrio_id = models.execute_kw(db, uid, password, 'res.country.neighborhood', 'create', [
                {
                    'code': row[6],
                    'district_id': district_id,
                    'name': row[7]
                }
            ])

        print "***********FIND BARRIO*************", barrio_id