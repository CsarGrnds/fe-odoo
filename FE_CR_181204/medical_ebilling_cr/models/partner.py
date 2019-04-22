# -*- coding: utf-8 -*-
##############################################################################
#
#    Account Module - Ecuador
#    Copyright (C) 2010 GnuThink Software All Rights Reserved
#    info@gnuthink.com
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from lxml import etree
from openerp import api, fields, models
from openerp.tools.translate import _
from openerp.exceptions import Warning
from openerp.addons.medical_ebilling_cr.tools.validation_cr import cedula_01_validation, cedula_02_validation, dimex_validation, nite_validation


try:
    import phonenumbers
    from phonenumbers.phonemetadata import PhoneMetadata
except:
    pass

docs_type = [
        ('01', 'Cedula Fisica'),
        ('02', 'Cedula Juridica'),
        ('03', 'DIMEX'),
        ('04', 'NITE'),
        ('100', 'Identificacion Extranjero'),
]

class ResPartner(models.Model):
    _inherit = 'res.partner'

    identification_type = fields.Selection(docs_type, string="Identification Type", select=True)
    identification_cr = fields.Char(string="Identification", size=20, select=True)
    comercial_name = fields.Char(string="Business Name", size=80)


    def get_phone_number(self, number):
        res = number
        if number:
            res_parse = phonenumbers.parse(number, self.country_id.code.upper())
            res_parse.country_code = PhoneMetadata.metadata_for_region(self.country_id.code.upper(), None).country_code
            res = number.split(str(res_parse.country_code))
            return (res[1] if len(res) > 1 else res[0]) or ''
        return res or ''

    @api.constrains("identification_cr")
    def _check_unique_identification_company(self):
        obj = self
        others = False
        ids = self
        if type(ids) is list:
            obj = obj[0]

        others = self.env['res.partner'].search([('parent_id', '=', False), ('identification_cr', '=', obj.identification_cr), ('id', '!=', obj.id), ('company_id', '=', obj.company_id.id)])
        if others:
            raise Warning('Its Duplicate identification.')

    @api.multi
    @api.constrains('identification_cr')
    def _check_identification_rule(self):
        def is_number_cr(s):
            try:
                float(s)
                return True
            except ValueError:
                return False

        for partner in self:
            if partner.identification_type and partner.identification_cr:
                if partner.identification_type != '100':
                    if len(partner.identification_cr) > 12:
                        raise Warning('Invalid identification.')

                    if not is_number_cr(partner.identification_cr):
                        raise Warning('Invalid identification.')

                    if partner.identification_type == '01':
                        if len(partner.identification_cr) > 9:
                            raise Warning('Cedula Fisica Invalida.')
                        numcc = partner.identification_cr
                        firts_one = numcc[0:1]
                        if int(firts_one) == 0:
                            raise Warning('Cedula Fisica Invalida.')
                        # cedula_01 = cedula_01_validation(partner.identification_cr)
                        # if not cedula_01:
                        #     raise Warning('Cedula Fisica Invalida.')

                    if partner.identification_type == '02':
                        if len(partner.identification_cr) > 10:
                            raise Warning('Cedula Juridica Invalida.')

                        #
                        #
                        # cedula_02 = cedula_02_validation(partner.identification_cr)
                        # if not cedula_02:
                        #     raise Warning('Cedula Juridica Invalida.')

                    if partner.identification_type == '03':
                        if len(partner.identification_cr) > 12:
                            raise Warning('DIMEX Invalido.')
                        numcc = partner.identification_cr
                        firts_one = numcc[0:1]
                        if int(firts_one) == 0:
                            raise Warning('DIMEX Invalido.')

                        # dimex_res = dimex_validation(partner.identification_cr)
                        # if not dimex_res:
                        #     raise Warning('DIMEX Invalido.')

                    if partner.identification_type == '04':
                        if len(partner.identification_cr) > 10:
                            raise Warning('NITE Invalido.')
                        #
                        # nite_res = nite_validation(partner.identification_cr)
                        # if not nite_res:
                        #     raise Warning('NITE Invalido.')
