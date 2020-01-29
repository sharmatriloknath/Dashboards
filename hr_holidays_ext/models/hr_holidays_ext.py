from odoo import api, fields, models, tools, SUPERUSER_ID, _
import datetime
import dateutil.relativedelta
from datetime import datetime as dt
from calendar import monthrange
from lxml import etree
import math
from dateutil import parser
from dateutil.relativedelta import relativedelta
import calendar
from odoo.exceptions import UserError, AccessError, ValidationError
flag_cust = False
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ResetData (models.Model):
	_inherit = "hr.holidays"

	carry_fwd_leaves = fields.Float('Carry Forward Leaves')
	encash_leave = fields.Float('Encashed Leaves')
	half_days = fields.Integer('Half days')
	full_days = fields.Integer('Full days')
	reset_date = fields.Date('Leave Type Reset Date')
	approval_date = fields.Date('Approval Date')
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
	carry_fwd_expiry_date = fields.Date("Expiry Date")

	# Added By Trilok Nath 16-01-2020
	adjusted_from_date = fields.Datetime("Adjustment From Date")
	adjusted_to_date = fields.Datetime("Adjustment To Date")
	ref_id = fields.Integer("Adjustment Reference Id")
	adjustment_holiday_ids = fields.One2many('leave.adjustment', 'holiday_id')
	number_of_days_duplicate = fields.Float("Number Of Days", help="This Field Store the Duplicate Value of number_of_days field")

	@api.onchange('employee_id')
	def leave_adjustment_function(self):
		if self.employee_id:
			data = self.env['hr.holidays'].search([('employee_id', '=', self.employee_id.id),('company_id', '=', self.env.user.company_id.id)])
			list1 = []
			if data:
				total_holidays_type = []
				for leave in data:
					if leave.holiday_status_id not in total_holidays_type:
						total_holidays_type.append(leave.holiday_status_id)
				for leave_type in total_holidays_type:
					query = "select sum(number_of_days) + sum(COALESCE(number_of_days_duplicate,0)) as days from hr_holidays where holiday_status_id=%s and state='validate'  and employee_id=%s" %(leave_type.id, self.employee_id.id)
					self.env.cr.execute(query)
					bal = self.env.cr.dictfetchall()
					if bal:
						balance = bal[0]['days']
						if not balance:
							balance = 0
						data = (0, False,
								{'leave_type': leave_type.id, 'balance': balance, 'employee_id': self.employee_id.id})
						list1.append(data)
			self.adjustment_holiday_ids = list1

	def leave_managed_by_hr_manager(self, holiday):
		if holiday.holiday_status_id.name in ('Casual Leaves', 'earned leaves'):
			employee = holiday.employee_id
			cl = self.env['hr.holidays.status'].search([('name', 'ilike', 'Casual Leaves'), ('company_id', '=', self.env.user.company_id.id), ('employee_type', '=', employee.employee_type.id)])
			el = self.env['hr.holidays.status'].search([('name', 'ilike', 'earned leaves'), ('company_id', '=', self.env.user.company_id.id), ('employee_type', '=', employee.employee_type.id)])
			adjustment = holiday.adjustment_holiday_ids
			cl_leave_adjust = ''
			el_leave_adjust = ''
			for line in adjustment:
				if line.leave_type.id == cl.id:
					cl_leave_adjust = line
				elif line.leave_type.id == el.id:
					el_leave_adjust = line
			req_days = holiday.number_of_days_temp
			if cl:
				if holiday.holiday_status_id.id == cl.id:
					if cl_leave_adjust:
						if cl_leave_adjust.balance > 0:
							if cl_leave_adjust.balance >= req_days:
								holiday.write({
									'state': 'validate'
								})
							else:
								if el:
									if el_leave_adjust and el_leave_adjust.balance > 0:
										el_adjust = el_leave_adjust.adjusted_days if el_leave_adjust.adjusted_days else 0
										cl_adjust = cl_leave_adjust.adjusted_days if cl_leave_adjust.adjusted_days else 0
										if cl_adjust == 0 and el_adjust == 0:
											holiday.write({
												'state': 'validate',
												'number_of_days': -cl_leave_adjust.balance,
											})
										else:

											if cl_adjust > 0:
												holiday.write({
													'state': 'validate',
													'number_of_days': -cl_adjust,
												})

											if el_adjust > 0:
												holiday.create({
													'holiday_status_id': el.id,
													'number_of_days_temp': 0,
													'number_of_days': -el_adjust,
													'number_of_days_duplicate':-el_adjust,
													'adjusted_from_date': el_leave_adjust.adjusted_from_date if el_leave_adjust.adjusted_from_date else False,
													'adjusted_to_date': el_leave_adjust.adjusted_to_date if el_leave_adjust.adjusted_to_date else False,
													'type': 'remove',
													'holiday_type': holiday.holiday_type if holiday.holiday_type else None,
													'employee_id': holiday.employee_id.id,
													'department_id': holiday.department_id if holiday.department_id else None,
													'payslip_status': holiday.payslip_status,
													'state': 'validate',
													'ref_id': holiday.id

												})

								else:
									holiday.write({
										'state': 'validate',
										'number_of_days': -cl_leave_adjust.balance,
									})
				else:
					if el:
						if el_leave_adjust:
							if el_leave_adjust.balance >= req_days:
								holiday.write({
									'state': 'validate'
								})
							else:
								if cl:
									if el_leave_adjust.balance > 0:
										el_adjust = el_leave_adjust.adjusted_days if el_leave_adjust.adjusted_days else 0
										cl_adjust = cl_leave_adjust.adjusted_days if cl_leave_adjust.adjusted_days else 0
										if cl_adjust == 0 and el_adjust == 0:
											holiday.write({
												'state': 'validate',
												'number_of_days': -el_leave_adjust.balance,
											})
										else:
											if el_adjust > 0:
												holiday.write({
													'state': 'validate',
													'number_of_days': -el_adjust,
												})

											if cl_adjust > 0:
												holiday.create({
													'holiday_status_id': cl.id,
													'number_of_days_temp': 0,
													'number_of_days': -cl_adjust,
													'number_of_days_duplicate': -cl_adjust,
													'adjusted_from_date': cl_leave_adjust.adjusted_from_date if cl_leave_adjust.adjusted_from_date else False,
													'adjusted_to_date': cl_leave_adjust.adjusted_to_date if cl_leave_adjust.adjusted_to_date else False,
													'type': 'remove',
													'holiday_type': holiday.holiday_type if holiday.holiday_type else None,
													'employee_id': holiday.employee_id.id,
													'department_id': holiday.department_id if holiday.department_id else None,
													'payslip_status': holiday.payslip_status,
													'state': 'validate',
													'ref_id': holiday.id

												})
								else:
									holiday.write({
										'state': 'validate',
										'number_of_days': -el_leave_adjust.balance,
									})

	def compute_valid_leaves_for_employee(self, date_from, date_to):
		policy_id = self.env['leaves.policy'].sudo().search(
			[('leave_type', '=', self.holiday_status_id.id), ('company_id', '=', self.env.user.company_id.id)])
		if date_from and not date_to:
			if policy_id:
				if not policy_id.dur_half:
					date_to_with_delta = fields.Datetime.from_string(date_from) + timedelta(days=1)
				else:
					date_to_with_delta = fields.Datetime.from_string(date_from) + timedelta(hours=5)
				self.date_to = str(date_to_with_delta)
				number_of_day = (datetime.datetime.strptime(self.date_to, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.datetime.strptime(date_from, DEFAULT_SERVER_DATETIME_FORMAT)).total_seconds()/(24*3600)
				self.number_of_days_temp = number_of_day

		elif (date_to and date_from) and (date_from <= date_to):
			policy_id = self.env['leaves.policy'].sudo().search(
				[('leave_type', '=', self.holiday_status_id.id), ('company_id', '=', self.env.user.company_id.id)])
			if policy_id:
				for val in policy_id:
					number_of_days = 0
					if val.weekends_leave_period == 'dont_count':
						num_days = self._get_number_of_days(date_from, date_to, self.employee_id.id)
						date_to1 = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
						date_from1 = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')

						# Logic of Public Holidays when week offs count as holidays is True 2019-11-19
						emp_region_id = self.employee_id.region_id.id
						public = self.env['holidays.master'].sudo().search(
							[('region_id', '=', emp_region_id), ('company_id', '=', self.env.user.company_id.id)])
						if public:
							public_leaves = public.global_leaves_ids
							public_holidays = []
							for holiday in public_leaves:
								public_holidays.append((holiday.date_from, holiday.date_to))

							# Public holidays between leave period
							leave_period_dates = []
							start_date = date_from1.date()
							end_date = date_to1.date()
							delta = end_date - start_date
							for i in range(delta.days + 1):
								day = start_date + timedelta(days=i)
								leave_period_dates.append(day)
							count = 0
							for date in public_holidays:
								if datetime.datetime.strptime(date[0], '%Y-%m-%d %H:%M:%S').date() in leave_period_dates:
									count += 1
						# End of Public Holidays logic

							self.number_of_days_temp = num_days - count
					else:
						number_of_days = self._get_number_of_days(date_from, date_to, self.employee_id.id)
						date_to1 = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
						date_from1 = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
						total_seconds = (date_to1 - date_from1).total_seconds()
						total_days = total_seconds / (24 * 3600)

						week_offs = total_days - number_of_days
						self.number_of_days_temp = number_of_days + week_offs
						if not val.dur_half:
							if float(self.number_of_days_temp) < 1.0:
								raise ValidationError("Half Day For This Leave Is Not Allowed")

		elif (date_to and date_from) and (date_from > date_to):
			raise ValidationError("From Date cannot be greater then To Date")

		else:
			self.number_of_days_temp = 0


class SchedulerRun (models.Model):
	_name = "scheduler.run"

	employee_type = fields.Many2one('hr.contract.type', string='Employee Type')
	leave_type = fields.Char('Leave Type')
	run_date = fields.Date('Scheduler Run Date')
	next_exec = fields.Date('Next Run Date')
	reset_date = fields.Date('Reset Date')
	status = fields.Char('Status')
	priority = fields.Integer('Priority') # not used in functionality
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)


class CustomLeaveAllocation (models.Model):
	_name = "custom.mon.alloc"

	name = fields.Char (default="Custom Month Leave Allocation")
	active = fields.Boolean ('Active', default=True)
	company_id = fields.Many2one ('res.company', string='Company', default=lambda self: self.env.user.company_id)
	employee_type = fields.Many2one ('hr.contract.type', string='Employee Type')
	leave_type = fields.Many2one ('hr.holidays.status', string='Leave Type')
	mon_1 = fields.Float (string="Month 1")
	mon_2 = fields.Float (string="Month 2")
	mon_3 = fields.Float (string="Month 3")
	mon_4 = fields.Float (string="Month 4")
	mon_5 = fields.Float (string="Month 5")
	mon_6 = fields.Float (string="Month 6")
	mon_7 = fields.Float (string="Month 7")
	mon_8 = fields.Float (string="Month 8")
	mon_9 = fields.Float (string="Month 9")
	mon_10 = fields.Float (string="Month 10")
	mon_11 = fields.Float (string="Month 11")
	mon_12 = fields.Float (string="Month 12")
	accumulate = fields.Float(string='Accumulated', compute='_sum_of_leaves')
	link_04_ids = fields.Many2one('hr.holidays.status')

	@api.multi
	def _sum_of_leaves(self):
		accumulate = self.mon_1 + self.mon_2 + self.mon_3 + self.mon_4 + self.mon_5 + self.mon_6 + self.mon_7 + self.mon_8 + self.mon_9 + self.mon_10 + self.mon_11 + self.mon_12
		return accumulate

	@api.multi
	def write(self, vals):
		res = super(CustomLeaveAllocation, self).write(vals)
		global flag_cust
		flag_cust = True
		return res


class HolidaysType (models.Model):
	_inherit = "hr.holidays.status"
	_description = "Leave Type"

	employee_type = fields.Many2one ('hr.contract.type', string='Employee Type')
	allocation_in_probation = fields.Boolean (string="Allocation In Probation")
	restrict_on_notice = fields.Boolean (string="Restrict on Notice")
	highlight_override = fields.Boolean (string="Highlight Override")
	allocation_in_probation_selection = fields.Selection (
		[('reflect', 'Reflect the Balance'), ('reserve', 'Reserve till Probation')], string=' ')
	restrict_on_notice_selection = fields.Selection (
		[('avail', 'Can Avail in Notice Period'), ('not avail', "Can't Avail in Notice Period")], string=' ')
	# status_id = fields.One2many('leave.approval','approval_id')
	accrual = fields.Boolean (string='Accrual')
	accrual_period = fields.Selection ([('month', 'Monthly'), ('year', 'Yearly'), ('custom', 'Custom')],
	                                   string="Accrual Period", default='month')
	accrual_day = fields.Integer ('Accrual Day', default='1')
	MONTH_LIST = [('1', 'Jan'), ('2', 'Feb'), ('3', 'Mar'), ('4', 'Apr'), ('5', 'May'), ('6', 'Jun'),
	              ('7', 'Jul'), ('8', 'Aug'), ('9', 'Sep'), ('10', 'Oct'), ('11', 'Nov'), ('12', 'Dec')]
	accrual_month = fields.Selection (MONTH_LIST, string='Accrual Month')
	reset = fields.Boolean (string='Reset')
	reset_period = fields.Selection ([('month', 'Monthly'), ('year', 'Yearly')], string="Reset Period", default='year')
	reset_day = fields.Integer ('Reset Day', default=1)
	reset_month = fields.Selection (MONTH_LIST, string='Reset Month', default='1')
	no_of_days = fields.Float (string="No of Days")
	reset_type = fields.Selection([('encash', 'Encash Leaves'),('carry','Carry Forward Leaves')], string='Leave Movement Type', default='carry')
	carry_fwd_value = fields.Float (string='Carry Forward Value')
	carry_fwd_type = fields.Selection ([('perc', 'Percentage'), ('num', 'Number')], string='Carry Forward Type')
	leave_encash = fields.Boolean('Encash Leaves')
	encash_value = fields.Float (string='Encashment Value')
	encash_type = fields.Selection ([('perc', 'Percentage'), ('num', 'Number')], string='Encashment Type')
	expiry_value = fields.Integer (string="Expiry Value")
	expiry_type = fields.Selection ([('mon', 'Months'), ('year', 'Years')], string='Expiry Type')
	prorate_type = fields.Selection ([('start_policy', 'Start of the Policy'),
	                                  ('start_end_policy', 'Start and End of the Policy'),
	                                  ('do_not_prorate', 'Do not Prorate')], string='Prorate Accrual', default='do_not_prorate')
	approval_policy_id = fields.Many2one('leave.approval')
	leaves_policy_id = fields.Many2one ('leaves.policy')
	advance_link_id = fields.One2many ('advance.accru.alloc', 'link_03_ids')
	cust_link_id = fields.One2many ('custom.mon.alloc', 'link_04_ids')
	expiry_date = fields.Date('Expiry Date')
	alloc_request = fields.Boolean('User can request for allocation for this type of leave')
# Validations on the fields for proper data entry
	@api.constrains('no_of_days')
	def validate_no_of_days(self):
		if self.no_of_days > 31:
			raise ValidationError ('No of Days to be allocated can not be more that 30 or 31 days')

# Called on Create and Write
	def validation_day(self):
		if self.accrual_month == '2':  # feb validation
			if self.accrual_day > 28:
				raise UserError("February has 27 or 28 days. Kindly fill accordingly")
		if self.accrual_month:  # Month based validation
			now = datetime.datetime.now().date()
			days = calendar.monthrange(now.year, int (self.accrual_month))[1]
			if self.accrual_day > days:
				raise ValidationError('Accrual Day should be according to the month you have entered.')
		if self.reset_month:  # month based validation
			now = datetime.datetime.now().date()
			days = calendar.monthrange(now.year, int (self.reset_month))[1]
			if self.reset_day >  days:
				raise ValidationError('Reset Day should be according to the month you have entered.')
		if self.accrual_day not in range (1, 32) or self.reset_day not in range (1, 32) :
			raise ValidationError("Day of Month is Out of range for Accrual Day/Reset day!")

	@api.model
	def create(self, vals):
		res = super(HolidaysType, self).create(vals)
		res.validation_day() # To validate data entry
		if res.no_of_days and res.accrual_period in ['month', 'custom']:
			temp_dict = {'employee_type': res.employee_type.id, 'leave_type': res.id,'link_04_ids':res.id} # optimised
			temp_dict1 = {'employee_type': res.employee_type.id, 'leave_type': res.id,'link_03_ids':res.id} # optimised
			# temp_dict1 = {'employee_type': res.employee_type.id, 'leave_type': res.id}
			print("the values in the rtem",temp_dict)
			for i in range(1,13):
				temp_dict['mon_%s' %i] = res.no_of_days
			custom_leaves_id = self.env['custom.mon.alloc'].sudo().create(temp_dict)
			advance_leaves_id = self.env['advance.accru.alloc'].sudo().create(temp_dict1)

			# leave_policy = self.env['leaves.policy'].sudo().create(temp_dict1)
			# approval = self.env['leave.approval'].sudo().create(temp_dict1)
			print('the values in the dict', temp_dict)
			print(custom_leaves_id)
			print(advance_leaves_id)
			# print("leave_policy",leave_policy)
			# print("leave_approval",approval)
			# if leave_policy:
			# 	res.update({'leaves_policy_id':leave_policy.id})
			# if approval:
			# 	res.update({'approval_policy_id':approval.id})
			now = datetime.datetime.now().date()
			accrual_date = datetime.datetime(now.year, now.month, res.accrual_day).date()
			reset_date = datetime.datetime (now.year, now.month, res.reset_day).date ()

			if res.reset_period == 'year':
				reset_date = datetime.datetime(now.year,int(res.reset_month), res.reset_day).date()
				if now > reset_date:
					reset_date = reset_date + relativedelta(years=+1)
			elif res.reset_period == 'month':
				reset_date = datetime.datetime (now.year, now.month, res.reset_day).date ()
				if now > reset_date:
					reset_date = reset_date + relativedelta(months=+1)

			scheduler_records = self.env['scheduler.run'].sudo().create( # optimized
				{'employee_type': res.employee_type.id, 'leave_type': res.id,
				 'run_date': accrual_date if now < accrual_date else accrual_date + relativedelta(months=+1),
				 'next_exec': accrual_date + relativedelta(months=+1) ,
				 'reset_date': reset_date,
				 'priority': 2})

		elif res.no_of_days and res.accrual_period == 'year':
			now = datetime.datetime.now().date()
			accrual_date = datetime.datetime (now.year, int(res.accrual_month), res.accrual_day).date()

			if res.reset_period == 'year':
				reset_date = datetime.datetime(now.year,int(res.reset_month), res.reset_day).date()
				if now > reset_date:
					reset_date = reset_date + relativedelta(years=+1)
			elif res.reset_period == 'month':
				reset_date = datetime.datetime (now.year, now.month, res.reset_day).date ()
				if now > reset_date:
					reset_date = reset_date + relativedelta(months=+1)

			scheduler_records = self.env['scheduler.run'].sudo().create(  # optimized
				{'employee_type': res.employee_type.id, 'leave_type': res.id,
				 'run_date': accrual_date if now < accrual_date else accrual_date + relativedelta(years=+1),
				 'next_exec': accrual_date + relativedelta(years=+1) if now < accrual_date else accrual_date + relativedelta (years=+2),
				 'reset_date': reset_date,
				 'priority': 2})
		return res

	@api.multi
	def write(self, vals):
		print ("Updating values")
		res = super(HolidaysType, self).write(vals)
		self.validation_day() # To validate data entry
		type = self.env['scheduler.run'].search([('leave_type','=',self.id),('employee_type','=',self.employee_type.id),
		                                         ('company_id', '=', self.env.user.company_id.id)], limit=1)
		type_cust = self.env['custom.mon.alloc'].search([('leave_type', '=', self.name),
		                                               ('employee_type', '=', self.employee_type.id),
	                                                ('company_id', '=', self.env.user.company_id.id)], limit=1)
		print('type_cust',type_cust)
		# if type in vals:
		temp_dict = {'employee_type': self.employee_type.id, 'leave_type': self.id}  # optimised
		for i in range(1, 13):
			temp_dict['mon_%s' % i] = self.no_of_days
		global flag_cust
		if not flag_cust:
			print("the val in flag are:................")
			custom_leaves_id = type_cust.sudo().update(temp_dict)

		if self.accrual_period == 'month' or self.accrual_period == 'custom':
			now = datetime.datetime.now().date()
			day = self.accrual_day
			accrual_date = datetime.datetime(now.year, now.month, day).date()
			if self.reset_period == 'year':
				reset_date = datetime.datetime(now.year,int(self.reset_month), self.reset_day).date()
				if now > reset_date:
					reset_date = reset_date + relativedelta(years=+1)
			else:
				reset_date = datetime.datetime(now.year, now.month, self.reset_day).date()
				if now > reset_date:
					reset_date = reset_date + relativedelta(months=+1)

			# scheduler_records = type.sudo().update(# optimized
			# 	{'employee_type': self.employee_type.id, 'leave_type': self.id,
			# 	 'run_date': accrual_date if now < accrual_date else accrual_date + relativedelta(months=+1),
			# 	 'next_exec': accrual_date + relativedelta (months=+1),
			# 	 'reset_date': reset_date,
			# 	 'priority': 2})

			# changes
			type.sudo().update(  # optimized
				{'employee_type': self.employee_type.id, 'leave_type': self.id,
				 'run_date': accrual_date if now < accrual_date else accrual_date + relativedelta(months=+1),
				 'next_exec': accrual_date + relativedelta(months=+1),
				 'reset_date': reset_date,
				 'priority': 2})

		elif self.no_of_days and self.accrual_period == 'year':
			now = datetime.datetime.now().date()
			accrual_date = datetime.datetime(now.year, int(self.accrual_month), self.accrual_day).date()

			if self.reset_period == 'year':
				reset_date = datetime.datetime(now.year, int(self.reset_month), self.reset_day).date ()
				if now > reset_date:
					reset_date = reset_date + relativedelta(years=+1)
			elif self.reset_period == 'month':
				reset_date = datetime.datetime(now.year, now.month, self.reset_day).date ()
				if now > reset_date:
					reset_date = reset_date + relativedelta(months=+1)

			# scheduler_records = type.sudo().update( # optimized
			# 	{'employee_type': self.employee_type.id, 'leave_type': self.id,
			# 	 'run_date': accrual_date if now < accrual_date else accrual_date + relativedelta(years=+1),
			# 	 'next_exec': accrual_date + relativedelta(years=+1) if now < accrual_date else accrual_date + relativedelta(years=+2),
			# 	 'reset_date': reset_date, 'priority': 2})

		# changes
			type.sudo().update(  # optimized
				{'employee_type': self.employee_type.id, 'leave_type': self.id,
				 'run_date': accrual_date if now < accrual_date else accrual_date + relativedelta(years=+1),
				 'next_exec': accrual_date + relativedelta(
					 years=+1) if now < accrual_date else accrual_date + relativedelta(years=+2),
				 'reset_date': reset_date, 'priority': 2})


		return res

	# Scheduler Function for leaves allocation
	@api.multi
	def run_scheduler_leaves_alloc(self):
		today = datetime.datetime.now()
		print("Scheduler running")
		new = self.env['scheduler.run'].search(
			[('run_date', '=', today.date()), ('company_id', '=', self.env.user.company_id.id)])
		new_1 = self.env['scheduler.run'].search(
			[('reset_date', '=', today.date()), ('company_id', '=', self.env.user.company_id.id)])
		for val in new:
				emp_ids = self.env['hr.employee'].search(
					[('id', '>', 0), ('employee_type','=', val.employee_type.id),
					 ('company_id', '=', self.env.user.company_id.id), ('active', '=', True)])
				query = "SELECT run_date,next_exec from scheduler_run where id='%s'"%val.id
				self.env.cr.execute(query)
				query_var = self.env.cr.fetchall()
				run_date_1 = query_var[0][0]
				next_exec_date = query_var[0][1]
				temp_emp = self.env['hr.holidays.status'].search (
					[('id', '=', val.leave_type), ('company_id', '=', self.env.user.company_id.id),
					 ('employee_type', '=', val.employee_type.id)])
				if temp_emp.accrual_period == 'month' or temp_emp.accrual_period == 'custom':
					query_update = "Update scheduler_run set run_date='%s' , next_exec='%s' where id=%s" \
					               % (next_exec_date, (datetime.datetime.strptime(next_exec_date,"%Y-%m-%d").date() + relativedelta (months=1)),val.id)
					self.env.cr.execute (query_update)
				else:
					query_update = "Update scheduler_run set run_date='%s' , next_exec='%s' where id=%s" \
					               % (next_exec_date, (datetime.datetime.strptime(next_exec_date,"%Y-%m-%d").date() + relativedelta (years=1)),val.id)
					self.env.cr.execute (query_update)
					self.env.cr.commit()
				if emp_ids:
					for each_emp in emp_ids:
						temp_emp = self.env['hr.holidays.status'].search(
							[('id', '=', val.leave_type), ('company_id', '=', self.env.user.company_id.id),
							 ('employee_type', '=', val.employee_type.id)])
						# for notice period allocation abort (if it is true for that leave type)
						if (temp_emp.restrict_on_notice == True and each_emp.notice_period == True) or temp_emp.allocation_in_probation == False :
							break

						# if temp_emp.accrual_period == 'custom' or temp_emp.accrual_period == 'year':
						if temp_emp.accrual_period == 'custom':
							cur_mon = int((datetime.date.today().strftime('%m')))
							print("the data in curmon -----------------",cur_mon)
							allocation_date = datetime.datetime.today().date()
							start_date = datetime.date(allocation_date.year, int(cur_mon), 1)
							end_date = start_date + relativedelta(months=1)
							mon_alloc = self.env['custom.mon.alloc'].search(
								[('id', '>', 0), ('company_id', '=', self.env.user.company_id.id),
								 ('leave_type', '=', int(val.leave_type)),('employee_type','=',val.employee_type.id)])
							print("the data after search -----------------",mon_alloc)
							if mon_alloc:
								# In case of Custom month allocation
								num_days = mon_alloc['mon_%s' %cur_mon] # pick the value of current month
								holiday_id = self.env['hr.holidays'].create(
									{'employee_id': each_emp.id, 'state': 'validate', 'name': temp_emp.name,
									 'type': 'add', 'number_of_days_temp': num_days, 'holiday_status_id': temp_emp.id,
									 'allocate_date':allocation_date,'date_from':start_date, 'date_to':end_date
									 })

						elif temp_emp.accrual_period == 'year':
							allocation_date = datetime.datetime.today().date()
							start_date = datetime.date(allocation_date.year, int(temp_emp.accrual_month), temp_emp.accrual_day)
							end_date = start_date + relativedelta(years=1)

							# In case of yearly allocation
							num_days = temp_emp.no_of_days
							holiday_id = self.env['hr.holidays'].create(
								{'employee_id': each_emp.id, 'state': 'validate', 'name': temp_emp.name,
								 'type': 'add', 'number_of_days_temp': num_days, 'holiday_status_id': temp_emp.id, 'allocate_date': allocation_date, 'date_from':start_date, 'date_to':end_date})

						# Linking with attendance, Fetch all the presents and half days of employee and allocate the leaves according to that.
						elif temp_emp.accrual_period == 'month':
							# Testing with attendance
							emp_shift = each_emp.resource_calendar_ids
							attendance_ids = emp_shift.attendance_ids
							# List to store the week days
							weekly_working_days = []
							for id in attendance_ids:
								weekly_working_days.append(int(id.dayofweek))

							global_leaves = emp_shift.global_leave_ids
							# List to store the global leaves
							public_holidays = []
							for holiday in global_leaves:
								public_holidays.append((holiday.date_from, holiday.date_to))
							total_week_working_days = len(weekly_working_days)
							current_month = datetime.datetime.today().month
							current_year = datetime.datetime.today().year
							days_of_month = monthrange(current_year,current_month)[1]

							total_days_datewise =[]
							for i in range(1, days_of_month + 1):
								total_days_datewise.append(datetime.date(current_year, current_month, i))
							# print(a)
							week_days=[]
							for date in total_days_datewise:
								week_days.append(date.weekday())

							days_without_weekoffs=[]
							for i in week_days:
								if i in weekly_working_days:
									days_without_weekoffs.append(i)

							# Current Month Public Holidays
							current_month_public_holidays = 0
							for date in public_holidays:
								if datetime.datetime.strptime(date[0],'%Y-%m-%d %H:%M:%S').weekday()  in weekly_working_days and datetime.datetime.strptime(date[0],'%Y-%m-%d %H:%M:%S').month==current_month:
									current_month_public_holidays += 1

							# total_working_days_of_month = (total_weeks_in_a_month*total_week_working_days)-current_month_public_holidays
							total_working_days_of_month = len(days_without_weekoffs)-current_month_public_holidays
							query="""select count(*) from hr_attendance where employee_id=%s and 
							employee_day_status=%s and company_id =%s and create_date between now()::timestamp::date	and now()::timestamp::date - interval '1 month' """
							self.env.cr.execute(query,(each_emp.id, 'present', self.env.user.company_id.id))
							result = self.env.cr.dictfetchall()
							present = 0
							if result:
								present = result[0]['count']

							query1="""select count(*) from hr_attendance where employee_id=%s and half_day_status=%s and company_id=%s
																		 and create_date between now()::timestamp::date and now()::timestamp::date - interval '1 month' """
							self.env.cr.execute(query1,(each_emp.id, True,self.env.user.company_id.id))
							result1 = self.env.cr.dictfetchall()
							# print(a)
							half_days = 0
							if result1:
								half_days = result1[0]['count']

							presents = present-half_days//2
							absents = total_working_days_of_month - presents
							advance_object = self.env['advance.accru.alloc'].search([('indentifier_alloc', '=', 'acc'), ('company_id', '=', self.env.user.company_id.id),
								 ('leave_type', '=', val.leave_type),('employee_type', '=', val.employee_type.id), ('from_num', '>=', absents),('to_num', '<=', absents)])

							if advance_object:
								for line in advance_object:

									if absents > line.from_num and absents < line.to_num and line.identifier_alloc == 'acc':
										count = line.count
										holiday_id = self.env['hr.holidays'].create(
											{'employee_id': each_emp.id, 'state': 'validate', 'name': temp_emp.name,
											 'type': 'add', 'number_of_days_temp': count,'holiday_status_id': temp_emp.id})

									elif absents > line.from_num and absents < line.to_num and line.identifier_alloc == 'start_policy':
										pass

									elif absents > line.from_num and absents < line.to_num and line.identifier_alloc == 'start_end_policy':
										pass


							else:
								allocation_date = datetime.datetime.today().date()

								start_date = datetime.date(allocation_date.year, allocation_date.month, 1)
								end_date = start_date + relativedelta(months=1)
								holiday_id = self.env['hr.holidays'].create(
									{'employee_id': each_emp.id, 'state': 'validate', 'name': temp_emp.name,
									 'type': 'add', 'number_of_days_temp': temp_emp.no_of_days,'holiday_status_id': temp_emp.id,
									 'allocate_date':allocation_date, 'date_from': start_date, 'date_to': end_date
									 })

		print("Allocation completed")

# Reset functionality
		for val_1 in new_1:
			# To update reset date
			val1_date = val_1.reset_date
			query = "SELECT reset_date from scheduler_run where id='%s'" % val_1.id
			self.env.cr.execute(query)
			query_var = self.env.cr.fetchall()
			reset_date_1 = query_var[0][0]
			temp_emp = self.env['hr.holidays.status'].search (
				[('id', '=', val_1.leave_type), ('company_id', '=', self.env.user.company_id.id),
				 ('employee_type', '=', val_1.employee_type.id)])
			if temp_emp.reset_period == 'month':
				query_update = "Update scheduler_run set reset_date='%s' where id='%s'" % ((datetime.datetime.strptime (reset_date_1, "%Y-%m-%d")
				                                                                            + relativedelta(months=1)), val_1.id)

				self.env.cr.execute (query_update)
			else:
				query_update = "Update scheduler_run set reset_date='%s' where id='%s'" % ((datetime.datetime.strptime (reset_date_1, "%Y-%m-%d")
				                                                                            + relativedelta (years=1)), val_1.id)
				self.env.cr.execute(query_update)

			print ("After updation", query_update)
			emp_ids = self.env['hr.employee'].search(
				[('id', '>', 0), ('employee_type', '=', val_1.employee_type.id),
				 ('company_id', '=', self.env.user.company_id.id),('active', '=', True)])
			if emp_ids:
				for each_emp in emp_ids:
					temp_emp = self.env['hr.holidays.status'].search([('id', '=', val_1.leave_type),('company_id', '=', self.env.user.company_id.id),
					                                                  ('employee_type','=', val_1.employee_type.id)])
					if temp_emp:
						carry_value = temp_emp.expiry_value
						expiry_date = None
						expiry_t = temp_emp.encash_type
						current1_date1 = datetime.date.today()
						if expiry_t == 'mon':
							expiry_date = datetime.date(current1_date1.year, carry_value, current1_date1.day)
						else:
							expiry_date = current1_date1 + relativedelta(years=carry_value)

						num, carry, encash = self.carry_forward_leave(each_emp,temp_emp)
						holiday_id = self.env['hr.holidays'].create(
							{
								'employee_id': each_emp.id,
								'state': 'validate',
								'name': "Reset of %s" % val_1.leave_type,
								'type': 'add',
								'number_of_days_temp': carry,
								'carry_fwd_leaves': carry,
								'encash_leave': encash,
								'holiday_status_id': temp_emp.id,
								'carry_fwd_expiry_date': expiry_date
							}
						)

						state_expired_search = self.env['hr.holidays'].search([('company_id', '=', self.env.user.company_id.id),('id','=', holiday_id.id)])
						if state_expired_search:
							holiday_status_id1 = state_expired_search.holiday_status_id.id
							state_expired_search1 = self.env['hr.holidays'].search([('company_id', '=', self.env.user.company_id.id),('name','not like','Reset of'), ('holiday_status_id', '=', holiday_status_id1),('id','!=', holiday_id.id),('type','=','add')])
							# print("the statew and reset is ", state_expired_search)
							# print("the statew and reset and state innnnnnnnnnnnnnnnnnnn ", state_expired_search1)
							# print('val_1.reset_date',val_1.reset_date)
							for values in state_expired_search1:
								# print("the value and the tyope",type(values),values.name)
								values.write({
									'state':'expiry',
									'reset_date':val1_date
								})
						print("the values in the variable are:", num, carry, encash)
						print("the value in the remaining leaves are:",each_emp.id,each_emp.rem_val)
		self.carry_forward_leave_expry_date()

	def carry_forward_leave(self,each_emp,temp_emp):
		carry_forward = None
		encash_leave = None
		num_days_temp = None

		print("the remaining leaves are--------------------------",each_emp,each_emp.rem_val)
		# print(a)
		if each_emp.rem_val <= temp_emp.carry_fwd_value:
			num_days_temp = each_emp.rem_val
		else:
			num_days_temp = temp_emp.carry_fwd_value

		if temp_emp.carry_fwd_type == 'num':
			if each_emp.rem_val <= temp_emp.carry_fwd_value:
				carry_forward = each_emp.rem_val
			else:
				carry_forward = temp_emp.carry_fwd_value
		else:
			carry_forward = each_emp.rem_val* temp_emp.carry_fwd_value / 100

		if temp_emp.encash_type == 'num':
			if each_emp.rem_val<= temp_emp.encash_value:
				encash_leave = each_emp.rem_val
			else:
				encash_leave = temp_emp.encash_value
		else:
			encash_leave = each_emp.rem_val * temp_emp.encash_value / 100
		return num_days_temp,carry_forward,encash_leave

	def carry_forward_leave_expry_date(self):
		obj = self.env['hr.holidays'].search([('carry_fwd_expiry_date','!=',None),('name','like','Reset of'),('company_id', '=', self.env.user.company_id.id)])
		for ob in obj:
			if ob.carry_fwd_expiry_date:
				current_date = datetime.date.today()
				expiry_date = datetime.datetime.strptime(ob.carry_fwd_expiry_date, '%Y-%m-%d')
				if current_date == expiry_date.date():
					ob.write({
						'state':'expiry',
					})
					print("this leave is expired now")
					# print(a)

# Advance accrual button action >  form view
	@api.multi
	def advance_accrual_alloc(self):
		view = self.env.ref('hr_holidays_ext.new_form_view_linked_advance_alloc')
		return {
			'name': ('Advance Accrual Allocation'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'hr.holidays.status',
			'views': [(view.id, 'form')],
			'view_id': view.id,
			'target': 'new',
			'res_id': self.id,
		}

# Custom button form view (Action)
	@api.multi
	def custom_accrual_alloc(self):
		view = self.env.ref('hr_holidays_ext.new_form_view_linked_custom_alloc')
		return {
			'name': ('Advance Custom Allocation'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'hr.holidays.status',
			'views': [(view.id, 'form')],
			'view_id': view.id,
			'target': 'new',
			'res_id': self.id,
		}


class LeaveApproval (models.Model):
	_name = "leave.approval"

	reporting_manager = fields.Boolean (string="Reporting Manager")
	hod = fields.Boolean (string="HOD")
	hr_manager = fields.Boolean (string="HR Manager")
	employee_type = fields.Many2one ('hr.contract.type', string='Employee Type')
	leave_type = fields.Many2one ('hr.holidays.status', string='Leave Type')
	name = fields.Char(default='Leave Approval')
	company_id = fields.Many2one ('res.company', string='Company', default=lambda self: self.env.user.company_id)

	# @api.multi
	# def leave_approval(self):
	# 	view = self.env.ref ('hr_holidays_ext.view_approval_master')
	# 	return {
	# 		'name': ('Leave Approval'),
	# 		'type': 'ir.actions.act_window',
	# 		'view_type': 'form',
	# 		'view_mode': 'form',
	# 		'res_model': 'leave.approval',
	# 		'views': [(view.id, 'form')],
	# 		'view_id': view.id,
	# 		'target': 'new',
	# 		'res_id': self.id,
	# 	}

	# @api.model
	# def create(self, vals):
	# 	""" Restrict that only one record will be created for leave_type and employee_type """
	# 	if 'leave_type' in vals and vals.get ('leave_type') and 'employee_type' in vals and vals.get ('employee_type'):
	# 		approval = self.search_count (
	# 			[('leave_type', '=', vals.get ('leave_type')), ('employee_type', '=', vals.get ('employee_type')),
	# 			 ('company_id', '=', self.env.user.company_id.id)])
	# 	if approval >= 1:
	# 		raise ValidationError("Approval already exists")
	# 	policy = super(LeaveApproval, self).create (vals)
	# 	return policy
	#
	# @api.multi
	# def name_get(self):
	# 	rex = super(LeaveApproval, self).name_get()
	# 	res = []
	# 	for record in self:
	# 		name = record.name
	# 		if record.leave_type and record.employee_type:
	# 			# name = record.name
	# 			name = "%(employee)s %(leave)s approval" % {
	# 				'employee': record.employee_type.name,
	# 				'leave': record.leave_type.name
	# 			}
	# 		res.append((record.id, name))
	# 	return res


class AdvanceAccrualAllocation (models.Model):
	_name = "advance.accru.alloc"

	name = fields.Char (default="Advance Accrual Allocation")
	active = fields.Boolean ('Active', default=True)
	company_id = fields.Many2one ('res.company', string='Company', default=lambda self: self.env.user.company_id)
	employee_type = fields.Many2one ('hr.contract.type', string='Employee Type',related='link_03_ids.employee_type',store=True)
	leave_type = fields.Many2one('hr.holidays.status', string='Leave Type', store=True )
	from_num = fields.Integer (string="From")
	to_num = fields.Integer (string="To")
	count = fields.Float (string='Count')
	indentifier_alloc = fields.Selection (
		[('acc', 'Accrual'), ('start_policy', 'Start of the Policy'),
		 ('start_end_policy', 'Start and End of the Policy')], string='Accrual Type')
	link_03_ids = fields.Many2one('hr.holidays.status')


	@api.model
	def create(self, vals):
		res = super(AdvanceAccrualAllocation, self).create (vals)
		res.leave_type = res.link_03_ids
		return res


class LeavesPolicy (models.Model):
	_name = "leaves.policy"
	_inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

	company_id = fields.Many2one ('res.company', string='Company', default=lambda self: self.env.user.company_id)
	name = fields.Char (default="Leave Policies")
	employee_type = fields.Many2one ('hr.contract.type', string='Employee Type')
	leave_name = fields.Char('Leave Name')
	leave_type = fields.Many2one ('hr.holidays.status', string='Leave Type')
	weekends_leave_period = fields.Selection ([('count', 'Count as leave'), ("dont_count", "Don't count as leave")],
	                                          string="Weekends Between Leave Period")
	# weekends_count = fields.Integer (string="Count After")
	# holiday_leave_period = fields.Selection ([('count', 'Count as leave'), ("dont count", "Don't count as leave")],
	#                                          string="Holidays Between Leave Period")
	# holiday_count = fields.Integer (string="Count After")
	# allow_leave_exceed = fields.Selection (
	# 	[("don't allow", "Don't Allow"), ('allow', 'Allow'), ('lop', 'Allow and Mark as LOP')],
	# 	string="While Applying leave exceed leave balance")
	dur_full = fields.Boolean ('Full Day')
	dur_half = fields.Boolean ('Half Day')
	# dur_quarter = fields.Boolean ('Quarterly')
	# dur_hour = fields.Boolean ('Hourly')
	leave_app_advance_sub = fields.Integer (string='Leave application should be submitted before ')
	min_leave_avail = fields.Integer (string='Minimum leave that can be availed per application ')
	max_leave_avail = fields.Integer (string='Maximum leave that can be availed per application')
	min_leave_app_gap = fields.Integer (string='Minimum gap between two applications')
	min_app_per_year = fields.Integer (string='Minimum number of applications allowed per year')
	leave_not_with = fields.Many2many ('hr.holidays.status', string='This leave can not be taken together with')

	# @api.multi
	# def leave_policy(self):
	# 	view = self.env.ref ('hr_holidays_ext.view_leave_policies_form')
	# 	return {
	# 		'name': ('Leaves Policy'),
	# 		'type': 'ir.actions.act_window',
	# 		'view_type': 'form',
	# 		'view_mode': 'form',
	# 		'res_model': 'leaves.policy',
	# 		'views': [(view.id, 'form')],
	# 		'view_id': view.id,
	# 		'target': 'new',
	# 		'res_id': self.id,
	# 	}

	# @api.model
	# def create(self, vals):
	# 	""" Restrict that only one record will be created for leave_type and employee_type """
	# 	if 'leave_type' in vals and vals.get ('leave_type') and 'employee_type' in vals and vals.get ('employee_type'):
	# 		leave_policy = self.search_count (
	# 			[('leave_type', '=', vals.get ('leave_type')), ('employee_type', '=', vals.get ('employee_type')),
	# 			 ('company_id', '=', self.env.user.company_id.id)])
	# 	if leave_policy >= 1:
	# 		raise ValidationError ("Policy already exists")
	# 	policy = super(LeavesPolicy, self).create (vals)
	# 	return policy
	#
	#
	# @api.multi
	# def name_get(self):
	# 	rex = super (LeavesPolicy, self).name_get ()
	# 	res = []
	# 	for record in self:
	# 		name = record.name
	# 		if record.leave_type and record.employee_type:
	# 			# name = record.name
	# 			name = "%(employee)s %(leave)s policy" % {
	# 				'employee': record.employee_type.name,
	# 				'leave': record.leave_type.name
	# 			}
	# 		res.append((record.id, name))
	# 	return res

class LeaveAdjustment(models.Model):
	_name = 'leave.adjustment'

	# Leave Adjustment Fields For HR
	holiday_id = fields.Many2one('hr.holidays', string="Holiday")
	leave_type = fields.Many2one('hr.holidays.status', string='Leave Type')
	balance = fields.Float("Balance")
	adjusted_days = fields.Float("Adjusted Days")
	adjusted_from_date = fields.Datetime("From Date")
	adjusted_to_date = fields.Datetime("To Date")
	# ref_id = fields.Integer("Refrence Id")
	company_id = fields.Many2one ('res.company', string='Company', default=lambda self: self.env.user.company_id)
	employee_id = fields.Many2one("hr.employee", "Employee Name")