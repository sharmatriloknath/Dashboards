from datetime import datetime
import datetime
import math
from datetime import timedelta
from odoo import models, fields, api, exceptions, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import pytz
from time import tzname
from pytz import timezone

class HrAttendance(models.Model):
    _inherit = "hr.attendance"
    _description = "Attendance"

    # company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id)
    late_coming=fields.Selection([('no','No'),('yes','Yes')],default='no')
    departure_early=fields.Selection([('no','No'),('yes','Yes')],default='no')
    employee_day_status=fields.Selection([('present','Present'),('absent','Absent')])
    half_day_status = fields.Boolean(string='Half Day')
    la_day_status = fields.Boolean(string='Late Arrival')
    ed_day_status = fields.Boolean(string='Early Departure')
    ot_day_status = fields.Boolean(string='Over Time')
    emp_code=fields.Char(string="Employee Code")
    # half_day_status = fields.Boolean(string='half day')
    # employee_day_status=fields.Selection([('present','Present'),('absent','Absent'),('half','Half Day'),('LA','LA'),('ED','ED'),('OT','OT')])
    add_or_deduct=fields.Float(string="Deduction")
    # detail_id = fields.Many2one("process.attendance", string="Employee Attendance Details")
    attendance_date=fields.Date(string="Attendance Date")
    in_manual=fields.Char(string="In Manual")
    out_manual=fields.Char(sring="Out Manual")
    overtime_duration=fields.Float(string='Overtime')
    single_punch = fields.Boolean(string="Sigle Punch")
    is_review=fields.Boolean(string="For Review")
    scheduler=fields.Boolean(string='Schedular',default=False)
    comment=fields.Text(string='Comment')
    policies_apply = {}

    #Class level variable for UTC format

    #The TimeZone of User
    def user_timezone(self,company_id):
        user = self.env["res.users"].search([('company_id', '=', company_id)])
        # tzn=None
        for val in user:
            timezone=val.tz
            if timezone:
                tzn=timezone
            else:
                tzn=self.env.user.tz or pytz.utc
            return tzn

    '''This function returns us the checks in UTC format for storing in database'''

    def checks_in_out_utc_format(self,check_in,check_out,company_id):

        user_timezone = self.user_timezone(company_id) #The timezone of user
        local = pytz.timezone(str(user_timezone))

        display_date_result = pytz.utc.localize(datetime.datetime.strptime(check_in, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
        display_date_result1 = pytz.utc.localize(datetime.datetime.strptime(check_out, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)

        date3 = display_date_result - datetime.datetime.strptime(check_in, DEFAULT_SERVER_DATETIME_FORMAT)
        date4 = display_date_result1 - datetime.datetime.strptime(check_out, DEFAULT_SERVER_DATETIME_FORMAT)

        check_in_utc_date = datetime.datetime.strptime(check_in, DEFAULT_SERVER_DATETIME_FORMAT) - date3
        check_out_utc_date = datetime.datetime.strptime(check_out, DEFAULT_SERVER_DATETIME_FORMAT) - date4

        return check_in_utc_date,check_out_utc_date


    '''This Function conver UTC to Local'''
    def checks_utc_to_local(self, check_in, check_out):
        user_tz = self.env.user.tz or str(pytz.utc)
        print(user_tz,":",type(user_tz))
        local = pytz.timezone(user_tz)
        print(local, ":", type(local))
        if check_in and check_out:
            display_date_result = pytz.utc.localize(datetime.datetime.strptime(check_in, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
            display_date_result1 = pytz.utc.localize(datetime.datetime.strptime(check_out, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)

            check_in_local = datetime.datetime.strftime(display_date_result, '%Y-%m-%d %H:%M:%S')
            check_out_local = datetime.datetime.strftime(display_date_result1, '%Y-%m-%d %H:%M:%S')
            return check_in_local, check_out_local

    '''This function is for schedular ..........EveryTime schedular execute it and check the condition which is defined
     inside it.....if condition is True then call another function else not.'''
    @api.multi
    def attendance_checks(self):
        print("schedular is running from the attendance to assign the checks ")

        query = 'select last_run,interval,company_id from attendance_checks where now()>next_run'
        self.env.cr.execute(query)
        data=self.env.cr.fetchall()
        print("The information in data",data)
        if data:
            for record in data:
                f_datetime = record[0]
                # next_run=record[1]
                interval= record[1]
                company_id=record[2]
                from_datetime = datetime.datetime.strptime(f_datetime, '%Y-%m-%d %H:%M:%S')
                to_datetime = from_datetime + timedelta(days=interval)
                current_date = datetime.datetime.now()
                if current_date > to_datetime:
                    runtime = datetime.datetime.now()
                    self.get_data_from_raw_punch(company_id)
                    queryupdate = "UPDATE attendance_checks SET last_run = '%s', next_run = '%s',runtime='%s' where company_id='%s'" % (to_datetime, to_datetime, runtime,company_id)
                    self.env.cr.execute(queryupdate)
                    print ("Updation Process is Successfully Done ....................................................")

    def get_list_of_companies(self):
        companies=self.env['res.company'].search([])
        print("The List Of Companies",companies)
        return companies

    '''This is the function which fetch data from database and check its company,shift,and finally call policy method.'''
    def get_data_from_raw_punch(self,company_id):
        shifts = self.shifts_list(company_id)
        if shifts:
            for shift in shifts:
                print('shieft type',shift.shift_type)
                date1 = datetime.date.today()
                date = date1.strftime('%Y-%m-%d')
                query = """select min(punch_datetime),max(punch_datetime),b.emp_punch_code from machine_raw_punch a, hr_employee b,
                                                           resource_calendar c where date(punch_datetime)='%s' and a.card_no = cast(b.emp_punch_code as integer) and b.resource_calendar_ids = '%s' group by b.emp_punch_code""" % ('2019-11-03',shift.id)
                self.env.cr.execute(query)
                all_record = self.env.cr.fetchall()
                if all_record:
                    for record in all_record:
                        emp_id = record[2]
                        objs = self.env["hr.employee"].search([('company_id', '=', company_id),('emp_punch_code','=',emp_id)])
                        policy=objs.policy_name
                        employee_id=objs.id
                        if shift.shift_type == 'same_day' and objs.resource_calendar_ids.shift_type == 'same_day' and  shift.id == objs.resource_calendar_ids.id:
                            check_in = record[0]
                            check_out = record[1]
                            emp_id = record[2]

                            hour = datetime.datetime.strptime(check_out,'%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(
                                check_in, '%Y-%m-%d %H:%M:%S')
                            worked_hours = hour.total_seconds() / 3600.0
                            punch_date=' '

                            if record[0] and record[1]:
                                d = datetime.datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                                d1 = d.date()
                                punch_date = d1.strftime('%Y-%m-%d')

                            elif record[0] and not (record[1]):
                                d = datetime.datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                                d1 = d.date()
                                punch_date = d1.strftime('%Y-%m-%d')

                            elif not (record[0]) and record[1]:
                                d = datetime.datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                                d1 = d.date()
                                punch_date = d1.strftime('%Y-%m-%d')
                            shift_start = 0.0
                            shift_end = 0.0
                            for shift_id in shift.attendance_ids:
                                shift_start = shift_id.hour_from
                                shift_end = shift_id.hour_to
                                date1 = datetime.date.today()
                                date = date1.strftime('%Y-%m-%d')

                            policies_varify = self.advance_employee_policies_details(check_in, check_out,worked_hours, emp_id,policy,company_id)
                            print("policy verification .........................",policies_varify)

                            self.same_day_check_in_date(employee_id,emp_id, check_in, check_out, shift_start, shift_end, punch_date,policies_varify, company_id,worked_hours)

                        elif shift.shift_type == 'different_days' and objs.resource_calendar_ids.shift_type == 'different_days' and shift.id == objs.resource_calendar_ids.id:
                            print('this is different day')
                            shift_start = 0.0
                            shift_end = 0.0
                            # print(a)
                            print('shift_id8888888888888888',shift.attendance_ids)
                            for shift_id in shift.attendance_ids:
                                print('shift_id1111111111111', shift_id)
                                shift_start = shift_id.hour_from
                                shift_end = shift_id.hour_to
                            punch_date = ''
                            min_check_dt = record[0]
                            max_check_dt = record[1]
                            emp_id = record[2]
                            hour = datetime.datetime.strptime(max_check_dt,'%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(min_check_dt, '%Y-%m-%d %H:%M:%S')
                            print('hour7777777', hour)
                            worked_hours = hour.total_seconds() / 3600.0
                            print("min_check_dt", min_check_dt)
                            print("max_check_dt", max_check_dt)
                            print("emp_id", emp_id)
                            if record[0] and record[1]:
                                d = datetime.datetime.strptime(min_check_dt, '%Y-%m-%d %H:%M:%S')
                                d1 = d.date()
                                punch_date = d1.strftime('%Y-%m-%d')

                            elif record[0] and not (record[1]):
                                d = datetime.datetime.strptime(min_check_dt, '%Y-%m-%d %H:%M:%S')
                                d1 = d.date()
                                punch_date = d1.strftime('%Y-%m-%d')

                            elif not (record[0]) and record[1]:
                                d = datetime.datetime.strptime(max_check_dt, '%Y-%m-%d %H:%M:%S')
                                d1 = d.date()
                                punch_date = d1.strftime('%Y-%m-%d')

                            policies_varify = self.advance_employee_policies_details(min_check_dt, max_check_dt,worked_hours, emp_id,policy,company_id)
                            print('policies_varify111', policies_varify, emp_id)
                            # print(a)
                            self.check_in_date(employee_id,emp_id, min_check_dt, max_check_dt, shift_start, shift_end,punch_date, policies_varify,company_id,policy)

    '''when same day shift employee have only one punch then to check wheather it is check_in or check_out this function verify it and store into database.'''
    def same_day_check_in_date(self,employee_id,emp_id,check_in,check_out,shift_start,shift_end,punch_date,policies_varify,company_id,worked_hours):

        #checks in UTC format
        check_in_utc,check_out_utc=self.checks_in_out_utc_format(check_in,check_out,company_id)
        if check_in != check_out:
            date_today = datetime.date.today()
            date_today_string = date_today.strftime('%Y-%m-%d')
            exist_check = """select count(*) from hr_attendance where emp_code='%s' and attendance_date='%s' and company_id='%s' """ % (emp_id,punch_date, company_id)
            self.env.cr.execute(exist_check)
            record = self.env.cr.fetchall()
            print("The values in record11111", record)
            if record[0][0]>0:
                # update_line = """update hr_attendance set check_out = '%s' where  employee_id = '%s' and attendance_date = '%s' """ % (check_out, emp_id, punch_date)
                update_line = """update hr_attendance set check_out = '%s' where  emp_code = '%s' and attendance_date = '%s' """ % (check_out_utc, emp_id, punch_date)
                self.env.cr.execute(update_line)
                print("record updated")
                return 'record_updated'
            else:
                if policies_varify:
                    policies_varify.update(
                        {'employee_id':employee_id,'emp_code': emp_id, 'check_in': check_in_utc, 'check_out': check_out_utc,
                         'worked_hours': worked_hours, 'attendance_date': punch_date, 'scheduler': True})
                    print("final dics", policies_varify)
                    # print(a)
                    self.env['hr.attendance'].create(policies_varify)
                    print("insertion is successful")

        else:
            check_in = datetime.datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
            max_time = float(str(check_in.hour) + '.' + str(check_in.minute))
            near_to_shift_start = abs(max_time - shift_start)
            near_to_shift_end = abs(max_time - shift_end)
            check_in_str = datetime.datetime.strftime(check_in,'%Y-%m-%d %H:%M:%S')

            print('check_in', check_in)
            print('max_time hours form time of check', max_time)
            print('near_to_shift_start', near_to_shift_start)
            print('near_to_shift_end', near_to_shift_end)

            if near_to_shift_start < near_to_shift_end:
                print('this is start')
                exist_check = """select count(*) from hr_attendance where emp_code='%s' and attendance_date='%s' and company_id='%s' """ % (emp_id,punch_date,company_id)
                self.env.cr.execute(exist_check)
                record = self.env.cr.fetchall()
                print("The values in record11111", record)
                if record[0][0] > 0:
                    # update_line = """update hr_attendance set check_out = '%s' where  employee_id = '%s' and attendance_date = '%s' """ % (check_out, emp_id, punch_date)
                    update_line = """update hr_attendance set check_in = '%s' where  emp_code = '%s' and attendance_date = '%s' """ % (check_in_utc, emp_id, punch_date)
                    print("record updated")
                    self.env.cr.execute(update_line)
                    return 'record_updated'

                else:
                    date1 = datetime.datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
                    date2 = date1.date()
                    date3 = date2.strftime(('%Y-%m-%d'))
                    date4 = date3 + ' ' + str(math.ceil(shift_end)) + ':00:00'
                    user_timezone = self.user_timezone(company_id)  # The timezone of user
                    local = pytz.timezone(user_timezone)
                    display_date_result = pytz.utc.localize(
                        datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
                    date_local = display_date_result - datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)
                    shift_near_time_date = datetime.datetime.strptime(date4,DEFAULT_SERVER_DATETIME_FORMAT) - date_local
                    print('date4', date4)

                    if policies_varify:
                        policies_varify.update({'employee_id': employee_id,
                                                'emp_code':emp_id,
                                                'check_in': check_in_utc,
                                                # 'check_out': date4,
                                                # 'check_out': check_out,
                                                'check_out': shift_near_time_date,
                                                'worked_hours': worked_hours,
                                                'attendance_date': punch_date,
                                                'out_manual': 'Out Manual',
                                                'is_review': True,
                                                'scheduler': True})
                        print("final dics3 same day", policies_varify)
                        # print(a)
                        self.env['hr.attendance'].create(policies_varify)
                        print("record_created successfully............................")
                        return 'record_created'
            else:
                print("this is new")
                nearest_shift_end = self.same_day_check_out_date(employee_id,emp_id, check_in_str, check_out, punch_date, shift_start,shift_end, policies_varify,company_id,worked_hours)
                return nearest_shift_end

    '''same day shift function for check_out.'''
    def same_day_check_out_date(self,employee_id,emp_id, check_in, check_out, punch_date, shift_start,shift_end, policies_varify,company_id,worked_hours):
        # checks in UTC format
        check_in_utc, check_out_utc = self.checks_in_out_utc_format(check_in, check_out, company_id)
        # print("The data in UTC format2", check_in_utc, check_out_utc)
        # print("The data in Original form2", check_in, check_out)
        # print(a)

        exist_check = """select count(*) from hr_attendance where emp_code='%s' and attendance_date='%s' and company_id='%s' """ % (emp_id,punch_date,company_id)
        self.env.cr.execute(exist_check)
        record = self.env.cr.fetchall()
        print('record1111111',record)
        if record[0][0]>0:
            # update_line = """update hr_attendance set check_in = '%s'  where  employee_id = '%s' and attendance_date = '%s' """ % (check_in, emp_id, punch_date)
            update_line = """update hr_attendance set check_out = '%s'  where  emp_code = '%s' and attendance_date = '%s' """ % (check_out_utc, emp_id, punch_date)
            self.env.cr.execute(update_line)
            print ("record updated check out data of same days...........................................................")
            return 'record_updated'

        else:
            # check_in_string = datetime.datetime.strftime(check_in, '%Y-%m-%d %H:%M:%S')
            date1 = datetime.datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
            date2=date1.date()
            date3 = date2.strftime(('%Y-%m-%d'))
            date4 = date3+' '+ str(math.ceil(shift_start))+':00:00'
            user_timezone = self.user_timezone(company_id)  # The timezone of user
            local = pytz.timezone(user_timezone)
            display_date_result = pytz.utc.localize(
                datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
            date_local = display_date_result - datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)
            shift_near_time_date = datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT) - date_local
            print('date4',date4)
            if policies_varify:
                policies_varify.update({'employee_id': employee_id,
                                        'emp_code':emp_id,
                                        'check_in': shift_near_time_date,
                                        # 'check_out': check_out,
                                        'check_out': check_out_utc,
                                        'worked_hours': worked_hours,
                                        'attendance_date': punch_date,
                                        'in_manual': 'In Manual',
                                        'is_review':True,
                                        'scheduler':True})
                print("final dictionay of same day check_out", policies_varify)

                self.env['hr.attendance'].create(policies_varify)
            print ("record created check out data of the same dayssssssssssssssssssssssssssss")

            print("record_created")
            return 'record_created'

    '''employee have  across the day punches then this function get executes.'''
    def check_in_date(self,employee_id,emp_id, min_check_dt, max_check_dt, shift_start, shift_end, punch_date, policies_varify,company_id,policy):
        # checks in UTC format
        check_in_utc, check_out_utc = self.checks_in_out_utc_format(min_check_dt, max_check_dt, company_id)
        hour = datetime.datetime.strptime(max_check_dt, '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(min_check_dt, '%Y-%m-%d %H:%M:%S')
        worked_hours = hour.total_seconds() / 3600.0

        # Trilok changes 2019-11-07

        date1 = datetime.datetime.strptime(min_check_dt, '%Y-%m-%d %H:%M:%S')
        manual_date = date1+relativedelta(days=1)
        date2 = manual_date.date()
        date3 = date2.strftime(('%Y-%m-%d'))
        date4 = date3 + ' ' + str(math.ceil(shift_end)) + ':00:00'
        user_timezone = self.user_timezone(company_id)  # The timezone of user
        local = pytz.timezone(user_timezone)
        display_date_result = pytz.utc.localize(
            datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
        date_local = display_date_result - datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)
        shift_near_time_date = datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT) - date_local
        # Trilok End

        if min_check_dt != max_check_dt:

            date_today = datetime.date.today()
            date_today_string = date_today.strftime('%Y-%m-%d')
            exist_check = """select count(*) from hr_attendance where emp_code='%s' and attendance_date='%s' and company_id='%s' """ % (emp_id,punch_date, company_id)
            self.env.cr.execute(exist_check)
            record = self.env.cr.fetchall()
            print("The values in record11111", record)
            if record[0][0]>0:
                update_line = """update hr_attendance set check_in = '%s' where  emp_code = '%s' and attendance_date = '%s' """ % (check_out_utc, emp_id, punch_date)
                self.env.cr.execute(update_line)
                print("record updated")
                return 'record_updated'

            else:
                date2 = datetime.datetime.strptime(punch_date, '%Y-%m-%d')
                date12 = date2 - relativedelta(days=1)
                punch_date2 = date12.strftime('%Y-%m-%d')

                if policies_varify:
                    print('gghhhhhhhc',company_id,emp_id,punch_date2)
                    employees_find = self.env['hr.attendance'].search([('company_id', '=', company_id),('emp_code','=',emp_id),('attendance_date','=',punch_date2)])

                    if employees_find:
                        employees_find.write({'check_out': check_in_utc})
                        employees_find2 = self.env['hr.attendance'].search([('company_id', '=', company_id), ('emp_code', '=', emp_id),('attendance_date', '=', punch_date2)])
                        details_list = []
                        if employees_find2:
                            details_list.append(employees_find2.check_in)
                            details_list.append(employees_find2.check_out)
                            hour = datetime.datetime.strptime(details_list[1],'%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(details_list[0], '%Y-%m-%d %H:%M:%S')
                            print('hour7777777', hour)
                            print("the details_list[0]",details_list)

                            # Here we need to convert the Fetched check_in check_out into local timezone for that we need to call a function
                            check_in,check_out=self.checks_utc_to_local(details_list[0], details_list[1])
                            print("the local format datetime is",check_in,check_out)
                            worked_hours = hour.total_seconds() / 3600.0
                            print('worked_hours888', worked_hours)
                            policies_varify2 = self.advance_employee_policies_details(check_in, check_out, worked_hours, emp_id, policy, company_id)

                            policies_varify2.update({'worked_hours': worked_hours})
                            print("the data in policies varify22222222222222222222",policies_varify2)
                            if 'overtime_duration' not in policies_varify2 and 'ot_day_status' not in policies_varify2:
                                policies_varify2.update({'overtime_duration': 0.0, 'ot_day_status': False})
                            if 'late_coming' not in policies_varify2:
                                policies_varify2.update({'late_coming':'no'})
                            if 'departure_early' not in policies_varify2:
                                policies_varify2.update({'departure_early': 'no'})
                            if 'ed_day_status' not in policies_varify2:
                                policies_varify2.update({'ed_day_status': False})
                            if 'la_day_status' not in policies_varify2:
                                policies_varify2.update({'la_day_status': False})
                            if 'half_day_status' not in policies_varify2:
                                policies_varify2.update({'half_day_status':False})
                            if 'add_or_deduct' not in policies_varify2:
                                policies_varify2.update({'add_or_deduct':None})
                            print("the data in policies varify22222222222222222222***********",policies_varify2)
                            policies_varify2.update({'out_manual': '','is_review': False})
                            print("the data in policies varify22222222222222222222***********22222222222", policies_varify2)
                            employees_find2.write(policies_varify2)
                            # print(a)
                    # policies_varify.update({'employee_id': employee_id,'emp_code':emp_id, 'check_in': check_out_utc,
                    #                         'worked_hours': worked_hours, 'attendance_date': punch_date,
                    #                         'scheduler': True})
                    policies_varify.update({'employee_id': employee_id, 'emp_code': emp_id, 'check_in': check_out_utc,
                                            'worked_hours': worked_hours, 'attendance_date': punch_date,'check_out':shift_near_time_date,'out_manual':'Out Manual','is_review':True,
                                            'scheduler': True})
                    print("the policies_varify************",policies_varify)
                    self.env['hr.attendance'].create(policies_varify)
                print("record_created")
                return 'record_created'

        else:
            check_in=datetime.datetime.strptime(max_check_dt, '%Y-%m-%d %H:%M:%S')
            max_time = float(str(check_in.hour) + '.' + str(check_in.minute))
            near_to_shift_start = abs(max_time-shift_start)
            near_to_shift_end = abs(max_time-shift_end)
            date = datetime.datetime.strptime(punch_date, '%Y-%m-%d')
            date1 = date - relativedelta(days=1)
            punch_date1 = date1.strftime('%Y-%m-%d')



            print('check_in-------',check_in)
            print('max_time-------',max_time)
            print('near_to_shift_start-------',near_to_shift_start)
            print('near_to_shift_end-------',near_to_shift_end)

            if near_to_shift_start < near_to_shift_end:

                print('this is start')
                exist_check = """select count(*) from hr_attendance where emp_code='%s' and attendance_date='%s' and company_id='%s' """ % (emp_id,punch_date1,company_id)
                self.env.cr.execute(exist_check)
                record = self.env.cr.fetchall()
                print("The values in record11111", record)
                date1 = datetime.datetime.strptime(max_check_dt, '%Y-%m-%d %H:%M:%S')
                date2 = date1.date()
                date3 = date2.strftime(('%Y-%m-%d'))
                date4 = date3 + ' ' + str(math.ceil(shift_end)) + ':00:00'
                user_timezone = self.user_timezone(company_id)  # The timezone of user
                local = pytz.timezone(user_timezone)
                display_date_result = pytz.utc.localize(datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
                date_local = display_date_result - datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)
                shift_near_time_date = datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT) - date_local
                print('date4', date4)
                if record[0][0] > 0:
                    # update_line = """update hr_attendance set check_out = '%s' where  employee_id = '%s' and attendance_date = '%s' """ % (min_check_dt, emp_id, punch_date)
                    # update_line = """update hr_attendance set check_in = '%s' where  emp_code = '%s' and attendance_date = '%s' """ % (check_in_utc, emp_id, punch_date)
                    update_line = """update hr_attendance set check_out = '%s', is_review= %s,out_manual='%s'  where  emp_code = '%s' and attendance_date = '%s' """ % (shift_near_time_date,True,'Out Manual',emp_id, punch_date1)

                    print("record updated")
                    self.env.cr.execute(update_line)
                    return 'record_updated'

                else:
                    # date1 = datetime.datetime.strptime(max_check_dt, '%Y-%m-%d %H:%M:%S')
                    # date2 = date1.date()
                    # date3 = date2.strftime(('%Y-%m-%d'))
                    # date4 = date3 + ' ' + str(math.ceil(shift_end)) + ':00:00'
                    # user_timezone = self.user_timezone(company_id)  # The timezone of user
                    # local = pytz.timezone(user_timezone)
                    # display_date_result = pytz.utc.localize(datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
                    # date_local = display_date_result - datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)
                    # shift_near_time_date = datetime.datetime.strptime(date4,DEFAULT_SERVER_DATETIME_FORMAT) - date_local
                    # print('date4', date4)
                    # print("punch_dateeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",punch_date)
                    date1 = datetime.datetime.strptime(max_check_dt, '%Y-%m-%d %H:%M:%S')
                    date2 = date1.date()
                    date3 = date2.strftime(('%Y-%m-%d'))
                    date4 = date3 + ' ' + str(math.ceil(shift_end)) + ':00:00'
                    print('date4', date4)
                    print("punch_dateeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",punch_date)

                    # insert_line = """insert into hr_attendance (employee_id,check_in,attendance_date,check_out,out_manual,worked_hours) values('%s','%s','%s','%s','%s',%s)""" % (emp_id,max_check_dt, punch_date,date4,'Out Manual',worked_hours)
                    # self.env.cr.execute(insert_line)
                    if policies_varify:
                        policies_varify.update({'employee_id': employee_id,
                                                'emp_code':emp_id,
                                                # 'check_in': max_check_dt,
                                                'check_in':check_out_utc,
                                                # 'check_out': date4,
                                                # 'check_out': max_check_dt,
                                                # 'check_out': shift_near_time_date,
                                                'worked_hours': worked_hours,
                                                'attendance_date': punch_date,
                                                # 'out_manual': 'Out Manual',
                                                # 'is_review': True,
                                                'scheduler':True})
                        print("final dics3", policies_varify)
                        # print(a)
                        self.env['hr.attendance'].create(policies_varify)
                        print("record_created55555555555555555555555")

                        return 'record_created'
                    # return 'record_created'


            else:
                print("this is new")
                nearest_shift_end =  self.check_out_date(employee_id,emp_id, min_check_dt, max_check_dt, punch_date,shift_start,shift_end,policies_varify,company_id)
                return nearest_shift_end
    #sam
    def check_out_date(self,employee_id,emp_id, min_check_dt, max_check_dt,punch_date,shift_start,shift_end,policies_varify,company_id):

        # checks in UTC format
        print('min_check_dt',min_check_dt,type(min_check_dt))
        print('max_check_dt',max_check_dt,type(max_check_dt))
        check_in_utc, check_out_utc = self.checks_in_out_utc_format(min_check_dt, max_check_dt, company_id)
        # print("The data in UTC format4", check_in_utc, check_out_utc)
        # print("The data in Original form4", check_in, check_out)
        # print(a)

        date=datetime.datetime.strptime(punch_date,'%Y-%m-%d')
        date1=date-relativedelta(days=1)
        punch_date=date1.strftime('%Y-%m-%d')
        hour = datetime.datetime.strptime(max_check_dt, '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(min_check_dt,'%Y-%m-%d %H:%M:%S')
        worked_hours = hour.total_seconds() / 3600.0

        print ('punch_date1111111111',punch_date)

        exist_check = """select count(*) from hr_attendance where emp_code='%s' and attendance_date='%s' and company_id='%s' """ % (emp_id,punch_date,company_id)
        self.env.cr.execute(exist_check)
        record = self.env.cr.fetchall()
        print('record1111111',record)
        if record[0][0]>0:
            # update_line = """update hr_attendance set check_out = '%s'  where  employee_id = '%s' and attendance_date = '%s' """ % (min_check_dt, emp_id, punch_date)
            update_line = """update hr_attendance set check_out = '%s'  where  emp_code = '%s' and attendance_date = '%s' """ % (check_in_utc, emp_id, punch_date)
            self.env.cr.execute(update_line)
            print ("record updated check out data")
            return 'record_updated'

        else:
            date1 = datetime.datetime.strptime(min_check_dt, '%Y-%m-%d %H:%M:%S')
            date = date1 - relativedelta(days=1)
            date2=date.date()
            date3 = date2.strftime(('%Y-%m-%d'))
            date4 = date3+' '+ str(math.ceil(shift_start))+':00:00'
            '''Convert date4 into UTC format'''

            user_timezone = self.user_timezone(company_id)  # The timezone of user
            local = pytz.timezone(user_timezone)
            display_date_result = pytz.utc.localize(datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
            date_local = display_date_result - datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT)
            shift_near_time_date = datetime.datetime.strptime(date4, DEFAULT_SERVER_DATETIME_FORMAT) - date_local
            print('date4',date4)
            if policies_varify:
                policies_varify.update({'employee_id': employee_id,
                                        'emp_code':emp_id,
                                        'check_in': shift_near_time_date,
                                        # 'check_out': min_check_dt,
                                        'check_out': check_in_utc,
                                        'worked_hours': worked_hours,
                                        'attendance_date': punch_date,
                                        'in_manual': 'In Manual',
                                        'is_review':True,
                                        'scheduler':True})
                print("final dics4", policies_varify)
                # print(a)

                self.env['hr.attendance'].create(policies_varify)
            print ("record created check out data")

            print("record_created")
            return 'record_created'

    # This Function Returns the List of all employees that are working in same company
    def current_company_employee(self):
        employees = self.env['hr.employee'].search([('company_id', '=', self.env.user.company_id.id)])
        return employees

    # This function return the list of all available shifts
    def shifts_list(self,company_id):
        shifts=self.env['resource.calendar'].search([('company_id','=',company_id)])
        print("The corresponding shifts are:",shifts)
        return shifts

    # This Function return the list of attendance policies
    def attendance_policies_list(self):
        print("policies function extraction")
        policy_list=self.env['employee.policies.list'].search([('company_id','=',self.env.user.company_id.id)])
        return policy_list

    def advance_employee_policies_details(self,check_in,check_out,worked_hours,emp_id,policy,company_id):
        check_in = datetime.datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
        check_in_time=float(check_in.time().strftime('%H.%M'))

        check_out = datetime.datetime.strptime(check_out,'%Y-%m-%d %H:%M:%S')
        check_out_time=float(check_out.time().strftime('%H.%M'))

        shifts = self.shifts_list(company_id)
        # Changes 6-11-19 trilok line 737 and 741 added
        objs = self.env["hr.employee"].search([('company_id', '=', company_id), ('emp_punch_code', '=', emp_id)])
        if shifts:
            policies_apply = {}
            for shift_record in shifts:
                if shift_record.id == objs.resource_calendar_ids.id:
                    for shift in shift_record.attendance_ids:
                        # print('policy.per_late_arrival',policy.per_late_arrival)
                        # print('shift.hour_from',shift.hour_from)
                        # print('check_in_time',check_in_time,check_out_time)
                        # print("worked_hours",worked_hours)
                        # print('late_arrival',policy.late_arrival)
                        # print('early departure', policy.early_departure)
                        # print("departure early",policy.per_early_departure)
                        # print("shift_to",shift.hour_to)

                        # print (a)

                        if policy.per_late_arrival > 0 and check_in_time-shift.hour_from > policy.per_late_arrival:
                            policies_apply.update({'late_coming': 'yes'})

                        if policy.per_early_departure>0 and shift.hour_to-check_out_time>policy.per_early_departure:
                            policies_apply.update({'departure_early': 'yes'})

                        if policy.late_arrival>0 and check_in_time-shift.hour_from>policy.late_arrival:
                            print('policy.show_late_arrival',policy.show_late_arrival)
                            if policy.show_late_arrival=='none':
                               policies_apply.update({'la_day_status': True})

                               # self.enable_setting(policy)  #Add all functionalities in this function when show late arrival in none (Pending)
                               enable_setting_val = self.enable_setting(policy,emp_id)
                               print('enable_setting_val',enable_setting_val)
                               if enable_setting_val:
                                   policies_apply.update({'add_or_deduct': enable_setting_val})

                            elif policy.show_late_arrival=='cut_full_day':
                                policies_apply.update({'la_day_status': True,'add_or_deduct': -1})

                            elif policy.show_late_arrival == 'cut_half_day':
                                policies_apply.update({'la_day_status': True, 'add_or_deduct': -0.5})

                        if policy.early_departure > 0 and shift.hour_to - check_out_time > policy.early_departure:
                            if policy.show_early_departure == 'none':
                                policies_apply.update({'ed_day_status': True})

                                enable_setting_val = self.enable_setting(policy,emp_id)
                                if enable_setting_val:
                                    policies_apply.update({'add_or_deduct': enable_setting_val})

                            elif policy.show_early_departure == 'cut_full_day':
                                policies_apply.update({'ed_day_status': True, 'add_or_deduct': -1})

                            elif policy.show_early_departure == 'cut_half_day':
                                policies_apply.update({'ed_day_status': True, 'add_or_deduct': -0.5})

                        if check_out_time-shift.hour_to>policy.ignore_ot:
                            ot=check_out_time-shift.hour_to
                            policies_apply.update({'ot_day_status':True,'overtime_duration':ot})

                        if policy.max_hours>0 and policy.working_hrs_for_absent>0 and worked_hours<=policy.max_hours and worked_hours>policy.working_hrs_for_absent:
                            policies_apply.update({'half_day_status': True})

                        if policy.working_hrs_for_absent>0 and worked_hours<=policy.working_hrs_for_absent:
                            policies_apply.update({'employee_day_status': 'absent', 'single_punch': True})

                        elif policy.working_hrs_for_present>0 and policy.max_hours>0 and worked_hours >= policy.working_hrs_for_present and worked_hours > policy.max_hours:
                            policies_apply.update({'employee_day_status': 'present'})
                        else:
                            policies_apply.update({'employee_day_status': 'present'})
                        return policies_apply

    def enable_setting(self,policy,emp_id):
        if policy.show_late_arrival=='none':
            if policy.enable_setting:
                query="""select count(*) from hr_attendance WHERE check_in BETWEEN date(to_char(NOW(),'YYYY-MM-01')) and date(Now() + interval '1 day') and employee_id = '%s' and la_day_status = True"""%(emp_id)
                self.env.cr.execute(query)
                count=self.env.cr.fetchone()
                if policy.month_late < count[0]:
                    if policy.cut_days_or_leave == 'days' and policy.cut_days == 'half':
                         return -0.5
                    else:
                        return -1

    @api.model
    def create(self, vals):
        if 'scheduler' in vals and not vals['scheduler']:

            if 'employee_id' in vals and vals.get('employee_id') and 'check_in' in vals and vals.get('check_in') and 'check_out' in vals and vals.get('check_out'):
                check_in_date=vals.get('check_in')
                check_out_date=vals.get('check_out')
                check_in,check_out=self.checks_utc_to_local(check_in_date,check_out_date)

                attendance_date=vals.get('attendance_date')
                employee_id=vals.get('employee_id')
                company_id=vals.get('company_id')
                empl_id = self.env["hr.employee"].search([('company_id', '=', company_id), ('id', '=', employee_id)])
                emp_id = empl_id.emp_punch_code
                delta = datetime.datetime.strptime(check_out,'%Y-%m-%d %H:%M:%S')-datetime.datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
                worked_hours = delta.total_seconds() / 3600.0

                policies_dict=self.manual_attendance_fun(check_in,check_out,attendance_date,emp_id,company_id,worked_hours) #calling to manual func

                policies_dict.update(
                    {
                        'employee_id':employee_id,
                        'emp_code':emp_id,
                        'check_in':vals.get('check_in'),
                        'check_out':vals.get('check_out'),
                        'in_manual':vals.get('in_manual'),
                        'out_manual':vals.get('out_manual'),
                        'attendance_date':attendance_date,
                        'company_id':company_id,
                        'worked_hours':worked_hours

                    })
                res = super(HrAttendance, self).create(policies_dict)
                return res
            else:
                ''' When only one check is available '''
                company_id=vals.get('company_id')
                employee_id=vals.get('employee_id')
                empl_id = self.env["hr.employee"].search([('company_id', '=', company_id), ('id', '=', employee_id)])
                emp_id = empl_id.emp_punch_code
                vals.update({'emp_code':emp_id,'is_review':True})
                res = super(HrAttendance, self).create(vals)
                return res
        else :
            res = super(HrAttendance, self).create(vals)
            return res


    @api.multi
    def write(self, vals):
        if 'check_out' in vals and vals['check_out'] and 'check_in' not in vals:
            self.hr_manual_attendance_customization()
        print("the values in the dictionary------------------",self,vals)
        res = super(HrAttendance, self).write(vals)
        emp_id=vals.get('employee_id',False)
        comp_id=self.company_id
        if emp_id:
            employee=self.env['hr.employee'].search([('id','=',emp_id),('company_id','=',comp_id.id)])
            emp_code=employee.emp_punch_code
            self.emp_code = emp_code
            if self.is_review:
                self.is_review=False
        return res

    @api.onchange('check_in')
    def compute_attendance(self):
        check_in=self.check_in
        if check_in:
            date=datetime.datetime.strptime(check_in, DEFAULT_SERVER_DATETIME_FORMAT)
            attendance_date=date.date()
            self.attendance_date=attendance_date
            self.in_manual='In Manual'
        print("the manual in",self.in_manual)

    @api.onchange('check_out')
    def compute_out_is_manual_or_not(self):
        check_out=self.check_out
        if check_out:
            self.out_manual='Out Manual'

    @api.onchange('check_in','check_out')
    def hr_manual_attendance_customization(self):
        check_in=self.check_in
        check_out=self.check_out
        company_id=self.company_id.id

        emp_id=self.employee_id.id
        worked_hours=self.worked_hours
        punch_date=self.attendance_date
        empl_id = self.env["hr.employee"].search([('company_id', '=', company_id), ('id', '=', emp_id)])

        policy = empl_id.policy_name
        emp_code = empl_id.emp_punch_code

        if check_in and check_out:
            check_in_local,check_out_local=self.checks_utc_to_local(check_in,check_out) #Call to convert check_in and Check_out in Local format
            policies=self.advance_employee_policies_details(check_in_local, check_out_local, worked_hours, emp_code, policy, company_id)
            print("The required policies are:",policies)

            self.employee_day_status = policies.get('employee_day_status',False)
            self.late_coming=policies.get('late_coming',False)
            self.departure_early=policies.get('departure_early',False)
            self.overtime_duration=policies.get('overtime_duration',False)
            # self.in_manual=policies.get('in_manual',False)
            # self.out_manual=policies.get('out_manual',False)
            self.ot_day_status=policies.get('ot_day_status',False)
            self.la_day_status=policies.get('la_day_status',False)
            self.ed_day_status=policies.get('ed_day_status',False)
            self.half_day_status=policies.get('half_day_status',False)
            self.add_or_deduct=policies.get('add_or_deduct',False)

            review=self.is_review
            if review:
                self.is_review=False

    def manual_attendance_fun(self,check_in,check_out,punch_date,emp_id,company_id,worked_hours):
        shifts = self.shifts_list(company_id)
        if shifts:
            for shift in shifts:
                # print('shieft type', shift.shift_type)
                print ('emp_type is:',type(emp_id))
                empl_id = self.env["hr.employee"].search([('company_id', '=', company_id), ('emp_punch_code', '=', emp_id)])
                if shift.id == empl_id.resource_calendar_ids.id:
                    print("employees", empl_id)
                    print ("The corresponding employee_code is",empl_id.emp_punch_code)
                    policy = empl_id.policy_name
                    policies_varify = self.advance_employee_policies_details(check_in, check_out, worked_hours, emp_id,policy, company_id)
                    return policies_varify

    def hr_attendance_customization_fun_customize(self):

        view = self.env.ref('hr_attendance_ext.attendance_customization_ext_form')
        return {
            'name': _('Attendance Details'),
            'type': 'ir.actions.act_window',
            # 'domain': [('id', 'in', tuple(res))],
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.attendance',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': self.id,

        }

    def hr_attendance_customization_fun_ok(self):

        view = self.env.ref('hr_attendance_ext.attendance_customization_ext_form')
        return {
            'name': _('Attendance Details'),
            'type': 'ir.actions.act_window',
            # 'domain': [('id', 'in', tuple(res))],
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.attendance',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': self.id,

        }

    # def delta_method_for_checks_and_shifts(self):
    #     check_in = datetime.datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
    #     max_time = float(str(check_in.hour) + '.' + str(check_in.minute))
    #     near_to_shift_start = abs(max_time - shift_start)
    #     near_to_shift_end = abs(max_time - shift_end)
    #
    #     print('check_in', check_in)
    #     print('max_time hours form time of check', max_time)
    #     print('near_to_shift_start', near_to_shift_start)
    #     print('near_to_shift_end', near_to_shift_end)
    #
    #     if near_to_shift_start > near_to_shift_end:
    #         print('this is start')
    #         exist_check = """select count(*) from hr_attendance where employee_id ='%s'
    #         and (check_in = '%s' or check_out = '%s') and attendance_date ='%s'""" % (
    #             emp_id, check_in, check_out, punch_date)
    #         self.env.cr.execute(exist_check)
    #         record = self.env.cr.fetchall()
    #         print("The values in record11111", record)
    #         if record[0][0] > 0:
    #             update_line = """update hr_attendance set check_out = '%s' where
    #             employee_id = '%s' and attendance_date = '%s' """ % (
    #                 check_out, emp_id, punch_date)
    #             print("record updated")
    #             self.env.cr.execute(update_line)
    #             return 'record_updated'
    #
    #         else:
    #             date1 = datetime.datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
    #             date2 = date1.date()
    #             date3 = date2.strftime(('%Y-%m-%d'))
    #             date4 = date3 + ' ' + str(math.ceil(shift_end)) + ':00:00'
    #             print('date4', date4)
    #
    #             if policies_varify:
    #                 policies_varify.update({'employee_id': emp_id,
    #                                         'check_in': check_out,
    #                                         # 'check_out': date4,
    #                                         'check_out': check_out,
    #                                         'worked_hours': worked_hours,
    #                                         'attendance_date': punch_date,
    #                                         'out_manual': 'Out Manual',
    #                                         'is_review': True,
    #                                         'scheduler': True})
    #                 print("final dics3 same day", policies_varify)
    #                 # print(a)
    #                 self.env['hr.attendance'].create(policies_varify)
    #                 print("record_created successfully............................")
    #                 return 'record_created'
    #     else:
    #         print("this is new")
    #         nearest_shift_end = self.same_day_check_out_date(emp_id, check_in, check_out, punch_date, shift_start,
    #                                                          shift_end, policies_varify)
    #         return nearest_shift_end

    # OVERTIME COMPUTATION ACCORDING TO MONTH IS DEFINED IN THIS FUNCTION
    # def ot_computation(self,policy):
    #     shifts,shift_id=self.shifts_list()
    #     # overtime_days = {'overtime': 0}
    #     for shift in shifts:
    #         if shift.ot_options=='ot1':
    #             query="""select sum(add_or_deduct) from hr_attendance WHERE check_in BETWEEN
    #             date(to_char(NOW(),'YYYY-MM-01')) and date(Now() + interval '1 day') and employee_id = 44
    #             and ot_day_status = True """
    #             self.env.cr.execute(query)
    #             sum=self.env.cr.fetchone()
    #             if sum[0]<=policy.max_ot_hrs:
    #                 # overtime_days['overtime']=sum[0]/policy.no_hrs
    #                 return sum[0]/policy.no_hrs
    #             elif sum[0]>policy.max_ot_hrs and max_ot_allow=='limited':
    #                 # overtime_days['overtime']=policy.max_ot_hrs/policy.no_hrs
    #                 return policy.max_ot_hrs/policy.no_hrs
    #             else:
    #                 # overtime_days['overtime']=sum[0]/policy.no_hrs
    #                 return sum[0]/policy.no_hrs
    #         elif shift.ot_options=='ot2':
    #             query="""select sum(worked_hours) from hr_attendance WHERE check_in BETWEEN
    #             date(to_char(NOW(),'YYYY-MM-01')) and date(Now() + interval '1 day') and employee_id = 44"""
    #             self.env.cr.execute(query)
    #             sum=self.env.cr.fetchone()
    #             total_hours=[]
    #             # for sh in shift_id:
    #             #     total_hours.append(sh.hour_to-sh.hour_from)
    #         else:
    #             pass
    #     # return overtime_days


class AttendanceChecks(models.Model):
    _name = 'attendance.checks'

    process_name = fields.Char('Attendance Punches')
    runtime=fields.Datetime("Process RunTime")
    last_run = fields.Datetime("last run")
    next_run = fields.Datetime("next run")
    interval = fields.Integer("Between This Interval Schedular Has To Run")
    company_id = fields.Many2one('res.company', 'Company',default=lambda self: self.env.user.company_id.id)


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def create(self, vals):
        res = super(ResCompany, self).create(vals)

        print ("resssssss data", res.id)

        self.env['attendance.checks'].create({
            'process_name':'Attendance',
            'interval':2,
            'company_id':res.id
        })

        return res












