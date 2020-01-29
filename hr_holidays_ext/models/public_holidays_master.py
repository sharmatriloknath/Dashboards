from odoo import api, fields, models
import datetime
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import date


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    holiday_master_id = fields.Many2one('holidays.master', 'Holiday Master')


class HolidaysMaster (models.Model):
	_name = 'holidays.master'

	name = fields.Char("Holidays List")
	description = fields.Char("Description")
	region_id = fields.Many2one('region', 'Region')
	year = fields.Selection([(num, str(num)) for num in range((datetime.datetime.now().year) - 5, (datetime.datetime.now().year)+5)], 'Year')
	global_leaves_ids = fields.One2many(
		'resource.calendar.leaves', 'holiday_master_id', 'Public Leaves',
	)
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

	@api.onchange('region_id')
	def name_of_holiday_get(self):
		if self.region_id:
			self.name = str(self.region_id.name)+'-'+str(self.year)

	@api.multi
	def copy(self, default=None):
		default = dict(default or {})
		default.update({'global_leaves_ids': [(0, False, {
			'name': line.name,
			'date_from': line.date_from,
			'date_to': line.date_to,
		}) for line in self.global_leaves_ids]})
		return super(HolidaysMaster, self).copy(default)

	def all_years_list(self):
		list = []
		query = "select  * from holidays_master where company_id=%s" % (
			self.env.user.company_id.id)
		self.env.cr.execute(query)
		data = self.env.cr.dictfetchall()
		if data:
			for item in data:
				list.append(item['id'])
		action = self.env.ref('hr_holidays_ext.public_holidays_action_view')
		result = action.read()[0]
		res = self.env.ref('hr_holidays_ext.Public_holiday_tree_view', False)
		res_form = self.env.ref('hr_holidays_ext.holiday_master_form_view', False)
		result['views'] = [(res and res.id or False, 'list'), (res_form and res_form.id or False, 'form')]
		result['domain'] = [('id', 'in', tuple(list))]
		result['target'] = 'main'
		result['view_type'] = 'tree'
		result['view_mode'] = 'tree,form'
		return result

	def previous_years_list(self):
		list = []
		query = "select  * from holidays_master where year < date_part('year', current_timestamp) and company_id=%s" %(self.env.user.company_id.id)
		self.env.cr.execute(query)
		data = self.env.cr.dictfetchall()
		if data:
			for item in data:
				list.append(item['id'])
		action = self.env.ref('hr_holidays_ext.public_holidays_action_view')
		result = action.read()[0]
		res = self.env.ref('hr_holidays_ext.Public_holiday_tree_view', False)
		res_form = self.env.ref('hr_holidays_ext.holiday_master_form_view', False)
		result['views'] = [(res and res.id or False, 'list'), (res_form and res_form.id or False, 'form')]
		result['domain'] = [('id', 'in', tuple(list))]
		result['target'] = 'main'
		result['view_type'] = 'tree'
		result['view_mode'] = 'tree,form'
		return result


	def current_year_list(self):
		list = []
		query = "select  * from holidays_master where year = date_part('year', current_timestamp) and company_id=%s" % (
			self.env.user.company_id.id)
		self.env.cr.execute(query)
		data = self.env.cr.dictfetchall()
		if data:
			for item in data:
				list.append(item['id'])
		action = self.env.ref('hr_holidays_ext.public_holidays_action_view')
		result = action.read()[0]
		res = self.env.ref('hr_holidays_ext.Public_holiday_tree_view', False)
		res_form = self.env.ref('hr_holidays_ext.holiday_master_form_view', False)
		result['views'] = [(res and res.id or False, 'list'), (res_form and res_form.id or False, 'form')]
		result['domain'] = [('id', 'in', tuple(list))]
		result['target'] = 'main'
		result['view_type'] = 'tree'
		result['view_mode'] = 'tree,form'
		return result

	def next_year_list(self):
		list = []
		query = "select  * from holidays_master where year > date_part('year', current_timestamp) and company_id=%s" % (
			self.env.user.company_id.id)
		self.env.cr.execute(query)
		data = self.env.cr.dictfetchall()
		if data:
			for item in data:
				list.append(item['id'])
		action = self.env.ref('hr_holidays_ext.public_holidays_action_view')
		result = action.read()[0]
		res = self.env.ref('hr_holidays_ext.Public_holiday_tree_view', False)
		res_form = self.env.ref('hr_holidays_ext.holiday_master_form_view', False)
		result['views'] = [(res and res.id or False, 'list'), (res_form and res_form.id or False, 'form')]
		result['domain'] = [('id', 'in', tuple(list))]
		result['target'] = 'main'
		result['view_type'] = 'tree'
		result['view_mode'] = 'tree,form'
		return result
