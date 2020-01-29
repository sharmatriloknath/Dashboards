from odoo import models, fields, api, exceptions, _
import logging
_logger=logging.getLogger(__name__)


class EmployeePoliciesList(models.Model):
    _name = "employee.policies.list"
    _description = "Employee Policies"
    _rec_name = 'policy_name'

    policy_name = fields.Char(string='Policy Name')
    per_late_arrival = fields.Float(string='Permitted Late Arrival')
    per_early_departure = fields.Float(string='Permitted Early Departure')
    max_hours = fields.Float(string='Max Working Hours For Half Day')
    working_hrs_for_absent = fields.Float(string='Working Hrs For Absent')
    working_hrs_for_present = fields.Float(string='Working Hrs For Present')
    late_arrival = fields.Float(string='Late Arrival')
    show_late_arrival = fields.Selection([('none','None'),('cut_full_day','Cut Full Day'),('cut_half_day','Cut Half Day')],string='Show As For Late Arrival')
    early_departure = fields.Float(string='Early Departure')
    show_early_departure = fields.Selection([('none','None'),('cut_full_day','Cut Full Day'),('cut_half_day','Cut Half Day')],string='Show As For Early Departure')
    req_punch = fields.Selection([('single','singlepunch'),('multi','multipunch'),('no_punch','No Punch'),('auto_departure','Auto Departure')],string='Required Punch In Day')
    single_punch = fields.Selection([('overwrite','overwrite'),('out','Fix Time Out')],string='Single Punch Only')
    enable_setting = fields.Boolean(string='Enable Late Coming Setting')
    cut_days_or_leave = fields.Selection([('days','Cut Days'),('leave','Cut Leave Balance')])
    month_late=fields.Integer(string="No Of Late In A Month")
    cut_days = fields.Selection([('half','Half Days'),('absent','Absent')],string='Cut Days')
    ignore_ot = fields.Float(string='Ignore Overtime')
    no_hrs = fields.Float(string='No Of Hrs in(HH:mm format)')
    max_ot_allow=fields.Selection([('none','None'),('limited','Limited')],string="Max OT Allow")
    max_ot_hrs = fields.Float(string='Max OT Hrs In Month')
    equal_to_days = fields.Integer(string='Equal to Days')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id)



class Employee (models.Model):
    _inherit = "hr.employee"

    policy_name = fields.Many2one('employee.policies.list','Policy')