from odoo import api, fields, models
import datetime
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import date
"""inheritance of hr.employee for adding employee_type """


class HrEmployee (models.Model):
	_inherit = 'hr.employee'

	employee_type = fields.Many2one ('hr.contract.type', string='Employee Type')
	notice_period = fields.Boolean (string="Notice Period")
	from_notice = fields.Datetime (string="Start of Notice")
	to_notice = fields.Datetime (string="End of Notice")
	probation = fields.Boolean (string="Probation Period")
	start_probation = fields.Datetime(string="Start of Probation")
	end_probation = fields.Datetime (string="End of Probation")
	hod = fields.Many2one ("hr.employee", string="HOD")


	#Added By Trilok 8-1-2020
	resignation_date = fields.Date("Resignation Date")
	notice_period_days = fields.Integer("Notice Period Days")
	last_day = fields.Date("Last Day")

	# Add one more field
	region_id = fields.Many2one('region', 'Region')


	@api.onchange('from_notice')
	def compute_attendance(self):
		from_notice = self.from_notice
		if from_notice:
			date = datetime.datetime.strptime(from_notice, DEFAULT_SERVER_DATETIME_FORMAT)
			notice_period_days = self.notice_period_days
			final_date = date + timedelta(days=int(notice_period_days))
			self.to_notice = final_date

	# Function Called By Scheduler For Making Employee InActive
	def run_scheduler_to_make_employee_inactive(self):
		all_employees = self.env['hr.employee'].search([('id', '>', 0), ('company_id', '=', self.env.user.company_id.id)])
		for employee in all_employees:
			if employee.last_day:
				if date.today() == (datetime.datetime.strptime(employee.last_day, '%Y-%m-%d') + timedelta(days=1)).date():
					employee.write({'active': False})

	#End Trilok Code Here

class ResourceCalendar(models.Model):
	_inherit = 'resource.calendar'

	name = fields.Char()


class ResourceCalendarLeaves(models.Model):
	_inherit = "resource.calendar.leaves"

	name = fields.Char()


class HrDepartment(models.Model):

	_inherit = "hr.department"


class Employee(models.Model):
	_inherit = "hr.employee"


class Job (models.Model):
	_inherit = "hr.job"


















