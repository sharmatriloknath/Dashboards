from odoo import models, fields, api, exceptions, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz

class ProcessAttendance(models.TransientModel):
    _name = 'process.attendance'
    _description = 'process_attendance'
    name = fields.Char(string="Monthly Detail", default='Monthly Detail')
    from_date=fields.Date(string="From Date")
    to_date=fields.Date(string="To Date")
    process_attendance_ids = fields.One2many('process.attendance.details', 'attendance_detail_id',string= 'Attendance Details')
    company_id=  fields.Many2one('res.company', 'Company',default=lambda self: self.env.user.company_id.id)




    def process_employee_attendance(self):

        result = []
        self.process_attendance_ids =  ''
        print("ggdhdhdj")
        objs = self.env["hr.attendance"].search([('attendance_date', '>=', self.from_date), ('attendance_date', '<=', self.to_date),('company_id', '=', self.company_id.id)], order='employee_id,attendance_date')
        print('objs1', objs)
        # print(a)
        for val in objs:
            temp1 = {}
            employee_id = val.employee_id
            from_date = self.from_date
            to_date = self.to_date

            delta = (datetime.strptime(self.to_date, '%Y-%m-%d') - datetime.strptime(self.from_date,'%Y-%m-%d')).days
            total_days = delta
            # print('emlll', val.employee_id.id)
            # print('from date', self.from_date)
            # print('to date', self.to_date)
            # print('type to date', type(self.to_date))
            # delta = (datetime.strptime(self.to_date, '%Y-%m-%d') - datetime.strptime(self.from_date,'%Y-%m-%d')).days
            # print ("total days",delta)
            temp1.update({
                              'from_date':from_date,
                              'to_date':to_date,
                              'total_days':total_days,
                              'employee_id':val.employee_id.id,
                              'overtime_duration':val.overtime_duration,
                              'in_manual':val.in_manual,
                              'out_manual':val.out_manual,
                              'departure_early':val.departure_early,
                             'la_day_status':val.la_day_status,
                             'ed_day_status':val.ed_day_status,
                             'ot_day_status':val.ot_day_status,
                              'attendance_detail_id':self.id
                              })

            if val.employee_day_status:
                # print('day status', val.employee_day_status)
                employee_day_status = val.employee_day_status
                temp1.update({'employee_day_status':employee_day_status})

            if val.late_coming == 'yes':
                # print('day status', val.late_coming)
                late_coming=val.late_coming
                temp1.update({'late_coming': late_coming})
            print('nnndsnn')
            # print("dddddddddddddddddddddddddddddddddddddddddddddddd",val.employee_id.emp_code)
            # print (a)
            for values in val.employee_id:
                values1 = self.env['hr.employee'].sudo().search([('id','=',values.id),('company_id', '=', self.company_id.id)])
                print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",values1)


                print('name',values1.name)
                print('name',values1)
                # print(a)
                # print('department',values.department_id.name)
                # print('designation',values.job_id.name)
                # print('leaves', values.leaves_count)
                print ('nnnnnnn11111')
                name = values1.name
                department = values1.department_id.name
                designation = values1.job_id.name
                leaves = values1.leaves_count
                # employee_code = values.emp_code

                temp1.update({
                              'name':name,
                              'department':department,
                              'designation':designation,
                              'leaves':leaves,
                              # 'employee_id':employee_code
                              })

            # print ('final dictionary is :',temp1)
            result.append(temp1)
            print('result111111',result)

        tempDict = {}
        for record in result:
            tempKey = record["employee_id"]
            if tempKey in tempDict:
                # pass
                tempDict[tempKey]["overtime_duration"] += record["overtime_duration"]

            else:
                tempDict[tempKey] = record
                tempDict[tempKey]["absent_count"], tempDict[tempKey]["present_count"], tempDict[tempKey]["late_coming_count"],tempDict[tempKey]["in_manual_count"],tempDict[tempKey]["out_manual_count"],tempDict[tempKey]["departure_early_count"],tempDict[tempKey]["la_day_status_count"],tempDict[tempKey]["ed_day_status_count"],tempDict[tempKey]["ot_day_status_count"]= 0, 0,0,0,0,0,0,0,0

            # tempDict[tempKey] = record
            # tempDict[tempKey]["absent_count"], tempDict[tempKey]["present_count"], tempDict[tempKey][
            #     "late_coming_count"] = 0, 0, 0

            if record.get('employee_day_status', False):
                if record['employee_day_status'] == 'absent':
                    # print(tempKey, 'Absent')
                    tempDict[tempKey]['absent_count'] += 1
                else:
                    # print(tempKey, 'Present')
                    tempDict[tempKey]['present_count'] += 1

            if record.get('late_coming', False):
                if record['late_coming'] == 'yes':
                    # print(tempKey, 'Absent')
                    tempDict[tempKey]['late_coming_count'] += 1
            if record.get('in_manual',False):
                if record['in_manual']=='In Manual':
                    tempDict[tempKey]['in_manual_count'] += 1

            if record.get('out_manual',False):
                if record['out_manual']=='Out Manual':
                    tempDict[tempKey]['out_manual_count'] += 1

            if record.get('departure_early',False):
                if record['departure_early']=='yes':
                    tempDict[tempKey]['departure_early_count'] += 1

            if record.get('la_day_status',False):
                if record['la_day_status']==True:
                    tempDict[tempKey]['la_day_status_count'] += 1

            if record.get('ed_day_status',False):
                if record['ed_day_status']==True:
                    tempDict[tempKey]['ed_day_status_count'] += 1

            if record.get('ot_day_status',False):
                if record['ot_day_status']==True:
                    tempDict[tempKey]['ot_day_status_count'] += 1



            # print('record',record)
            # print ('record',record.get("employee_id"))
        tempList = [tempDict[i] for i in tempDict]

        print('tempList:1111111111',tempList)
        # print(a)
        for record_dict in tempList:
            self.env["process.attendance.details"].create(record_dict)
        # print(a)



        # for val in objs:
        #     if val:
        #         res = {}
        #         print('val',val)
        #         print('objs',val.attendance_date)
        #         print('objs', val.id)
        #         attendance_date = val.attendance_date
        #         id =  val.id
        #
        #
        #
        #         res.update({'employee_id':id,'attendance_date':attendance_date})
        #         print ('res under loop',res)
        #         self.env["process.attendance.details"].create(res)

        # print('res outer',res)
        # pass

    def process_attendance_cancel(self):
        self.process_attendance_ids = ''
        self.from_date = ''
        self.to_date = ''




class ProcessAttendanceDetails(models.TransientModel):
    _name = 'process.attendance.details'
    _description = 'process_attendance_details'


    attendance_detail_id = fields.Many2one('process.attendance',string="Employee ID")
    employee_id = fields.Integer(string="Employee ID")
    # employe_name = fields.Char(string="Employee Name")
    # attendance_date = fields.Date(string="Employee ID")
    name = fields.Char(string="Employee Name")
    department = fields.Char(string="Department")
    late_coming_count = fields.Integer('Late Come')
    designation = fields.Char('Designation')
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date')
    present_count = fields.Integer('Attendance')
    absent_count = fields.Integer('Absent')
    leaves =fields.Integer('Leaves')
    total_days = fields.Integer('Number of days')
    overtime_duration = fields.Float('Total Overtime')
    in_manual_count = fields.Integer('In Manual')
    out_manual_count = fields.Integer('Out Manual')
    departure_early_count= fields.Integer('Departure Early')
    la_day_status_count = fields.Integer('Late Arrival')
    ed_day_status_count = fields.Integer('Early Departure')
    ot_day_status_count = fields.Integer('Overtime Count')

    detailed_attendance_lines = fields.One2many('detailed.attendance.details', 'detailed_attendant_id', string='Detailed Attendance Details')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id)

    def hr_attendance_details(self):
        res=[]
        self.detailed_attendance_lines = []
        employee_id = int(self.env.context.get('employee_id'))
        date_from = self.env.context.get('date_from')
        department = self.env.context.get('department')
        designation = self.env.context.get('designation')
        total_days = self.env.context.get('total_days')
        name = self.env.context.get('name')
        date_to = self.env.context.get('date_to')
        # print('gggggg',type(employee_id))
        # print('gggggg', employee_id)
        # print('date_from',date_from)
        # print('department', department)
        # print('designation', designation)
        # print('name', name)
        # print('department', department)
        # print('date_to', date_to)
        detail = self.env["hr.attendance"].search([('attendance_date', '>=', date_from), ('attendance_date', '<=', date_to),('employee_id', '=',employee_id),('company_id', '=',self.company_id.id)],order='employee_id,attendance_date')
        # print("Object details",detail)
        if detail:
            for val in detail:
                # date1=val.check_in
                # date2=val.check_out
                # view_check_out=None
                # view_check_in=None
                # user_tz = self.env.user.tz or pytz.utc
                # print("The user time zone is:",user_tz)
                # local = pytz.timezone(user_tz)
                # print ("The lacal is :",local)
                # print("The date from the database is in timezone of ....................................................",date1)
                # if date1 and date2:
                #     display_date_result = pytz.utc.localize(datetime.strptime(date1, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
                #     display_date_result1 = pytz.utc.localize(datetime.strptime(date2, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
                #
                #     print("The date from the database is in timezone of ..........after change in the timezone..........................................",type(display_date_result),display_date_result)
                #     date3=display_date_result-datetime.strptime(date1,DEFAULT_SERVER_DATETIME_FORMAT)
                #     date4=display_date_result1-datetime.strptime(date2,DEFAULT_SERVER_DATETIME_FORMAT)
                #     print("upto here no problem")
                #     view_check_in=datetime.strptime(date1,DEFAULT_SERVER_DATETIME_FORMAT)-date3
                #     view_check_out=datetime.strptime(date2,DEFAULT_SERVER_DATETIME_FORMAT)-date4
                # elif date1 and not date2:
                #     print("check_out not present")
                #     display_date_result = pytz.utc.localize(datetime.strptime(date1, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
                #     date3=display_date_result-datetime.strptime(date1,DEFAULT_SERVER_DATETIME_FORMAT)
                #     view_check_in=datetime.strptime(date1,DEFAULT_SERVER_DATETIME_FORMAT)-date3
                # else:
                #     print ("check_in not present")
                #     display_date_result1 = pytz.utc.localize(datetime.strptime(date2, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local).replace(tzinfo=None)
                #     date4=display_date_result1-datetime.strptime(date2,DEFAULT_SERVER_DATETIME_FORMAT)
                #     view_check_out=datetime.strptime(date2,DEFAULT_SERVER_DATETIME_FORMAT)-date4



                # print("employee_id:",val.employee_id.id)
                attendance_details = self.env['detailed.attendance.details'].create({
                    'employee_id': val.employee_id.id,
                    'from_date':date_from,
                    'to_date':date_to,
                    'worked_hours':val.worked_hours,
                    'late_coming':val.late_coming,
                    'departure_early':val.departure_early,
                    'employee_day_status':val.employee_day_status,
                    'overtime_duration':val.overtime_duration,
                    'is_review':val.is_review,
                    'check_in':val.check_in,
                    'check_out':val.check_out,
                    'attendance_date':val.attendance_date,
                    'department':department,
                    'designation':designation,
                    'total_days':total_days,
                    'in_manual':val.in_manual,
                    'out_manual':val.out_manual,
                    'ot_day_status':val.ot_day_status,
                    'la_day_status':val.la_day_status,
                    'ed_day_status':val.ed_day_status,
                    'name':name

                })
                # print ("DDDDDDDDDDD,attendance_detailsD",attendance_details)
                res.append(attendance_details.id)

        # self.detailed_attendance_lines = res
        print('RESSSSSSSSSSSSSS',res,tuple(res))
        view = self.env.ref('hr_attendance_ext.detailed_attendance_process_tree')
        return {
            'name': _('Attendance Details'),
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', tuple(res))],
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'detailed.attendance.details',
            'views': [(view.id, 'tree')],
            'view_id': view.id,
            'target': 'current',
            # 'res_id': self.id,

        }
        # print("the final list of record:",res)



        # view = self.env.ref('mrp.action_open_form_consumed_material_form')
        # consumed_id = self.env['mrp.consumed.materials'].search([('move_id', '=', self.id)])
        #
        # if len(consumed_id) > 0:
        #     for val in self:
        #         consumed_id.required_qty = val.product_uom_qty

        # return {
        #     'name': _('IH'),
        #     'type': 'ir.actions.act_window',
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'res_model': 'detailed.attendance.details',
        #     'views': [(view.id, 'tree')],
        #     'view_id': view.id,
        #     'target': 'new',
        #
        # }


class DetailedAttendanceDetails(models.TransientModel):
    _name = 'detailed.attendance.details'


    detailed_attendant_id = fields.Many2one('process.attendance.details',string="detailed lines")
    employee_id = fields.Integer(string="Employee ID")
    name = fields.Char(string="Employee Name")
    department = fields.Char(string="Department")
    late_coming = fields.Char('Late Coming')
    designation = fields.Char('Designation')
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date')
    total_days = fields.Integer('Number of days')
    worked_hours = fields.Float('Worked Hours')
    departure_early = fields.Char('Early Departure')
    overtime_duration = fields.Float('Overtime Duration')
    is_review=fields.Boolean("Is Review")
    employee_day_status=fields.Char("Present/Absent")
    attendance_date=fields.Date("Attendance")
    check_in =fields.Datetime("Check In")
    check_out =fields.Datetime("Check Out")
    in_manual =fields.Char("In Manual")
    out_manual =fields.Char("Out Manual")
    ot_day_status =fields.Boolean("OT Status")
    la_day_status =fields.Boolean("LA Status")
    ed_day_status =fields.Boolean("ED Status")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id)







