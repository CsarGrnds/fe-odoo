# -*- coding: utf-'8' "-*-"
from openerp import api, fields, models
from openerp.tools.translate import _

class City(models.Model):
    """City"""
    _name = 'res.country.state.city'
    _description = "Country State City"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True, size=2, select=True)
    state_id = fields.Many2one('res.country.state', string='State', required=True, select=True)

class District(models.Model):
    """District"""
    _name = 'res.country.district'
    _description = "District"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True, size=2, select=True)
    city_id = fields.Many2one('res.country.state.city', string='City', required=True, select=True)

class Neighborhood(models.Model):
    """Neighborhood"""
    _name = 'res.country.neighborhood'
    _description = "Neighborhood"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True, size=2, select=True)
    district_id = fields.Many2one('res.country.district', string='District', required=True, select=True)

