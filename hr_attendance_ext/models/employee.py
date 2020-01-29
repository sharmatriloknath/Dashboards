from odoo import models, fields, api, exceptions, _


class HrEmployee(models.Model):
    _inherit = "hr.employee"



    emp_punch_code=fields.Char(string='Employee Punch Code')