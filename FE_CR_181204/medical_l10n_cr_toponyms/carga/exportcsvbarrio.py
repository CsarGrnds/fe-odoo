import csv
from xml.dom import minidom
import unicodedata

pathology_list = []

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

def remove_accents(s):
    return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))


count_row = 0
index_iter = 0
doc = None
terp = None
data = None
i_d = 1

state_list = []
comp2 = open('codificacionubicacion.csv')
reader2 = csv.reader(comp2, delimiter='|')
reader2.next()
for row in reader2:
    print "linea ", row
    if count_row == 0:
        doc, terp, data = get_openerp_dom()

    if unicode(str(row[6]), "utf8") != '-':
        code = unicode(str(row[6]), "utf8")
        name = unicode(str(row[7]), "utf8")
        name_distrit = unicode(str(row[5]), "utf8")
        code_distrit = unicode(str(row[4]), "utf8")
        distrit_str = "district_new_id_" + code_distrit + '_' + remove_accents(name_distrit).replace(' ', '').lower()
        if code + '-' + name + code_distrit + '_' + remove_accents(name_distrit).replace(' ', '').lower() not in state_list:
            record = doc.createElement('record')
            record.setAttribute("id", "barrio_new_id_"+ code + '_' + remove_accents(name).replace(' ', '').lower())
            record.setAttribute("model", "res.country.neighborhood")

            data_rec_dict = {
                'code': unicode(str(row[6]), "utf8"),
                'name': unicode(str(row[7]), "utf8"),
                'district_id': distrit_str
            }
            state_list.append(code + '-' + name + code_distrit + '_' + remove_accents(name_distrit).replace(' ', '').lower())

            print index_iter
            print data_rec_dict

            for k, val in data_rec_dict.iteritems():

                ref_c = False
                bool_c = False
                if val or val != '-':
                    if k in ['district_id']:
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

    if count_row == 1000:
        print "iter ", index_iter
        # print "product_product_"+str((index_iter/500))+".xml"

        a = terp.toprettyxml(encoding="utf-8")
        if a:
            fo = open(""+"barrio_"+str((index_iter))+".xml", "wb")
            fo.write(str('<?xml version="1.0" encoding="utf-8"?>')+"\n"+a)
            fo.close()

        count_row = 0
        doc = None
        terp = None
        data = None

if 1<=count_row<1000:
    a = terp.toprettyxml(encoding="utf-8")
    if a:
        fo = open(""+"barrio_final.xml", "wb")
        fo.write(str('<?xml version="1.0" encoding="utf-8"?>')+"\n"+a)
        fo.close()

# print product_list
