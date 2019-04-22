import csv
from xml.dom import minidom

pathology_list = []


comp1 = open('codificacionubicacion.csv')
reader1 = csv.reader(comp1, delimiter='|')


reader1.next()
i = 419
k = 0
j = 1

cont = 1


def get_openerp_dom():
    doc_t = minidom.Document()
    terp_t = doc_t.createElement("openerp")
    doc_t.appendChild(terp_t)
    data_t = doc_t.createElement("data")
    # data_t.setAttribute("noupdate", "0")
    terp_t.appendChild(data_t)
    return doc_t, terp_t, data_t

def create_fiel_rec(doc_t, c, val, ref_field, ref_bool):
    field = doc_t.createElement('field')
    field.setAttribute("name", c)
    if not ref_field and not ref_bool:
        field.appendChild(doc_t.createTextNode(val))
    else:
        if ref_field:
            field.setAttribute("ref", val)
        if ref_bool:
            field.setAttribute("eval", val)
    return field

count_row = 0
index_iter = 0
doc = None
terp = None
data = None
i_d = 1

state_list = []
comp2 = open('codificacionubicacion.csv')
reader2 = csv.reader(comp2, delimiter='|')
for row in reader2:
    print "linea ", row
    if count_row == 0:
        doc, terp, data = get_openerp_dom()
    if unicode(str(row[0]), "utf8") != '-':
        code = unicode(str(row[0]), "utf8")
        if code not in state_list:
            record = doc.createElement('record')
            record.setAttribute("id", "country_state_new_id_"+unicode(str(row[0]).replace(".", "_"), "utf8"))
            record.setAttribute("model", "res.country.state")

            data_rec_dict = {
                'code': unicode(str(row[0]), "utf8"),
                'name': unicode(str(row[1]), "utf8"),
                'country_id': 'base.cr'
            }
            state_list.append(unicode(str(row[0]), "utf8"))

            print index_iter
            print data_rec_dict

            for k, val in data_rec_dict.iteritems():

                ref_c = False
                bool_c = False
                if val or val != '-':
                    if k in ['country_id']:
                        ref_c = True
                    val_c = val
                    if isinstance(val, bool):
                        bool_c = True
                        val_c = str(val)
                    if isinstance(val, float):
                        val_c = str(val)

                    if type(val_c) != str:
                        val_c = val_c
                    field = create_fiel_rec(doc, k, val_c, ref_c, bool_c)
                    record.appendChild(field)

                pathology_list.append(data_rec_dict)

                data.appendChild(record)

                record_stck = False


    count_row += 1
    index_iter += 1

    if count_row == 23179:
        # print index_iter
        # print "product_product_"+str((index_iter/500))+".xml"

        a = terp.toprettyxml(encoding="utf-8")
        if a:
            fo = open("./carga/"+"account_"+str((index_iter/23179))+".xml", "wb")
            fo.write(str('<?xml version="1.0" encoding="utf-8"?>')+"\n"+a)
            fo.close()

        count_row = 0
        doc = None
        terp = None
        data = None

if 1<=count_row<23179:
    a = terp.toprettyxml(encoding="utf-8")
    if a:
        fo = open(""+"country_state_final.xml", "wb")
        fo.write(str('<?xml version="1.0" encoding="utf-8"?>')+"\n"+a)
        fo.close()

# print product_list
