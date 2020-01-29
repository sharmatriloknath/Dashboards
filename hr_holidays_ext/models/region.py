from odoo import api, fields, models


class Region (models.Model):
    _name = 'region'

    name = fields.Char(string="Region")
    country_id = fields.Many2one('res.country', 'Country')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
