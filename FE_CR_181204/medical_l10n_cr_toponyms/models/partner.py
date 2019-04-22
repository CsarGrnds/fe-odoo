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
from openerp import api, fields, models
from openerp.tools.translate import _

ADDRESS_FIELDS = ('city_id', 'district_id', 'neighborhood_id')

class ResPartner(models.Model):
    _inherit = 'res.partner'

    city_id = fields.Many2one('res.country.state.city', string='City', select=True)
    district_id = fields.Many2one('res.country.district', string='District', select=True)
    neighborhood_id = fields.Many2one('res.country.neighborhood', string='Neighborhood', select=True)
    otras_senas = fields.Text(string='Otras Senas', size=160)

    @api.onchange('city_id')
    def onchange_city_id(self):
        self.district_id = False
        if self.city_id:
            self.state_id = self.city_id.state_id.id
            self.country_id = self.city_id.state_id.country_id.id
        else:
            self.state_id = False
            self.country_id = False

    @api.onchange('district_id')
    def onchange_district_id(self):
        self.neighborhood_id = False

    @api.model
    def _address_fields(self):
        res = super(ResPartner, self)._address_fields()
        return res + list(ADDRESS_FIELDS)
