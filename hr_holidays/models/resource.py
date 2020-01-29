# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"
    _description = "Leave Detail"

    holiday_id = fields.Many2one("hr.holidays", string='Leave Request')

class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"