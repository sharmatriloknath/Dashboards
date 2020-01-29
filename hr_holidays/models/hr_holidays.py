# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging
import math
import time
from datetime import timedelta
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools import float_compare
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger (__name__)

HOURS_PER_DAY = 8


class HolidaysType (models.Model):
	_name = "hr.holidays.status"
	_inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
	_description = "Leave Type"

	name = fields.Char ('Leave Type', required=True, translate=True)
	categ_id = fields.Many2one ('calendar.event.type', string='Meeting Type',
	                            help='Once a leave is validated, Odoo will create a '
	                                 'corresponding meeting of this type in the calendar.')
	color_name = fields.Selection ([
		('red', 'Red'),
		('blue', 'Blue'),
		('lightgreen', 'Light Green'),
		('lightblue', 'Light Blue'),
		('lightyellow', 'Light Yellow'),
		('magenta', 'Magenta'),
		('lightcyan', 'Light Cyan'),
		('black', 'Black'),
		('lightpink', 'Light Pink'),
		('brown', 'Brown'),
		('violet', 'Violet'),
		('lightcoral', 'Light Coral'),
		('lightsalmon', 'Light Salmon'),
		('lavender', 'Lavender'),
		('wheat', 'Wheat'),
		('ivory', 'Ivory')], string='Color in Report', required=True, default='red',
		help='This color will be used in the leaves summary located in Reporting > Leaves by Department.')
	limit = fields.Boolean ('Allow to Override Limit',
	                        help='If you select this check box, the system allows the employees to take more leaves '
	                             'than the available ones for this type and will not take them into account for the '
	                             '"Remaining Legal Leaves" defined on the employee form.')
	active = fields.Boolean ('Active', default=True,
	                         help="If the active field is set to false, it will allow you "
	                              "to hide the leave type without removing it.")

	max_leaves = fields.Float (compute='_compute_leaves', string='Maximum Allowed',
	                           help='This value is given by the sum of all leaves'
	                                ' requests with a positive value.')
	leaves_taken = fields.Float (compute='_compute_leaves', string='Leaves Already Taken',
	                             help='This value is given by the sum of all'
	                                  ' leaves requests with a negative value.')
	remaining_leaves = fields.Float (compute='_compute_leaves', string='Remaining Leaves',
	                                 help='Maximum Leaves Allowed - Leaves Already Taken',store=True)
	virtual_remaining_leaves = fields.Float (compute='_compute_leaves', string='Virtual Remaining Leaves',
	                                         help='Maximum Leaves Allowed - Leaves Already Taken - Leaves Waiting Approval')

	double_validation = fields.Boolean (string='Apply Double Validation',
	                                    help="When selected, the Allocation/Leave Requests for this type "
	                                         "require a second validation to be approved.")
	company_id = fields.Many2one ('res.company', string='Company', default=lambda self: self.env.user.company_id,
	                              readonly=True)

	@api.multi
	def get_days(self, employee_id):
		# need to use `dict` constructor to create a dict per id
		result = dict (
			(id, dict (max_leaves=0, leaves_taken=0, remaining_leaves=0, virtual_remaining_leaves=0)) for id in self.ids)

		holidays = self.env['hr.holidays'].search ([
			('employee_id', '=', employee_id),
			('state', 'in', ['confirm', 'validate1', 'validate']),
			('holiday_status_id', 'in', self.ids)
		])

		for holiday in holidays:
			status_dict = result[holiday.holiday_status_id.id]
			if holiday.type == 'add':
				if holiday.state == 'validate':
					# note: add only validated allocation even for the virtual
					# count; otherwise pending then refused allocation allow
					# the employee to create more leaves than possible
					status_dict['virtual_remaining_leaves'] += holiday.number_of_days_temp
					status_dict['max_leaves'] += holiday.number_of_days_temp
					status_dict['remaining_leaves'] += holiday.number_of_days_temp
			elif holiday.type == 'remove':  # number of days is negative
				status_dict['virtual_remaining_leaves'] -= holiday.number_of_days_temp
				if holiday.state == 'validate':
					status_dict['leaves_taken'] += holiday.number_of_days_temp
					status_dict['remaining_leaves'] -= holiday.number_of_days_temp
		return result

	@api.multi
	def _compute_leaves(self):
		data_days = {}
		if 'employee_id' in self._context:
			employee_id = self._context['employee_id']
		else:
			employee_id = self.env['hr.employee'].search ([('user_id', '=', self.env.user.id)], limit=1).id

		if employee_id:
			data_days = self.get_days (employee_id)

		for holiday_status in self:
			result = data_days.get (holiday_status.id, {})
			holiday_status.max_leaves = result.get ('max_leaves', 0)
			holiday_status.leaves_taken = result.get ('leaves_taken', 0)
			holiday_status.remaining_leaves = result.get ('remaining_leaves', 0)
			holiday_status.virtual_remaining_leaves = result.get ('virtual_remaining_leaves', 0)

	@api.multi
	def name_get(self):
		if not self._context.get ('employee_id'):
			# leave counts is based on employee_id, would be inaccurate if not based on correct employee
			return super (HolidaysType, self).name_get ()
		res = []
		for record in self:
			name = record.name
			if not record.limit:
				name = "%(name)s (%(count)s)" % {
					'name': name,
					'count': _ ('%g remaining out of %g') % (record.virtual_remaining_leaves or 0.0, record.max_leaves or 0.0)
				}
			res.append ((record.id, name))
		return res

	@api.model
	def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
		""" Override _search to order the results, according to some employee.
        The order is the following

         - limit (limited leaves first, such as Legal Leaves)
         - virtual remaining leaves (higher the better, so using reverse on sorted)

        This override is necessary because those fields are not stored and depends
        on an employee_id given in context. This sort will be done when there
        is an employee_id in context and that no other order has been given
        to the method.
        """
		leave_ids = super (HolidaysType, self)._search (args, offset=offset, limit=limit, order=order, count=count,
		                                                access_rights_uid=access_rights_uid)
		if not count and not order and self._context.get ('employee_id'):
			leaves = self.browse (leave_ids)
			sort_key = lambda l: (not l.limit, l.virtual_remaining_leaves)
			return leaves.sorted (key=sort_key, reverse=True).ids
		return leave_ids


# Shubham Start
class PublicHolidays (models.Model):
	_name = "hr.publicholidays"
	_description = "Public Holidays"

	attendee_ids = fields.Many2many ('res.partner', string="Attendees")
	taken_seats = fields.Float (string="Taken seats")
	end_date = fields.Date (string="End Date")
	# start_date = fields.Date(string="Start Date", store=True
	#                       , inverse='_set_end_date')

	# public_holiday = fields.Text('Public Holiday Date', readonly=True)
	public_holiday = fields.Date (string="Public Holiday", store=True)
	companies = fields.Many2one ('res.company', 'Companies', required="True",
	                             default=lambda self: self.env.user.company_id.id)
	tag = fields.Many2one ('hr.department', string='Tags')
	holiday_name = fields.Char ('Holiday name', required="True")
	payslip_status1 = fields.Boolean ('Reported in last payslips',
	                                  help='Green this button when the leave has been taken into account in the payslip.')
	holiday_status_id1 = fields.Many2one ("hr.holidays.status", string="Leave Type", required="True")
	employee_id1 = fields.Many2many ('hr.employee', string='Impacted Employees', required="True")
	state = fields.Selection ([
		('draft', 'Draft'),
		('done', 'Done')
	], string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
		help="The status is set to 'Draft', when a Public Holiday request is created." +
		     "\nThe status is 'Done', when Public Holiday request is saved.")

	@api.multi
	def confirm(self):
		self.write ({'state': 'done'})
		return True

	@api.multi
	@api.onchange ('tag')
	def tag_change(self):
		result = {}
		emp_list = []
		if self.tag:
			employee_ids = self.env['hr.employee'].search ([('department_id', '=', self.tag.id)])
			if len (employee_ids) > 0:
				for val in employee_ids:
					emp_list.append (val.id)
			result['domain'] = {'employee_id1': [('id', 'in', tuple (emp_list))]}
		return result


# Shubham End (Public Holidays)


class Holidays (models.Model):
	_name = "hr.holidays"
	_description = "Leave"
	_order = "type desc, date_from desc"
	_inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
	# Nidhi

	color_override = fields.Boolean ('Color', default='get_overriden_leave_requests')

	@api.multi
	def get_overriden_leave_requests(self):
		check_highlight = self.env['hr.holidays.status'].search (
			[('company_id', '=', self.env.user.company_id.id), ('highlight_override', '=', True),
			 ('name', '=', self.holidays_status_id.name)])
		if check_highlight:
			emp = self.env.user.id
			if emp.remaining_leaves < self.number_of_days:
				self.color_override = True
			else:
				self.color_override = False
	visible_invisible = fields.Boolean (compute='_compute_visible_invisible', string='Visible/Invisible',
	                                    help="Used to hide or show the Cancel button for user or manager basis")

	def _compute_visible_invisible(self):
		for leave in self:
			visible_invisible = False
			if leave.create_uid.id == self.env.user.id:
				visible_invisible = True
			leave.visible_invisible = visible_invisible


	def _default_employee(self):
		return self.env.context.get ('default_employee_id') or self.env['hr.employee'].search (
			[('user_id', '=', self.env.uid), ('company_id', '=', self.env.user.company_id.id)], limit=1)

	def _get_default_department_id(self):
		department_id = False
		emp_id = self.env['hr.employee'].search (
			[('user_id', '=', self.env.user.id), ('company_id', '=', self.env.user.company_id.id)])
		if emp_id:
			department_id = emp_id[0].department_id and emp_id[0].department_id.id or False
		return department_id

	def _get_default_manager_id(self):
		manager_id = False
		emp_id = self.env['hr.employee'].search ([('user_id', '=', self.env.user.id)])
		if emp_id:
			manager_id = emp_id.parent_id and emp_id.parent_id.id or False
		# else:
		# 	manager_id = False
		return manager_id


	def _get_default_create_employee_id(self):
		create_employee_id = False
		emp_id = self.env['hr.employee'].search \
			([('user_id', '=', self.env.user.id)])
		if emp_id:
			create_employee_id = emp_id.id or False
		# else:
		# 	manager_id = False
		return create_employee_id

	# def _get_default_create_hod_id(self):
	# 	create_hod_id = False
	# 	emp_id = self.env['hr.employee'].search ([('user_id', '=', self.env.user.id)])
	# 	print("EMP ID", emp_id)
	# 	if emp_id:
	# 		create_hod_id = emp_id.hod or False
	# 	# else:
	# 	# 	manager_id = False
	# 	return create_hod_id

	create_employee_id = fields.Many2one ('hr.employee', 'Create Employee', default= _get_default_create_employee_id,
	                                      help="Created Employee: Used to maintain the hierarchy visibility of records in Record Rules")
	# create_hod_id = fields.Many2one ('hr.employee', 'Create Employee', default=_get_default_create_hod_id,
	#                                  help="Created HoD: Used to maintain the hierarchy visibility of records in Record Rules")
	company_id = fields.Many2one ('res.company', string='Company', default=lambda self: self.env.user.company_id)
	name = fields.Char ('Description')
	state = fields.Selection ([
		('draft', 'To Submit'),
		('cancel', 'Cancelled'),
		('confirm', 'To Approve'),
		('refuse', 'Refused'),
		('validate1', 'Second Approval'),
		('validate', 'Approved'),
		('expiry','Expiry')
	], string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
		help="The status is set to 'To Submit', when a leave request is created." +
		     "\nThe status is 'To Approve', when leave request is confirmed by user." +
		     "\nThe status is 'Refused', when leave request is refused by manager." +
		     "\nThe status is 'Approved', when leave request is approved by manager.")

	payslip_status = fields.Boolean ('Reported in last payslips',
	                                 help='Green this button when the leave has been taken into account in the payslip.')
	report_note = fields.Text ('HR Comments')
	user_id = fields.Many2one ('res.users', string='User', related='employee_id.user_id', related_sudo=True, store=True,
	                           default=lambda self: self.env.uid, readonly=True)
	date_from = fields.Datetime ('Start Date', readonly=True, index=True, copy=False,
	                             states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
	                             track_visibility='onchange')
	date_to = fields.Datetime ('End Date', readonly=True, copy=False,
	                           states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
	                           track_visibility='onchange')
	# Nidhi to put domain on Request checked allocation leaves
	holiday_status_id = fields.Many2one ("hr.holidays.status", string="Leave Type", required=True, readonly=True,
	                                     states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

	# Nidhi Start: to ensure Allocation Request can only be done as per Leave Type permission

	@api.onchange ('type')
	def allocation_requested_leaves(self):
		result = {}
		leave_list = []
		if self.type == 'add':
			request_leave_types = self.env['hr.holidays.status'].search (
				[('company_id', '=', self.env.user.company_id.id), ('alloc_request', '=', True)])
			if request_leave_types:
				if len (request_leave_types) > 0:
					for val in request_leave_types:
						leave_list.append (val.id)
				result['domain'] = {'holiday_status_id': [('id', 'in', tuple (leave_list))]}
		return result

	employee_id = fields.Many2one ('hr.employee', string='Employee', index=True, readonly=True,
	                               states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
	                               default=_default_employee, track_visibility='onchange')
	manager_id = fields.Many2one ('hr.employee', string='Manager', readonly=True)
	notes = fields.Text ('Reasons', readonly=True,
	                     states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
	number_of_days_temp = fields.Float (
		'Allocation', copy=False, readonly=True,
		states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
		help='Number of days of the leave request according to your working schedule.')
	number_of_days = fields.Float ('Number of Days', compute='_compute_number_of_days', store=True,
	                               track_visibility='onchange')
	meeting_id = fields.Many2one ('calendar.event', string='Meeting')
	type = fields.Selection ([
		('remove', 'Leave Request'),
		('add', 'Allocation Request'),
		('expiry', 'Expired')  # Expiry added Nidhi
	], string='Request Type', required=True, readonly=True, index=True, track_visibility='always', default='remove',
		states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
		help="Choose 'Leave Request' if someone wants to take an off-day."
		     "\nChoose 'Allocation Request' if you want to increase the number of leaves available for someone")
	parent_id = fields.Many2one ('hr.holidays', string='Parent', copy=False)
	linked_request_ids = fields.One2many ('hr.holidays', 'parent_id', string='Linked Requests')
	department_id = fields.Many2one ('hr.department', string='Department', readonly=True,
	                                 default=_get_default_department_id)
	category_id = fields.Many2one ('hr.employee.category', string='Employee Tag', readonly=True,
	                               states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
	                               help='Category of Employee')
	holiday_type = fields.Selection ([
		('employee', 'By Employee'),
		('category', 'By Employee Tag')], string='Allocation Mode', readonly=True, required=True, default='employee',
		states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
		help='By Employee: Allocation/Request for individual Employee,'
		     ' By Employee Tag: Allocation/Request for group of employees in category')
	first_approver_id = fields.Many2one('hr.employee', string='First Approval', readonly=True, copy=False,
	                                     default=_get_default_manager_id,
	                                     help='This area is automatically filled by the user who validate the leave',
	                                     oldname='manager_id')
	second_approver_id = fields.Many2one ('hr.employee', string='Second Approval', readonly=True, copy=False,
	                                      oldname='manager_id2',
	                                      help='This area is automaticly filled by the user who validate '
	                                           'the leave with second level (If Leave type need second validation)')
	double_validation = fields.Boolean('Apply Double Validation', related='holiday_status_id.double_validation')
	can_reset = fields.Boolean('Can reset', compute='_compute_can_reset')
	create_approval_id = fields.One2many('leaves.approval.require', 'assigned_01')  # Nidhi - linking with leave approval
	ismanager = fields.Boolean("User is Manager", compute='check_if_manager')  # Nidhi
	allocate_date = fields.Date("Allocation date")
	# check_no_of_days = fields.Float('Check no of days')  #No use of this field created only for testing purpose

	@api.onchange ('employee_id')
	def _onchange_holiday_status_id(self):
		res = {}
		leave_type_list=[]
		employee_leaves = self.env['hr.holidays.status'].search(
			[('employee_type', '=', self.employee_id.employee_type.id)])
		if len(employee_leaves) > 0:
			for val in employee_leaves:
				if self.type == 'add':
					if val.alloc_request:
						leave_type_list.append(val.id)
				else:
					leave_type_list.append(val.id)
			res['domain'] = {'holiday_status_id': [('id','in',tuple(leave_type_list))]}

		return res


	@api.multi
	@api.depends ('holiday_type')
	def check_if_manager(self):
		res_user = self.env['res.users'].search(
			[('id', '=', self.env.uid), ('company_id', '=', self.env.user.company_id.id)])
		user = self.env['hr.employee'].search(
			[('user_id', '=', res_user.id), ('company_id', '=', self.env.user.company_id.id)])
		manager = self.env['hr.employee'].search (
			[('parent_id', '=', user.id), ('company_id', '=', self.env.user.company_id.id)])
		for val in self:
			if len(manager) > 0:
				val.ismanager = True
			else:
				val.ismanager = False


	@api.multi
	@api.depends ('number_of_days_temp', 'type')
	def _compute_number_of_days(self):
		for holiday in self:
			if holiday.type == 'remove':
				holiday.number_of_days = -holiday.number_of_days_temp
			else:
				holiday.number_of_days = holiday.number_of_days_temp

	@api.multi
	def _compute_can_reset(self):
		""" User can reset a leave request if it is its own leave request or if he is an Hr Manager."""
		user = self.env.user
		group_hr_manager = self.env.ref ('hr_holidays.group_hr_holidays_manager')
		for holiday in self:
			if group_hr_manager in user.groups_id or holiday.employee_id and holiday.employee_id.user_id == user:
				holiday.can_reset = True

	@api.multi
	def get_days(self, employee_id):
		# need to use `dict` constructor to create a dict per id
		result = dict (
			(id, dict (max_leaves=0, leaves_taken=0, remaining_leaves=0, virtual_remaining_leaves=0)) for id in
			self.ids)

		holidays = self.env['hr.holidays'].search ([
			('employee_id', '=', employee_id),
			('state', 'in', ['confirm', 'validate1', 'validate']),
			('holiday_status_id', 'in', self.ids)
		])

		for holiday in holidays:
			status_dict = result[holiday.holiday_status_id.id]
			if holiday.type == 'add':
				if holiday.state == 'validate':
					# note: add only validated allocation even for the virtual
					# count; otherwise pending then refused allocation allow
					# the employee to create more leaves than possible
					status_dict['virtual_remaining_leaves'] += holiday.number_of_days_temp
					status_dict['max_leaves'] += holiday.number_of_days_temp
					status_dict['remaining_leaves'] += holiday.number_of_days_temp
			elif holiday.type == 'remove':  # number of days is negative
				status_dict['virtual_remaining_leaves'] -= holiday.number_of_days_temp
				if holiday.state == 'validate':
					status_dict['leaves_taken'] += holiday.number_of_days_temp
					status_dict['remaining_leaves'] -= holiday.number_of_days_temp
		return result

	@api.constrains ('date_from', 'date_to')
	def _check_date(self):
		for holiday in self:
			if holiday.type == 'remove':
				domain = [
					('date_from', '<=', holiday.date_to),
					('date_to', '>=', holiday.date_from),
					('employee_id', '=', holiday.employee_id.id),
					('id', '!=', holiday.id),
					('type', '=', holiday.type),
					('state', 'not in', ['cancel', 'refuse']),
				]
				nholidays = self.search_count (domain)
				if nholidays:
					raise ValidationError (_ ('You can not have 2 leaves that overlaps on same day!'))

	@api.constrains ('state', 'number_of_days_temp', 'holiday_status_id')
	def _check_holidays(self):
		for holiday in self:
			if holiday.holiday_type != 'employee' or holiday.type != 'remove' or not holiday.employee_id or holiday.holiday_status_id.limit:
				continue
			leave_days = holiday.holiday_status_id.get_days (holiday.employee_id.id)[holiday.holiday_status_id.id]
			# if float_compare (leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or \
			# 				float_compare (leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
			if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == 0 or \
					float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == 0:
				raise ValidationError (_ ('The number of remaining leaves is not sufficient for this leave type.\n'
				                          'Please verify also the leaves waiting for validation.'))

	_sql_constraints = [
		# ('type_value',
		#  "CHECK( (holiday_type='employee' AND employee_id IS NOT NULL) or (holiday_type='category' AND category_id IS NOT NULL))",
		#  "The employee or employee category of this request is missing. Please make sure that your user login is linked to an employee."),
		('date_check2', "CHECK ( (type='add') OR (date_from <= date_to))",
		 "The start date must be anterior to the end date."),
		('date_check', "CHECK ( number_of_days_temp >= 0 )", "The number of days must be greater than 0."),
	]

	@api.onchange('date_from', 'date_to')
	def _onchange_date_from(self):
		""" If there are no date set for date_to, automatically set one day later than the date_from. Also update the number_of_days."""
		date_from = self.date_from
		date_to = self.date_to
		self.compute_valid_leaves_for_employee(date_from, date_to)

		# policy_id = self.env['leaves.policy'].sudo().search(
		# 	[('leave_type', '=', self.holiday_status_id.id), ('company_id', '=', self.env.user.company_id.id)])
		# if date_from and not date_to:
		# 	date_to_with_delta = fields.Datetime.from_string(date_from) + timedelta(hours=8)
		# 	self.date_to = str(date_to_with_delta)
		# 	number_of_day = (datetime.strptime(self.date_to, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(date_from, DEFAULT_SERVER_DATETIME_FORMAT)).total_seconds()/(24*3600)
		# 	self.number_of_days_temp = number_of_day
		# # Compute and update the number of days
		# if (date_to and date_from) and (date_from <= date_to):
		# 	if policy_id:
		# 		for val in policy_id:
		# 			number_of_days = 0
		# 			if val.weekends_leave_period == 'dont_count':
		# 				num_days = self._get_number_of_days(date_from, date_to, self.employee_id.id)
		# 				date_to1 = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
		# 				date_from1 = datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
		#
		# 				# Logic of Public Holidays when week offs count as holidays is True 2019-11-19
		# 				emp_shift = self.employee_id.resource_calendar_ids
		# 				global_leaves = emp_shift.global_leave_ids
		# 				# List to store the global leaves
		# 				public_holidays = []
		# 				for holiday in global_leaves:
		# 					public_holidays.append((holiday.date_from, holiday.date_to))
		#
		# 				# Public holidays between leave period
		# 				leave_period_dates = []
		# 				start_date = date_from1.date()
		# 				end_date = date_to1.date()
		# 				delta = end_date - start_date
		# 				for i in range(delta.days + 1):
		# 					day = start_date + timedelta(days=i)
		# 					leave_period_dates.append(day)
		# 				count = 0
		# 				for date in public_holidays:
		# 					if datetime.strptime(date[0], '%Y-%m-%d %H:%M:%S').date() in leave_period_dates:
		# 						count += 1
		# 			# End of Public Holidays logic
		#
		# 				self.number_of_days_temp = num_days - count
		# 			else:
		# 				number_of_days = self._get_number_of_days(date_from, date_to, self.employee_id.id)
		# 				date_to1 = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
		# 				date_from1 = datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
		# 				if val.dur_full and not val.dur_half:
		# 					total_days = (date_to1 - date_from1).days
		# 				else:
		# 					total_seconds = (date_to1 - date_from1).seconds
		# 					total_days = total_seconds / (24 * 3600)
		#
		# 				week_offs = total_days - number_of_days
		# 				self.number_of_days_temp = number_of_days + week_offs
		# 	else:
		# 		# self.number_of_days_temp = self._get_number_of_days(date_from, date_to, self.employee_id.id)
		# 		number_of_day = (datetime.strptime(self.date_to, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(
		# 			date_from, DEFAULT_SERVER_DATETIME_FORMAT)).total_seconds() / (24 * 3600)
		# 		self.number_of_days_temp = number_of_day
		#
		# elif (date_to and date_from) and (date_from > date_to):
		# 	raise ValidationError("From Date cannot be greater then To Date")
		# else:
		# 	self.number_of_days_temp = 0

	@api.onchange('holiday_type')
	def _onchange_type(self):
		if self.holiday_type == 'employee' and not self.employee_id:
			self.employee_id = self.env['hr.employee'].search ([('user_id', '=', self.env.uid)], limit=1)
		elif self.holiday_type != 'employee':
			self.employee_id = None

		# Nidhi 28 May/19 On onchange of employee on Leave Request

	@api.onchange ('holiday_status_id')
	def _onchange_employee_id(self):
		if not self.employee_id and self.holiday_status_id:
			return {}
		self.manager_id = self.employee_id and self.employee_id.parent_id
		self.department_id = self.employee_id.department_id
# Nidhi for on change approvers
		emp = self.env['hr.employee'].search ([('user_id', '=', self.env.uid)])
		if emp:
			manager = emp[0].parent_id
			hod = emp[0].hod
			check_leave = self.env['leave.approval'].search ([('leave_type', '=', self.holiday_status_id.id)])
			print("Check_leave", check_leave)

			for check in check_leave:
				if check:
					data = []
					self.create_approval_id = ""
					if check.reporting_manager and emp.parent_id:
						val_data_0 = (0, False, {
							'approver': manager.id,
							'designation': manager.job_id.name,
							'status': 'Draft',
						})
						data.append (val_data_0)
					if check.hod and emp.hod:
						val_data_1 = (0, False, {
							'approver': hod.id,
							'designation': hod.job_id.name,
							'status': 'Draft',
						})
						data.append (val_data_1)
					self.create_approval_id = data
					# return {}

			# Written in one to many

	def _get_number_of_days(self, date_from, date_to, employee_id):
		""" Returns a float equals to the timedelta between two dates given as string."""
		from_dt = fields.Datetime.from_string (date_from)
		to_dt = fields.Datetime.from_string (date_to)
		if employee_id:
			employee = self.env['hr.employee'].browse (employee_id)

			# Testing 16/11/19
			shift = employee.resource_calendar_ids
			return employee.get_work_days_count (from_dt, to_dt, shift)

		time_delta = to_dt - from_dt
		return math.ceil (time_delta.days + float (time_delta.seconds) / 86400)

	# @api.onchange ('date_from')
	# def _onchange_date_from(self):
	# 	""" If there are no date set for date_to, automatically set one 8 hours later than the
	# 	date_from. Also update the number_of_days."""
	# 	date_from = self.date_from
	# 	date_to = self.date_to
	#
	# 	# No date_to set so far: automatically compute one 8 hours later
	# 	if date_from and not date_to:
	# 		date_to_with_delta = fields.Datetime.from_string (date_from) + timedelta (hours=HOURS_PER_DAY)
	# 		self.date_to = str (date_to_with_delta)
	#
	# 	# Compute and update the number of days
	# 	if (date_to and date_from) and (date_from <= date_to):
	# 		self.number_of_days_temp = self._get_number_of_days (date_from, date_to, self.employee_id.id)
	# 	else:
	# 		self.number_of_days_temp = 0
	#
	# @api.onchange ('date_to')
	# def _onchange_date_to(self):
	# 	""" Update the number_of_days. """
	# 	date_from = self.date_from
	# 	date_to = self.date_to
	#
	# 	# Compute and update the number of days
	# 	if (date_to and date_from) and (date_from <= date_to):
	# 		self.number_of_days_temp = self._get_number_of_days (date_from, date_to, self.employee_id.id)
	# 	else:
	# 		self.number_of_days_temp = 0

	####################################################
	# ORM Overrides methods
	####################################################

	@api.multi
	def name_get(self):
		res = []
		for leave in self:
			if leave.type == 'remove':
				if self.env.context.get ('short_name'):
					res.append ((leave.id, _ ("%s : %.2f day(s)") % (
						leave.name or leave.holiday_status_id.name, leave.number_of_days_temp)))
				else:
					res.append ((leave.id, _ ("%s on %s : %.2f day(s)") % (
						leave.employee_id.name or leave.category_id.name, leave.holiday_status_id.name, leave.number_of_days_temp)))
			else:
				res.append ((leave.id, _ ("Allocation of %s : %.2f day(s) To %s") % (
					leave.holiday_status_id.name, leave.number_of_days_temp, leave.employee_id.name)))
		return res

	# def _check_state_access_right(self, vals):
	# 	if vals.get ('state') and vals['state'] not in ['draft', 'confirm', 'cancel'] and not self.env[
	# 		'res.users'].has_group ('hr_holidays.group_hr_holidays_user'):
	# 		return False
	# 	return True

	@api.multi
	def add_follower(self, employee_id):
		employee = self.env['hr.employee'].browse (employee_id)
		if employee.user_id:
			self.message_subscribe_users (user_ids=employee.user_id.ids)

	@api.model
	def create(self, values):
		""" Override to avoid automatic logging of creation """
		employee_id = values.get('employee_id', False)
		print("the val in the dict", values)
		if (values.get('date_from') and values.get('date_to')) == False:
			current = datetime.strftime(datetime.today().date(),'%Y-%m-%d')
			values.update({'allocate_date': current})
			print(values)
		if not values.get('department_id'):
			values.update({'department_id': self.env['hr.employee'].browse (employee_id).department_id.id})

		holiday = super (Holidays, self.with_context (mail_create_nolog=True, mail_create_nosubscribe=True)).create(values)
		holiday.add_follower (employee_id)

		# Trilok code for policies
		policy_id = holiday.env['leaves.policy'].search(
			[('leave_type', '=', holiday.holiday_status_id.id), ('company_id', '=', self.env.user.company_id.id)])
		# print ("policy iddddddddddddddd",policy_id)
		emp_type = holiday.employee_id.employee_type.id
		for val in policy_id:
			if val.employee_type.id == emp_type:
				for employee in holiday.employee_id:
					if holiday.type == 'remove':
						query = '''select count(*) from hr_holidays where upper(type) = upper('rEMove')and upper(state) = upper('Validate') and create_date::date between to_date(concat(date_part('Year',now()::date),'-01-01'),'yyyy-mm-dd') and now()::date and employee_id = %s''' % employee.id
						holiday.env.cr.execute(query)
						query_result = holiday.env.cr.dictfetchone()
						# print("query_result", query_result)
						if val.min_app_per_year > 0 and query_result["count"] > val.min_app_per_year:
							raise ValidationError("maximum number of applications per year is {} days".format(val.min_app_per_year))

						query1 = '''select create_date::date,date_to::date from hr_holidays where upper(type) = 
						upper('rEMove') and upper(state) = upper('Validate') and create_date::date between to_date(concat(date_part('Year',now()::date),'-01-01'),'yyyy-mm-dd') 
		                       and now()::date and employee_id = %s order by create_date desc limit 1'''\
								 % employee.id
						holiday.env.cr.execute(query1)
						query_result1 = holiday.env.cr.fetchall()
						if query_result1 is not None:
							# print("query_resulttttttttttttttttttttttttttt", query_result1)
							# print("query_resulttttttttttttttttttttttttttt", query_result1[0][0], query_result1[0][1])
							cre_date = datetime.strptime(query_result1[0][0], '%Y-%m-%d')
							date_to = datetime.strptime(query_result1[0][1], '%Y-%m-%d')
							# print("cre_date", cre_date, type(cre_date))
							current_dt = fields.Datetime.now()
							# cdate=datetime.strptime(current_dt,'%Y-%m-%d')
							current_date = datetime.strptime(current_dt.split(" ")[0], '%Y-%m-%d')
							days = (current_date - date_to).days
							if val.min_leave_app_gap > 0 and days > val.min_leave_app_gap:
								raise ValidationError(
									"Minimum gap between two application should be atleast {} days".format(
										val.min_leave_app_gap))

		return holiday

	@api.multi
	def write(self, values):
		employee_id = values.get ('employee_id', False)
		print ("MAIN write CALLEDDDDDDDDDDDD")
		# if not self._check_state_access_right (values):
		# 	raise AccessError (
		# 		_ ('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % values.get ('state'))
		result = super (Holidays, self).write (values)
		self.add_follower (employee_id)
		# if 'employee_id' in values: # Nidhi
		# 	self._onchange_employee_id ()
		return result

	@api.multi
	def unlink(self):
		for holiday in self.filtered (lambda holiday: holiday.state not in ['draft', 'cancel', 'confirm']):
			raise UserError (_ ('You cannot delete a leave which is in %s state.') % (holiday.state,))
		return super (Holidays, self).unlink ()

	####################################################
	# Business methods
	####################################################

	@api.multi
	def _create_resource_leave(self):
		""" This method will create entry in resource calendar leave object at the time of holidays validated """
		for leave in self:
			self.env['resource.calendar.leaves'].create ({
				'name': leave.name,
				'date_from': leave.date_from,
				'holiday_id': leave.id,
				'date_to': leave.date_to,
				'resource_id': leave.employee_id.resource_id.id,
				'calendar_id': leave.employee_id.resource_calendar_id.id
			})
		return True

	@api.multi
	def _remove_resource_leave(self):
		""" This method will create entry in resource calendar leave object at the time of holidays cancel/removed """
		return self.env['resource.calendar.leaves'].search ([('holiday_id', 'in', self.ids)]).unlink ()

	@api.multi
	def action_draft(self):
		for holiday in self:
			if not holiday.can_reset:
				raise UserError (_ ('Only an HR Manager or the concerned employee can reset to draft.'))
			if holiday.state not in ['confirm', 'refuse']:
				raise UserError (_ ('Leave request state must be "Refused" or "To Approve" in order to reset to Draft.'))
			holiday.write ({
				'state': 'draft',
				'first_approver_id': False,
				'second_approver_id': False,
			})
			linked_requests = holiday.mapped ('linked_request_ids')
			for linked_request in linked_requests:
				linked_request.action_draft ()
			linked_requests.unlink ()
		return True

	@api.multi  # keep as is Nidhi
	def action_confirm(self):
		if self.filtered (lambda holiday: holiday.state != 'draft'):
			raise UserError (_ ('Leave request must be in Draft state ("To Submit") in order to confirm it.'))
		if self.create_approval_id:  # Nidhi
			for val in self.create_approval_id:
				val.write ({'status': 'To Submit', 'status_date': time.strftime (DEFAULT_SERVER_DATETIME_FORMAT)})
		return self.write ({'state': 'confirm'})

	# Nidhi
	# @api.multi
	# def _check_security_action_approve(self):
	# 	if not self.env.user.has_group ('hr_holidays.group_hr_holidays_user'):
	# 		raise UserError (_('Only an HR Officer or Manager can approve leave requests.'))

	@api.multi
	def action_approve(self):  # Nidhi
		# if double_validation: this method is the first approval approval
		# if not double_validation: this method calls action_validate() below

		# self._check_security_action_approve ()
		current_employee = self.env['hr.employee'].search ([('user_id', '=', self.env.uid)], limit=1)
		for holiday in self:
			if holiday.state != 'confirm':
				raise UserError (_ ('Leave request must be confirmed ("To Approve") in order to approve it.'))
			if holiday.double_validation:
				if holiday.create_approval_id:
					for val in holiday.create_approval_id:
						val.write ({'status': 'Approved', 'status_date': time.strftime (DEFAULT_SERVER_DATETIME_FORMAT),
						            'remarks': self.report_note})
				return holiday.write ({'state': 'validate1', 'first_approver_id': current_employee.id, })
			else:
				holiday.action_validate ()

	@api.multi
	def _prepare_create_by_category(self, employee):
		self.ensure_one ()
		values = {
			'name': self.name,
			'type': self.type,
			'holiday_type': 'employee',
			'holiday_status_id': self.holiday_status_id.id,
			'date_from': self.date_from,
			'date_to': self.date_to,
			'notes': self.notes,
			'number_of_days_temp': self.number_of_days_temp,
			'parent_id': self.id,
			'employee_id': employee.id
		}
		return values

	@api.multi
	def _check_security_action_validate(self):
		if not self.env.user.has_group ('hr_holidays.group_hr_holidays_user'):
			raise UserError (_ ('Only an HR Officer or Manager can approve leave requests.'))

	@api.multi
	def action_validate(self):
		# self._check_security_action_validate ()
		current_employee = self.env['hr.employee'].search ([('user_id', '=', self.env.uid)], limit=1)
		for holiday in self:
			if holiday.state not in ['confirm', 'validate1']:
				raise UserError (_ ('Leave request must be confirmed in order to approve it.'))
			if holiday.state == 'validate1' and not holiday.env.user.has_group ('hr_holidays.group_hr_holidays_manager'):
				raise UserError (_ ('Only an HR Manager can apply the second approval on leave requests.'))
			# Trilok Changes 17-01-2020
			if holiday.holiday_status_id.name in ('Casual Leaves', 'earned leaves') and holiday.type == 'remove':
				holiday.leave_managed_by_hr_manager(holiday)
			else:
				# end changes
				holiday.write ({'state': 'validate'})
			# holiday.write({'state': 'validate'})
			if holiday.double_validation:
				if holiday.create_approval_id:
					for val in holiday.create_approval_id:
						val.write ({'status': 'Second Approval', 'status_date': time.strftime (DEFAULT_SERVER_DATETIME_FORMAT)})
				holiday.write ({'second_approver_id': current_employee.id, 'approver': current_employee.id})
			else:
				if holiday.create_approval_id:
					for val in holiday.create_approval_id:
						val.write ({'status': 'Second Approval', 'status_date': time.strftime (DEFAULT_SERVER_DATETIME_FORMAT),
						            'remarks': self.report_note})
				holiday.write ({'first_approver_id': current_employee.id, 'approver': current_employee.id})
			if holiday.holiday_type == 'employee' and holiday.type == 'remove':
				holiday._validate_leave_request ()
			elif holiday.holiday_type == 'category':
				leaves = self.env['hr.holidays']
				for employee in holiday.category_id.employee_ids:
					values = holiday._prepare_create_by_category (employee)
					leaves += self.with_context (mail_notify_force_send=False).create (values)
				# TODO is it necessary to interleave the calls?
				leaves.action_approve ()
				if leaves and leaves[0].double_validation:
					leaves.action_validate ()
		return True

	def _validate_leave_request(self):
		""" Validate leave requests (holiday_type='employee' and holiday.type='remove')
        by creating a calendar event and a resource leaves. """
		for holiday in self.filtered (lambda request: request.type == 'remove' and request.holiday_type == 'employee'):
			meeting_values = holiday._prepare_holidays_meeting_values ()
			meeting = self.env['calendar.event'].with_context (no_mail_to_attendees=True).create (meeting_values)
			holiday.write ({'meeting_id': meeting.id})
			holiday._create_resource_leave ()

	@api.multi
	def _prepare_holidays_meeting_values(self):
		self.ensure_one ()
		meeting_values = {
			'name': self.display_name,
			'categ_ids': [(6, 0, [
				self.holiday_status_id.categ_id.id])] if self.holiday_status_id.categ_id else [],
			'duration': self.number_of_days_temp * HOURS_PER_DAY,
			'description': self.notes,
			'user_id': self.user_id.id,
			'start': self.date_from,
			'stop': self.date_to,
			'allday': False,
			'state': 'open',  # to block that meeting date in the calendar
			'privacy': 'confidential'
		}
		# Add the partner_id (if exist) as an attendee
		if self.user_id and self.user_id.partner_id:
			meeting_values['partner_ids'] = [
				(4, self.user_id.partner_id.id)]
		return meeting_values

	@api.multi
	def action_refuse(self):
		# self._check_security_action_refuse ()
		current_employee = self.env['hr.employee'].search ([('user_id', '=', self.env.uid)], limit=1)
		for holiday in self:
			if holiday.state not in ['confirm', 'validate', 'validate1']:
				raise UserError (_ ('Leave request must be confirmed or validated in order to refuse it.'))
			if holiday.state == 'validate1':
				if holiday.create_approval_id:
					for val in holiday.create_approval_id:
						val.write ({'status': 'Refused', 'status_date': time.strftime (DEFAULT_SERVER_DATETIME_FORMAT),
						            'remarks': self.report_note})
				holiday.write ({'state': 'refuse', 'first_approver_id': current_employee.id})
			else:
				if holiday.create_approval_id:
					for val in holiday.create_approval_id:
						val.write ({'status': 'Refused', 'status_date': time.strftime (DEFAULT_SERVER_DATETIME_FORMAT),
						            'remarks': self.report_note})
				holiday.write ({'state': 'refuse', 'second_approver_id': current_employee.id})
			# Delete the meeting
			if holiday.meeting_id:
				holiday.meeting_id.unlink ()
			# If a category that created several holidays, cancel all related
			holiday.linked_request_ids.action_refuse ()
		self._remove_resource_leave ()
		return True

	# Nidhi Commented below code to not go by group access
	# @api.multi
	# def _check_security_action_refuse(self):
	# 	if not self.env.user.has_group ('hr_holidays.group_hr_holidays_user'):
	# 		raise UserError (_ ('Only an HR Officer or Manager can refuse leave requests.'))

	####################################################
	# Messaging methods
	####################################################

	@api.multi
	def _track_subtype(self, init_values):
		if 'state' in init_values and self.state == 'validate':
			return 'hr_holidays.mt_holidays_approved'
		elif 'state' in init_values and self.state == 'validate1':
			return 'hr_holidays.mt_holidays_first_validated'
		elif 'state' in init_values and self.state == 'confirm':
			return 'hr_holidays.mt_holidays_confirmed'
		elif 'state' in init_values and self.state == 'refuse':
			return 'hr_holidays.mt_holidays_refused'
		return super (Holidays, self)._track_subtype (init_values)

	@api.multi
	def _notification_recipients(self, message, groups):
		""" Handle HR users and officers recipients that can validate or refuse holidays
        directly from email. """
		groups = super (Holidays, self)._notification_recipients (message, groups)

		self.ensure_one ()
		hr_actions = []
		if self.state == 'confirm':
			app_action = self._notification_link_helper ('controller', controller='/hr_holidays/validate')
			hr_actions += [{'url': app_action, 'title': _ ('Approve')}]
		if self.state in ['confirm', 'validate', 'validate1']:
			ref_action = self._notification_link_helper ('controller', controller='/hr_holidays/refuse')
			hr_actions += [{'url': ref_action, 'title': _ ('Refuse')}]

		new_group = (
			'group_hr_holidays_user', lambda partner: bool (partner.user_ids) and any (
				user.has_group ('hr_holidays.group_hr_holidays_user') for user in partner.user_ids), {
				'actions': hr_actions,
			})

		return [new_group] + groups

	@api.multi
	def _message_notification_recipients(self, message, recipients):
		result = super (Holidays, self)._message_notification_recipients (message, recipients)
		leave_type = self.env[message.model].browse (message.res_id).type
		title = _ ("See Leave") if leave_type == 'remove' else _ ("See Allocation")
		for res in result:
			if result[res].get ('button_access'):
				result[res]['button_access']['title'] = title
		return result


 # Nidhi 28 May/19 Leaves approval
class LeavesApproval (models.Model):
	_name = 'leaves.approval.require'

	approver = fields.Many2one ('hr.employee', 'Name of Approving Authority')
	assigned_01 = fields.Many2one ('hr.holidays')
	designation = fields.Char ('Designation')
	status = fields.Char ('Status')
	status_date = fields.Date ('Status Date')
	remarks = fields.Char ('Remarks')
	company_id = fields.Many2one ('res.company', string='Company', default=lambda self: self.env.user.company_id)


 # new approval process table added Nidhi 28 May/19
