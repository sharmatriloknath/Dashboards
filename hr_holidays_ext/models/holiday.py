from odoo import models,api,fields
import logging
import math
from datetime import timedelta,datetime
from dateutil.relativedelta import relativedelta as rd
from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools import float_compare
from odoo.tools.translate import _
from dateutil import parser

# Trilok

class Holidays(models.Model):
    _inherit = 'hr.holidays'
    '''Request application should be submitted before how many days'''



    @api.constrains('date_from')
    def _check_date_to(self):

        policy_id = self.env['leaves.policy'].search([('leave_type', '=', self.holiday_status_id.id),('company_id','=',self.env.user.company_id.id)])
        # emp_type=self.employee_id.employee_type.id
        for val in policy_id:
            # if val.employee_type.id==emp_type:
            for holiday in self:
                if holiday.type == 'remove':
                    today = datetime.today()
                    date_from = parser.parse(holiday.date_from)
                    if date_from<today:
                        raise ValidationError("Leave request for past date is not possible")
                    days = (date_from - today).days
                    # print("isudbgkibfsion", days)
                    if val.leave_app_advance_sub > 0 and days < val.leave_app_advance_sub:
                        raise ValidationError(
                            _('Leave application should be submitted before {} days!'.format(val.leave_app_advance_sub)))

    '''this fuction check the minimum number of days required for requesting for leave request'''

    @api.constrains('number_of_days_temp')
    def _check_number_of_days_temp(self):
        if self.type=='remove':
            policy_id = self.env['leaves.policy'].search([('leave_type', '=', self.holiday_status_id.id) ,('company_id','=',self.env.user.company_id.id)])
            # emp_type = self.employee_id.employee_type.id
            for holiday in self:
                for val in policy_id:
                    # if val.employee_type.id==emp_type:
                    if holiday.number_of_days_temp < val.min_leave_avail:
                        raise ValidationError(
                            _('Minimum days for leave request should be greater or equal to {} days!'.format(
                                val.min_leave_avail)))
                    elif val.max_leave_avail > 0:
                        if holiday.number_of_days_temp > val.max_leave_avail:
                            raise ValidationError(
                                _('Maximum days for leave request should be less or equal to {} days!'.format(
                                    val.max_leave_avail)))
                    if not val.dur_half and holiday.number_of_days_temp < 1:
                        raise ValidationError("Half Day Is Not Allowed For This Leave")

    @api.multi
    def write(self, values):
        result = super(Holidays, self).write(values)
        employee_id = values.get('employee_id', False)
        # if not self._check_state_access_right(values):
        #     raise AccessError(
        #         _('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % values.get('state'))
        # result = super(Holidays, self).write(values)
        self.add_follower(employee_id)
        if 'employee_id' in values:
            self._onchange_employee_id()
        policy_id = self.env['leaves.policy'].search([('leave_type', '=', self.holiday_status_id.id),('company_id','=',self.env.user.company_id.id)])
        # print ("policy iddddddddddddddd",policy_id)
        # emp_type=self.employee_id.employee_type.id
        for val in policy_id:
            # if val.employee_type.id==emp_type:
            for employee in self.employee_id:
                if self.type == 'remove':
                    query = '''select count(*) from hr_holidays where upper(type) = upper('rEMove')
                       and upper(state) = upper('Validate')
                         and create_date::date between to_date(concat(date_part('Year',now()::date),'-01-01'),'yyyy-mm-dd') and now()::date and employee_id = %s''' % self.employee_id.id
                    self.env.cr.execute(query)
                    query_result = self.env.cr.dictfetchone()
                    print("query_result", query_result)
                    # print ("AAAAAAAAAAAAAAAAAAAAAAAAAAA",val.min_app_per_year, query_result["count"])

                    if val.min_app_per_year > 0 and query_result["count"] > val.min_app_per_year:
                        raise ValidationError(
                            "maximum number of applications per year is {} days".format(val.min_app_per_year))

                    query1 = '''select create_date::date,date_to::date from hr_holidays where upper(type) = upper('rEMove')
                 and upper(state) = upper('Validate')
                and create_date::date between to_date(concat(date_part('Year',now()::date),'-01-01'),'yyyy-mm-dd') and now()::date and employee_id = %s order by create_date desc limit 1'''% self.employee_id.id
                    self.env.cr.execute(query1)
                    query_result1 = self.env.cr.fetchall()
                    if query_result1:
                        cre_date = datetime.strptime(query_result1[0][0], '%Y-%m-%d')
                        date_to = datetime.strptime(query_result1[0][1], '%Y-%m-%d')
                        print("cre_date", cre_date, type(cre_date))
                        current_dt = fields.Datetime.now()
                        # cdate=datetime.strptime(current_dt,'%Y-%m-%d')
                        current_date = datetime.strptime(current_dt.split(" ")[0], '%Y-%m-%d')
                        days = (current_date - date_to).days
                        if val.min_leave_app_gap > 0 and days > val.min_leave_app_gap:
                            raise ValidationError("Minimum gap between two application should be atleast {} days".format(
                                val.min_leave_app_gap))

        return result

    # @api.onchange('date_from')
    # def _onchange_date_from(self):
    #     """ If there are no date set for date_to, automatically set one 8 hours later than
    #         the date_from. Also update the number_of_days.
    #     """
    #     date_from = self.date_from
    #     date_to = self.date_to
    #     policy_id = self.env['leaves.policy'].sudo().search([('leave_type', '=', self.holiday_status_id.id),
    #     ('company_id', '=',self.env.user.company_id.id)])
    #     if date_from and not date_to:
    #         date_to_with_delta = fields.Datetime.from_string(date_from) + timedelta(hours=8)
    #         self.date_to = str(date_to_with_delta)
    #
    #     # Compute and update the number of days
    #     if (date_to and date_from) and (date_from <= date_to):
    #         for val in policy_id:
    #             if val.weekends_leave_period == 'dont_count':
    #                 self.number_of_days_temp = self._get_number_of_days(date_from, date_to, self.employee_id.id)
    #             else:
    #                 date_to1 = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
    #                 date_from1 = datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
    #                 if val.dur_full:
    #                     total_days = (date_to1 - date_from1).days
    #                 else:
    #                     total_seconds = (date_to1 - date_from1).seconds
    #                     total_days = total_seconds/(24*3600)
    #
    #                 week_offs = total_days - self.number_of_days_temp
    #                 self.number_of_days_temp = self.number_of_days_temp + week_offs
    #                 print("the inside ifpppppppppppppppppppppppp",self.number_of_days_temp)
    #         print("outside  mmmmmmmmmmmmmmmmmmmmmmmmmmmmmm",self.number_of_days_temp)
    #     else:
    #         self.number_of_days_temp = 0

    # @api.onchange('date_from', 'date_to')
    # def _onchange_date_from1(self):
    #     """ If there are no date set for date_to, automatically set one 8 hours later than
    #         the date_from. Also update the number_of_days.
    #     """
    #     description = self.name
    #     date_from = self.date_from
    #     date_to = self.date_to
    #     policy_id = self.env['leaves.policy'].sudo().search(
    #         [('leave_type', '=', self.holiday_status_id.id), ('company_id', '=', self.env.user.company_id.id)])
    #     if date_from and not date_to:
    #         date_to_with_delta = fields.Datetime.from_string(date_from) + timedelta(hours=8)
    #         self.date_to = str(date_to_with_delta)
    #
    #     # Compute and update the number of days
    #     if (date_to and date_from) and (date_from <= date_to):
    #         for val in policy_id:
    #             number_of_days = 0
    #             if val.weekends_leave_period == 'dont_count':
    #                 self.number_of_days_temp = self._get_number_of_days(date_from, date_to, self.employee_id.id)
    #             else:
    #                 number_of_days = self._get_number_of_days(date_from, date_to, self.employee_id.id)
    #                 date_to1 = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
    #                 date_from1 = datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
    #                 if val.dur_full:
    #                     total_days = (date_to1 - date_from1).days
    #                 else:
    #                     total_seconds = (date_to1 - date_from1).seconds
    #                     total_days = total_seconds / (24 * 3600)
    #
    #                 week_offs = total_days - number_of_days
    #                 self.number_of_days_temp = number_of_days + week_offs
    #             print("the inside ifpppppppppppppppppppppppp", self,val,self.number_of_days_temp)
    #         print("outside  mmmmmmmmmmmmmmmmmmmmmmmmmmmmmm", self.number_of_days_temp)
    #     else:
    #         self.number_of_days_temp = 0
    #     date_from1 = self.date_from
    #     date_to1 = self.date_to
    #     print("lastttttttttt  mmmmmmmmmmmmmmmmmmmmmmmmmmmmmm",self, self.number_of_days_temp)




