from odoo import api, fields, models, tools, _
from odoo.http import Controller, request
import time, datetime
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, RedirectWarning, except_orm
from odoo.addons import decimal_precision as dp
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.tools import pycompat
from odoo.tools.float_utils import float_round
from datetime import timedelta
import datetime
import dateutil.relativedelta
from dateutil.relativedelta import relativedelta
from datetime import datetime as dt
from lxml import etree
from threading import Timer
import re


class PurchaseExtensionDashboard(models.Model):
    _description = "purchase Detail"
    _name = "purchase.extension.dashboard"

    active = fields.Boolean('Active', default=True, store=True)
    name = fields.Selection([
        ('material.req.slip', 'Purchase Indent'),
        ('purchase.req', 'PR'),
        ('purchase.order', 'PO'),
        ('request.for.quotation', 'RFQ'),
        ('supplier.quotation', 'Quotation'),
        ('pr.create.data', 'Create PR'),
        ('purchase.requisition', 'Purchase Agreements'),
        ('purchase.requisition.amd', 'Purchase Ammendmend'),
        ('kpi.matrix', 'KPI Matrix')
    ], string="Name")
    computation = fields.Char(compute="_computation")
    total = fields.Integer("Total")
    user_id = fields.Many2one('res.users', 'User')
    company_id = fields.Many2one('res.company', 'Company')
    pending = fields.Integer("Pending")
    high_priority = fields.Integer("High Priority")
    color = fields.Integer('Color')
    view_type = fields.Boolean('Type', default=True)
    user_wise_id = fields.One2many("purchase.extension.dashboard.user.wise", "purchase_ext_dashboard_id")
    have_child = fields.Boolean('Have Child', default=False)
    emp_id = fields.Integer("employee id")
    require_date = fields.Date(string='Require Date')
    cancelled = fields.Integer("Cancelled")
    rfq_not_sent = fields.Integer("RFQ not sent")
    email_not_sent = fields.Integer("Email Not Sent")
    inactive_item = fields.Integer("Inactive Items")
    inactive_vendor = fields.Integer("Inactive Vendor")
    supplier_without_email = fields.Integer("Email Does Not Exist")
    items_without_hsn = fields.Integer("Items Without HSN")
    expire_in_two_month = fields.Integer("Expire In Next Two Months" ,store = True)
    modified_in_last_month = fields.Integer("Modified In From Last Month", store = True)
    exhaust_commitment_value = fields.Float("Exhaust Commitment Value", store = True)

    @api.multi
    def _computation(self):
        model_used = []
        self.data_from_kpi()
        emp_dict = {}
        emp_total = {}
        for record in self:
            if record.name not in model_used:
                model_used.append(record.name)
                # Tilok 21 sep start
                user_id1 = self._context.get("uid")
                user = self.env['res.users'].browse(user_id1)

                '''This code is for Management who can see all the records because he has complete access rights'''
                if user.has_group('purchase_extension.group_purchase_management'):

                    if str(record.name) == 'pr.create.data':
                        print("The model that we have", record.name)
                        pending_cr = record.execute_query_for_management("pending")
                        print("this is the model", pending_cr)
                        min_require_date = None
                        for cr_obj in pending_cr:
                            if cr_obj.require_date:
                                if not min_require_date:
                                    min_require_date = cr_obj.require_date
                                if cr_obj.require_date < min_require_date:
                                    min_require_date = cr_obj.require_date
                        if min_require_date:
                            min_require_date = min_require_date.split()[0]
                            record.sudo().write({"require_date": min_require_date, "pending": len(pending_cr)})
                        if len(pending_cr) == 0:
                            record.write({"color": 10})
                        else:
                            record.write({"color": 9})

                    elif str(record.name) == 'kpi.matrix':
                        total_record = record.execute_query_for_management('kpi')
                        if total_record:
                            record.write({
                                          "inactive_item": total_record[0].inactive_items,
                                           "inactive_vendor": total_record[0].inactive_vendor,
                                          'supplier_without_email': total_record[0].supplier_dont_have_email,
                                          'items_without_hsn': total_record[0].item_not_linked_with_hsn})

                    elif str(record.name) == 'purchase.requisition':
                        total_record = []
                        total_record = record.execute_query_for_management('total')
                        print("the requisition data is", total_record)
                        deadline_date = []
                        for agreement in total_record:
                            deadline_date.append(agreement.date_end)
                        current_date = datetime.datetime.today()
                        after_two_months = current_date + relativedelta(months=2)
                        expire = 0
                        for date in deadline_date:
                            if datetime.datetime.strptime(date,'%Y-%m-%d %H:%M:%S') >= current_date and datetime.datetime.strptime(date,'%Y-%m-%d %H:%M:%S') < after_two_months:
                                expire += 1
                        total_values = []
                        for record in total_record:
                            po_list = []
                            if record.type_id.type == 'arc':
                                po_list.append(record.purchase_ids)
                            for po in po_list:
                                for purchase in po:
                                    if purchase.state in ('purchase', 'done'):
                                        total_values.append(purchase.amount_total)

                        exhaust_value = sum(total_values)

                        print("the len(total_record)", len(total_record))
                        print("the expire", expire)
                        print("the exhaust_value", exhaust_value)

                        record.env.cr.execute(
                            'update purchase_extension_dashboard set total=%s , '
                            'expire_in_two_month=%s,exhaust_commitment_value=%s where id=%s'
                            % (len(total_record), expire, exhaust_value, record.id))

                        # record.sudo().write(
                        # {"total": len(total_record),
                        # 'expire_in_two_month': expire,
                        # 'exhaust_commitment_value': exhaust_value})

                        # record.sudo().update(
                        # {
                        # 'total': len(total_record),
                        # 'expire_in_two_month': expire,
                        # 'exhaust_commitment_value': exhaust_value
                        # })

                    elif str(record.name) == 'purchase.requisition.amd':
                        total_record = []
                        total_record = record.execute_query_for_management('total')
                        modified_date = []
                        for agreement in total_record:
                            modified_date.append(agreement.write_date)

                        current_date = datetime.datetime.today()
                        from_last_months = current_date + relativedelta(months= -1)
                        modified = 0
                        for date in modified_date:
                            if datetime.datetime.strptime(date,'%Y-%m-%d %H:%M:%S') <= current_date and datetime.datetime.strptime(date,'%Y-%m-%d %H:%M:%S') > from_last_months:
                                modified += 1
                        print("the modified_date is", modified_date)
                        print("the modified_date is", current_date)
                        print("the modified_date is", from_last_months)
                        print("the modified_count is", modified)
                        record.sudo().write({"total": len(total_record), 'modified_in_last_month': modified})

                    else:
                        cancelled_data = []
                        rfq_not_sent_data = []
                        email_not_sent_data = []
                        total_data = record.execute_query_for_management("total")
                        pending_data = record.execute_query_for_management("pending")
                        if str(record.name) == 'purchase.order' or str(record.name) == 'purchase.req':
                            cancelled_data = record.execute_query_for_management("cancelled")
                        if str(record.name) == 'request.for.quotation':
                            rfq_not_sent_data = record.execute_query_for_management('confirm')
                        if str(record.name) == 'purchase.order':
                            email_not_sent_data = record.execute_query_for_management('unsent')
                        record.sudo().write({"total": len(total_data), "pending": len(pending_data), 'cancelled': len(cancelled_data),'rfq_not_sent': len(rfq_not_sent_data), 'email_not_sent': len(email_not_sent_data)})
                        if len(pending_data) == 0:
                            record.write({"color": 10})
                        else:
                            record.write({"color": 9})

                # Trilok 20 sep end

                #Trilok Start 26-09-19
                else:
                    if self.env.user.has_group('purchase_extension.group_product_category_wise_acces'):
                        record_category_wise = record.get_category_wise_record_list(record.name)
                        # print("The data in the record is",record_category_wise)
                        self.categ_wise_record_fun1(record, record_category_wise)
                        # print(a)
                    #Trilok Ends here
                    else:
                        if record.user_id.id == self.env.user.id and record.company_id.id == record.env.user.company_id.id:
                            query="""select * from res_groups_users_rel where gid in (select id from res_groups where 
                            category_id in (select id from ir_module_category where name ilike 'Purchases')) and uid=%s""" %(user.id)
                            record.env.cr.execute(query)
                            condition_satisfied = record.env.cr.fetchall()
                            if condition_satisfied:
                                user_wise_list = []
                                have_child = False
                                if record.name:

                                    emp_id = record.env["hr.employee"].search([("user_id", "=", record.env.user.id)]).id
                                    if emp_id:
                                        if str(record.name) == 'pr.create.data':
                                            pending_cr = record.execute_query("pending", emp_id)
                                            min_require_date = None
                                            if pending_cr:
                                                for cr_obj in pending_cr:
                                                    if cr_obj.require_date :
                                                        if not min_require_date:
                                                            min_require_date = cr_obj.require_date
                                                        if cr_obj.require_date < min_require_date:
                                                            min_require_date = cr_obj.require_date
                                                # cr_user_dict = {
                                                #     "pending": len(self.execute_query("pending", emp_id)),
                                                #     "require_date": min_require_date,
                                                #     "have_child": False
                                                # }
                                                # print({"require_date": min_require_date, "pending": len(record.execute_query("pending", emp_id)), "have_child": have_child,
                                                #      "emp_id": emp_id})
                                                if min_require_date:
                                                    min_require_date = min_require_date.split()[0]
                                                    record.sudo().write({"require_date": min_require_date, "pending": len(pending_cr), "have_child": have_child,"emp_id": emp_id})
                                                # change code to resolve the error by trilok helped by pushkal
                                                else:
                                                    record.sudo().write({"require_date": min_require_date, "pending": len(pending_cr),"have_child": have_child, "emp_id": emp_id})
                                                if len(pending_cr) == 0:
                                                    record.write({"color": 10})
                                                else:
                                                    record.write({"color": 9})
                                        else:

                                            emp_objs = record.env["hr.employee"].search([("parent_id", "=", emp_id)])
                                            if len(emp_objs) > 0:
                                                have_child = True
                                            emp_dict.update({emp_id: {}})
                                            emp_id_val = record.get_employee_child(emp_objs, emp_dict.get(emp_id))
                                            if emp_id_val:
                                                emp_dict.get(emp_id).update(emp_id_val)
                                            emp_total = record.get_list_of_keys(emp_dict, emp_total, 1)
                                            emp_string = str(emp_dict)
                                            sequence_list = []
                                            for s in re.split("{|:|}|,| ", emp_string):
                                                if s.isdigit():
                                                    sequence_list.append(int(s))
                                            emp_total_sequence = []
                                            for i in sequence_list:
                                                for key, val in emp_total.items():
                                                    if i == key:
                                                        emp_total_sequence.append([key, val])
                                            for element in emp_total_sequence:
                                                if emp_id == element[0]:
                                                    total = element[1].get("total")
                                                    pending = element[1].get("pending")
                                                    record.sudo().write({"total": total, "pending": pending, "have_child": have_child, "emp_id": emp_id})
                                                    if pending == 0:
                                                        record.write({"color": 10})
                                                    else:
                                                        record.write({"color": 9})
                                                user_wise = (0, False, {
                                                    "emp_id": element[0],
                                                    "emp_name": record.env["hr.employee"].search([("id", "=", element[0])]).name,
                                                    "user_wise_total": element[1].get("total"),
                                                    "user_wise_pending": element[1].get("pending"),
                                                    "level": str(element[1].get('level')),
                                                })
                                                user_wise_list.append(user_wise)
                                            line_obj = record.env["purchase.extension.dashboard.user.wise"].search(
                                                [("purchase_ext_dashboard_id", "=", record.id)])
                                            if len(line_obj) > 0:

                                                if len(line_obj) == len(user_wise_list):
                                                    for i, line in enumerate(line_obj):
                                                        line.sudo().write(user_wise_list[i][2])
                                                elif len(line_obj) > len(user_wise_list):
                                                    for i, line in enumerate(line_obj):
                                                        try:
                                                            line.sudo().write(user_wise_list[i][2])
                                                        except:
                                                            query = "delete from purchase_extension_dashboard_user_wise where id ="+ str(line.id)
                                                            record.env.cr.execute(query)
                                                elif len(line_obj) < len(user_wise_list):
                                                    a = 0
                                                    list_of_new_users = []
                                                    for i, line in enumerate(line_obj):
                                                        line.sudo().write(user_wise_list[i][2])
                                                        a = i
                                                    for j, user in enumerate(user_wise_list):
                                                        if j > a:
                                                           list_of_new_users.append(user)
                                                    # print ("record managerrrrrrrrrrrrr",record)
                                                    # print ("user wise listttttttttt mangerrrrr", user_wise_list)
                                                    # print ("manager list_of_new_users",list_of_new_users)
                                                    record.sudo().write({"user_wise_id": list_of_new_users})
                                            else:
                                                record.sudo().write({"user_wise_id": user_wise_list})
                                    else:
                                        record.write({"active": False})

    @api.model
    def create_card_for_user(self):
        model_names = []
        users = self.env["res.users"].search([("id", ">", 0)])
        names = self.env["purchase.extension.dashboard.query"].search([("id", ">", 0)])
        for name in names:
            model_names.append(name.model_name)
        model_names = set(model_names)
        for user in users:
            for company in user.company_ids:
                for name in model_names:
                    self.env['purchase.extension.dashboard'].create({"name": name, "user_id": user.id,
                                                                     "company_id": company.id})

    @api.multi
    def compute_by_scheduler(self):
        return {
            'type': 'ir.actions.window',
            'tag': 'reload',
        }

    def execute_query_for_management(self,label_name):
        list_query_obj = []
        # print("the models in the field is", self.name)
        try:
            query = self.env["purchase.extension.dashboard.query"].search([("model_name", "=", str(self.name)),
                                                                       ("label_name", "=", label_name)]).query
            company_id = self.env.user.company_id.id
            if query:
                if label_name == 'total' and str(self.name) != 'pr.create.data' and str(self.name) != 'kpi.matrix':
                    if str(self.name) == 'material.req.slip':
                        query = str(query) + " where type = 'indent' and company_id=" + str(company_id)
                    else:
                        query = str(query)  + " where company_id=" + str(company_id)
                elif label_name == 'pending' and str(self.name) != 'pr.create.data'  and  str(self.name) != 'material.req.slip' and str(self.name) != 'kpi.matrix':
                    query = str(query) + " and company_id=" + str(company_id)
                elif label_name == 'pending' and str(self.name) == 'pr.create.data':
                    query = str(query) + " where company_id=" + str(company_id) + ")"
                    print("the final query is ", query)
                elif label_name == 'cancelled' and (str(self.name) == 'purchase.order' or str(self.name) == 'purchase_req'):
                    query = str(query) + " and company_id = " + str(company_id)

                elif label_name == 'confirm' and str(self.name) == 'request.for.quotation':
                    query = str(query) + " and company_id=" + str(company_id)

                elif label_name == 'unsent' and str(self.name) == 'purchase.order':
                    query = str(query) + " and company_id=" + str(company_id)
                elif label_name == 'kip' and str(self.name) == 'kip.matrix':
                    query = str(query) + " where company_id=" + str(company_id)

                self.env.cr.execute(query)
                list_query_dict = self.env.cr.dictfetchall()
                for query_dict in list_query_dict:
                    list_query_obj.append(self.env[self.name].search([("id", "=", query_dict["id"])]))
        except:
            list_query_obj = []
        return list_query_obj

    def execute_query(self, label_name, emp_id, categ_status = False):
        list_query_obj = []
        try:
            user_id = self.env["hr.employee"].search([("id", "=", emp_id)]).user_id[0]
            query = self.env["purchase.extension.dashboard.query"].search([("model_name", "=", str(self.name)),
                                                                           ("label_name", "=", label_name)]).query
            company_id = self.env.user.company_id.id
            if query:
                if label_name == 'total' and str(self.name) != 'pr.create.data':
                    query = str(query) + " where company_id=" + str(company_id) + " and create_uid=" + str(user_id.id)
                elif label_name == 'pending' and str(self.name) != 'pr.create.data':
                    query = str(query) + " and company_id=" + str(company_id) + " and create_uid=" + str(user_id.id)
                elif label_name == 'pending' and str(self.name) == 'pr.create.data':
                    query = str(query) + " where company_id=" + str(company_id) + " and create_uid=" + str(user_id.id) + ")"
                self.env.cr.execute(query)
                list_query_dict = self.env.cr.dictfetchall()
                for query_dict in list_query_dict:
                    list_query_obj.append(self.env[self.name].search([("id", "=", query_dict["id"])]))
        except:
            list_query_obj = []
        return list_query_obj

    def get_employee_child(self, emp_objs, emp_dict):
        if emp_objs:
            for emp_obj in emp_objs:
                emp_dict.update({emp_obj.id: {}})
                emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_obj.id)])
                emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_obj.id))
                if emp_obj and emp_id_val:
                    emp_dict.get(emp_obj.id).update(emp_id_val)
        else:
            return emp_dict

    def get_total(self, emp_dict):
        val_user_dict1 = {
            "total": 0,
            "pending": 0,
        }
        for key, val in emp_dict.items():
            val_user_dict = {
                "total": len(self.execute_query("total", key)),
                "pending": len(self.execute_query("pending", key)),
                }
            if val:
                val_user_dict2 = self.get_total(val)
                val_user_dict["total"] = int(val_user_dict["total"]) + int(val_user_dict2["total"])
                val_user_dict["pending"] = int(val_user_dict["pending"]) + int(val_user_dict2["pending"])
            if not val_user_dict["total"]:
                val_user_dict["total"] = 0
            if not val_user_dict["pending"]:
                val_user_dict["pending"] = 0
            val_user_dict1["total"] = int(val_user_dict1["total"]) + int(val_user_dict["total"])
            val_user_dict1["pending"] = int(val_user_dict1["pending"]) + int(val_user_dict["pending"])
        return val_user_dict1

    #Trilok Changes 26-09-19
    def get_list_of_keys(self, emp_dict, emp_total, level, categ_dict =False, categ_status =False):
        # print ("get lost keyssssssssss",self, emp_dict, emp_total, level)
        categ_list_data = categ_dict
        categ_status_check = categ_status
        for key, val in emp_dict.items():
            # if categ_status:
            #     total = self.execute_query("total",key)
            #     pending = self.execute_query("pending",key)
            if categ_list_data and categ_status_check:
                total = len(self.execute_query1("total", key, categ_list_data, categ_status_check))
                pending = len(self.execute_query1("pending", key, categ_list_data, categ_status_check))
            else:
                total = len(self.execute_query("total", key))
                pending = len(self.execute_query("pending", key))
            if not total:
                total = 0
            if not pending:
                pending = 0
            emp_total.update({key: {"total": total, "pending": pending, "level": level}})
            if val:
                if categ_list_data and categ_status_check:
                    val_dict = self.get_total1(val, categ_list_data, categ_status_check)
                else:
                    val_dict = self.get_total(val)
                if categ_list_data and categ_status_check:
                    emp_total = self.get_list_of_keys(val, emp_total, level+1, categ_list_data, categ_status_check )
                else:
                    emp_total = self.get_list_of_keys(val, emp_total, level+1)
                if not val_dict["total"]:
                    val_dict["total"] = 0
                if not val_dict["pending"]:
                    val_dict["pending"] = 0
                # print ("remp totallllllllllllllllll",emp_total)
                # print ("valuessssssssssss",total ,val_dict["total"],type(total),type(val_dict["total"]))
                emp_total.update({key: {"total": total + val_dict["total"], "pending": pending + val_dict["pending"],
                                  "level": level}})
        # print ("return emp totallllllllllll")
        return emp_total
    #End here

    # @api.multi
    # def write(self, values):
    #     print ("write of purchase extension dashboardddddddddd",self,values)
    #     print ("context in Write of Dashboard",self._context)
    #     res = super(PurchaseExtensionDashboard, self).write(values)
    #     return res

    # @api.multi
    # @api.onchange('name')
    # def _compute_total(self):
    #     emp_dict = {}
    #     emp_total = {}
    #     user_wise_list = []
    #     if self.name:
    #         print(self.execute_activity_query("total"), self.execute_activity_query("pending_for_approval"), "2222222222222")
    #         # attr = ["total", "pending_for_approval"]
    #         # for i in attr:
    #         #     setattr(self, str(i), self.execute_activity_query(str(i)))
    #         self.total = self.execute_activity_query("total")
    #         self.pending_for_approval = self.execute_activity_query("pending_for_approval")
    #
    #         if self.pending_for_approval == 0:
    #             self.color = 10
    #             print("grrrrrrrrrrrrrrrrrrreeeeeeeeeeeeeeeeeeeeeeeeeeen")
    #         else:
    #             self.color = 9
    #             print(self.color, "reeeeeeeeeeeeddddddddddddddddd")
    #         emp_id = self.env["hr.employee"].search([("user_id", "=", self.env.user.id)]).id
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         print(emp_dict)
    #         # changes start
    #         emp_total = self.get_list_of_keys(emp_dict, emp_total, 1)
    #         print(emp_total, "final dict")
    #         for key, val in emp_total.items():
    #             user_wise = {
    #                 "emp_id": key,
    #                 "emp_name": self.env["hr.employee"].search([("id", "=", key)]).name,
    #                 "user_wise_total": val["total"],
    #                 "user_wise_pending": val["pending"],
    #                 "level_color": str(val['level']),
    #
    #             }
    #             user_wise_list.append(user_wise)
    #         self.user_wise_id = user_wise_list

    def get_obj_of_keys(self, emp_dict, obj_list):
        for key, val in emp_dict.items():
            objs = self.execute_query("total", key)
            for obj in objs:
                if obj.id:
                    obj_list.append(obj.id)
            if val:
                obj_list = self.get_obj_of_keys(val, obj_list)
        return obj_list

    # @api.multi
    # def get_total_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     # print(emp_id, "employee")
    #     # ravi at 5/4/2019 start
    #     emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
    #     # ravi at 5/4/2019
    #     emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #     emp_dict.update({emp_id: {}})
    #     emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #     if emp_id_val:
    #         emp_dict.get(emp_id).update(emp_id_val)
    #     obj_list = self.get_obj_of_keys(emp_dict, obj_list)
    #     if self.name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', obj_list)]
    #         result['target'] = 'main'
    #         result["status"] = "total"
    #     # ravi at 5/4/2019 start
    #     # return result
    #     if (self.name == 'purchase.req'):
    #         if len(emp_id_user)<=0:
    #             raise ValidationError(_('Please define employee for related user'))
    #             return 0
    #         else:
    #             return result
    #         # print("VALLLLLLLLLLll", val.user_id)
    #     else:
    #         return result
    #     # ravi at 5/4/2019 end
    @api.multi
    def get_total_list_view(self):
        obj_list = []
        emp_dict = {}
        result = {}
        emp_id = self._context.get("emp_id")
        user = self.env.user
        # print(emp_id, "employee")
        # ravi at 5/4/2019 start
        emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
        # ravi at 5/4/2019
        emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
        emp_dict.update({emp_id: {}})
        emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
        if emp_id_val:
            emp_dict.get(emp_id).update(emp_id_val)

        if user.has_group('purchase_extension.group_purchase_management'):
            flag = True
            pending_data = self.execute_query_for_management("total")
            for item in pending_data:
                obj_list.append(item.id)

        elif user.has_group('purchase_extension.group_product_category_wise_acces'):
            record_categ_wise = self.get_category_wise_record_list(self.name)
            flag = True
            # obj_list = self.get_obj_of_keys1(emp_dict, obj_list, record_categ_wise, flag)
            total_data = self.execute_query2("total",record_categ_wise)   #This is new line 21-11-2019
            for item in total_data:
                obj_list.append(item.id)
        else:
            obj_list = self.get_obj_of_keys(emp_dict, obj_list)
        if self.name:
            action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
            res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
            res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
            result = action[0].read()[0]
            result['views'] = [(res, 'list'), (res_form, 'form')]

        # # Trilok Changes 24-09-19 management check start
        # if user.has_group('purchase_extension.group_purchase_management'):
        #     if self.name == 'purchase.order':
        #         po_ids1=[]
        #         po_ids = self.env['purchase.order'].search([('id','>',0),('company_id','=',self.env.user.company_id.id)])
        #         if len(po_ids)>0:
        #             po_ids1 =po_ids._ids
        #         result['domain'] = [('id', 'in', po_ids1)]
        #     elif self.name == 'request.for.quotation':
        #         rfq_ids1 = []
        #         rfq_ids = self.env['request.for.quotation'].search(
        #             [('id', '>', 0), ('company_id', '=', self.env.user.company_id.id)])
        #         if len(rfq_ids) > 0:
        #             rfq_ids1 = rfq_ids._ids
        #         result['domain'] = [('id', 'in', rfq_ids1)]
        #     elif self.name == 'purchase.req':
        #         pr_ids1 = []
        #         pr_ids = self.env['purchase.req'].search(
        #             [('id', '>', 0), ('company_id', '=', self.env.user.company_id.id)])
        #         if len(pr_ids) > 0:
        #             pr_ids1 = pr_ids._ids
        #         result['domain'] = [('id', 'in', pr_ids1)]
        #     elif self.name == 'supplier.quotation':
        #         sq_ids1 = []
        #         sq_ids = self.env['supplier.quotation'].search(
        #             [('id', '>', 0), ('company_id', '=', self.env.user.company_id.id)])
        #         if len(sq_ids) > 0:
        #             sq_ids1 = sq_ids._ids
        #         result['domain'] = [('id', 'in', sq_ids1)]
        # else:
            result['domain'] = [('id', 'in', obj_list)]
            result['target'] = 'main'
            result["status"] = "total"
        # ravi at 5/4/2019 start
        # return result
        if (self.name == 'purchase.req'):
            if len(emp_id_user) <= 0:
                raise ValidationError(_('Please define employee for related user'))
                return 0
            else:
                return result
            # print("VALLLLLLLLLLll", val.user_id)
        else:
            return result
        # ravi at 5/4/2019 end

    def get_delay_obj_of_keys(self, emp_dict, obj_list):
        for key, val in emp_dict.items():
            objs = self.execute_query("pending", key)
            # if len(objs) > 0:
            for obj in objs:
                if obj.id:
                    obj_list.append(obj.id)
            # else:
            #     if objs[0].id:
            #         obj_list.append(objs[0].id)
            if val:
                obj_list = self.get_delay_obj_of_keys(val, obj_list)
        return obj_list

    @api.multi
    def get_require_date_list_view(self):
        obj_list = []
        result = {}
        emp_id = self._context.get("emp_id")
        user = self.env.user
        # ravi at 5/4/2019 start
        emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
        # ravi at 5/4/2019

        #Trilok starts here
        if self.env.user.has_group('purchase_extension.group_purchase_management'):
            objs = self.execute_query_for_management("pending")

        # elif user.has_group('purchase_extension.group_product_category_wise_acces'):
        #     record_category_wise = self.get_category_wise_record_list(self.name)
        #     flag = True
        #     objs = self.execute_query1('pending', emp_id, record_category_wise, flag)
        # #trilok ends here
        else:
            objs = self.execute_query("pending", emp_id)
        # objs = self.execute_query("pending", emp_id)
        min_require_date = None
        for cr_obj in objs:
            if not min_require_date:
                min_require_date = cr_obj.require_date
            if cr_obj.require_date:
                if cr_obj.require_date < min_require_date:
                    min_require_date = cr_obj.require_date
        if min_require_date:
            for obj in objs:
                if min_require_date == obj.require_date:
                    obj_list.append(obj.id)
        if self.name:
            action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
            res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
            res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
            result = action[0].read()[0]
            result['views'] = [(res, 'list'), (res_form, 'form')]
            result['domain'] = [('id', 'in', obj_list)]
            result['target'] = 'main'
            result["status"] = "pending"
        # ravi at 5/4/2019 start
        # return result
        if (self.name == 'pr.create.data'):
            if len(emp_id_user)<=0:
                raise ValidationError(_('Please define employee for related user'))
                return 0
            else:
                return result
            # print("VALLLLLLLLLLll", val.user_id)
        else:
            return result
        # ravi at 5/4/2019 end

    @api.multi
    def get_pending_list_view(self):
        obj_list = []
        emp_dict = {}
        result = {}
        #Trilok Starts here
        emp_id_user = ()
        flag = False
        emp_id = self._context.get("emp_id")
        user = self.env.user
        if user.has_group('purchase_extension.group_purchase_management'):
            flag =True
            pending_data = self.execute_query_for_management("pending")
            for item in pending_data:
                obj_list.append(item.id)

        elif user.has_group('purchase_extension.group_product_category_wise_acces'):
            record_category_wise = self.get_category_wise_record_list(self.name)
            flag = True

            if str(self.name) == 'pr.create.data':
                emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
                pending = self.execute_query("pending", emp_id)
                # pending = self.execute_query1("pending", emp_id, record_category_wise, flag)
                for item in pending:
                    obj_list.append(item.id)

            pending_data = self.execute_query2("pending", record_category_wise) # This is the new section 21-11-2019
            for item in pending_data:
                obj_list.append(item.id)

            # emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
            # emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
            # emp_dict.update({emp_id: {}})
            # emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
            # if emp_id_val:
            #     emp_dict.get(emp_id).update(emp_id_val)
            # obj_list = self.get_delay_obj_of_keys1(emp_dict, obj_list,record_category_wise, flag)
          #Trilok ends here

        else:
            # ravi at 5/4/2019 start
            if str(self.name) == 'pr.create.data':
                emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
                pending = self.execute_query("pending", emp_id)
                for item in pending:
                    obj_list.append(item.id)
            else:
                emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
                # ravi at 5/4/2019
                emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
                emp_dict.update({emp_id: {}})
                emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
                if emp_id_val:
                    emp_dict.get(emp_id).update(emp_id_val)
                obj_list = self.get_delay_obj_of_keys(emp_dict, obj_list)

        # # shubham did on 30/8
        # if self.name =='supplier.quotation':
        #     company_id = self.env.user.company_id.id
        #     all_sq = self.env['supplier.quotation'].search([('id', '>', 0), ('company_id', '=', company_id)])
        #     if len(all_sq) > 0:
        #         action = self.env.ref('purchase_extension.action_rfq_report_view')
        #         result = action.read()[0]
        #         res = self.env.ref('purchase_extension.view_rfq_report_view_tree', False)
        #         res_form = self.env.ref('purchase_extension.view_request_for_quotation_form', False)
        #         # print ("KKKKKKKKKKKKKK",res,res.id)
        #         result['views'] = [(res and res.id or False, 'list')]
        #         result['target'] = 'main'
        #         result['domain'] = [('company_id', '=', company_id)]
        #
        # else:
        action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
        res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
        res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
        result = action[0].read()[0]
        result['views'] = [(res, 'list'), (res_form, 'form')]
        result['domain'] = [('id', 'in', obj_list)]
        result['target'] = 'main'
        result["status"] = "pending"
        # ravi at 5/4/2019 start
        # return result
        if flag:
            return result
        else:
            if (self.name == 'purchase.req' or self.name == 'pr.create.data'):
                if len(emp_id_user)<=0:
                    raise ValidationError(_('Please define employee for related user'))
                    return 0
                else:
                    return result
                # print("VALLLLLLLLLLll", val.user_id)
            else:
                return result
            # ravi at 5/4/2019 end
    #
    # @api.multi
    # def get_pending_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     # ravi at 5/4/2019 start
    #     emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
    #     # ravi at 5/4/2019
    #     emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #     emp_dict.update({emp_id: {}})
    #     emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #     if emp_id_val:
    #         emp_dict.get(emp_id).update(emp_id_val)
    #     obj_list = self.get_delay_obj_of_keys(emp_dict, obj_list)
    #
    #     # shubham did on 30/8
    #     if self.name == 'supplier.quotation':
    #         company_id = self.env.user.company_id.id
    #         all_sq = self.env['supplier.quotation'].search([('id', '>', 0), ('company_id', '=', company_id)])
    #         if len(all_sq) > 0:
    #             action = self.env.ref('purchase_extension.action_rfq_report_view')
    #             result = action.read()[0]
    #             res = self.env.ref('purchase_extension.view_rfq_report_view_tree', False)
    #             res_form = self.env.ref('purchase_extension.view_request_for_quotation_form', False)
    #             # print ("KKKKKKKKKKKKKK",res,res.id)
    #             result['views'] = [(res and res.id or False, 'list')]
    #             result['target'] = 'main'
    #             result['domain'] = [('company_id', '=', company_id)]
    #
    #     else:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', obj_list)]
    #         result['target'] = 'main'
    #         result["status"] = "pending"
    #     # ravi at 5/4/2019 start
    #     # return result
    #     if (self.name == 'purchase.req' or self.name == 'pr.create.data'):
    #         if len(emp_id_user) <= 0:
    #             raise ValidationError(_('Please define employee for related user'))
    #             return 0
    #         else:
    #             return result
    #         # print("VALLLLLLLLLLll", val.user_id)
    #     else:
    #         return result
    #     # ravi at 5/4/2019 end

    @api.multi
    def change_view_type(self):
        self.view_type = self._context.get("view_type")

    #Trilok start 21-11-19
    def get_category_wise_record_list(self,model_name):
        categ_wise_record = []
        flag = True
        if str(model_name) == 'purchase.req':
            categ_wise_record = self.env.user.get_pr_domain(flag)

        elif  str(model_name) == 'purchase.order':
            categ_wise_record = self.env.user.get_po_domain(flag)

        elif str(model_name) == 'request.for.quotation':
            categ_wise_record = self.env.user.get_rfq_domain(flag)

        elif str(model_name) == 'supplier.quotation':
            categ_wise_record = self.env.user.get_sq_domain(flag)

        elif str(model_name) == 'purchase.requisition':
            categ_wise_record = self.env.user.get_agreement_domain(flag)

        elif str(model_name) == 'purchase.requisition.amd':
            categ_wise_record = self.env.user.get_ammendmend_domain(flag)

        elif str(model_name) == 'material.req.slip':
            pass

        return categ_wise_record

    def categ_wise_record_fun1(self, record, record_category_wise):
        if str(record.name) == 'pr.create.data':
            print("The model that we have", record.name)
            pending_cr = record.execute_query_for_management("pending")
            print("this is the model", pending_cr)
            min_require_date = None
            for cr_obj in pending_cr:
                if cr_obj.require_date:
                    if not min_require_date:
                        min_require_date = cr_obj.require_date
                    if cr_obj.require_date < min_require_date:
                        min_require_date = cr_obj.require_date
            if min_require_date:
                min_require_date = min_require_date.split()[0]
                record.sudo().write({"require_date": min_require_date, "pending": len(pending_cr)})
            if len(pending_cr) == 0:
                record.write({"color": 10})
            else:
                record.write({"color": 9})

        elif str(record.name) == 'kpi.matrix':
            total_record = record.execute_query_for_management('kpi')
            if total_record:
                record.write({
                    "inactive_item": total_record[0].inactive_items,
                    "inactive_vendor": total_record[0].inactive_vendor,
                    'supplier_without_email': total_record[0].supplier_dont_have_email,
                    'items_without_hsn': total_record[0].item_not_linked_with_hsn})

        elif str(record.name) == 'purchase.requisition':
            total_record = []
            total_record = record.execute_query2("total", record_category_wise)
            print("the requisition data is", total_record)
            deadline_date = []
            for agreement in total_record:
                deadline_date.append(agreement.date_end)
            current_date = datetime.datetime.today()
            after_two_months = current_date + relativedelta(months=2)
            expire = 0
            for date in deadline_date:
                if datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S') >= current_date and datetime.datetime.strptime(
                        date, '%Y-%m-%d %H:%M:%S') < after_two_months:
                    expire += 1
            total_values = []
            for record in total_record:
                po_list = []
                if record.type_id.type == 'arc':
                    po_list.append(record.purchase_ids)
                for po in po_list:
                    for purchase in po:
                        if purchase.state in ('purchase', 'done'):
                            total_values.append(purchase.amount_total)

            exhaust_value = sum(total_values)

            print("the len(total_record)", len(total_record))
            print("the expire", expire)
            print("the exhaust_value", exhaust_value)

            record.env.cr.execute(
                'update purchase_extension_dashboard set total=%s , '
                'expire_in_two_month=%s,exhaust_commitment_value=%s where id=%s'
                % (len(total_record), expire, exhaust_value, record.id))

            # record.sudo().write(
            # {"total": len(total_record),
            # 'expire_in_two_month': expire,
            # 'exhaust_commitment_value': exhaust_value})

            # record.sudo().update(
            # {
            # 'total': len(total_record),
            # 'expire_in_two_month': expire,
            # 'exhaust_commitment_value': exhaust_value
            # })

        elif str(record.name) == 'purchase.requisition.amd':
            total_record = []
            total_record = record.record.execute_query2("total", record_category_wise)
            modified_date = []
            for agreement in total_record:
                modified_date.append(agreement.write_date)

            current_date = datetime.datetime.today()
            from_last_months = current_date + relativedelta(months=-1)
            modified = 0
            for date in modified_date:
                if datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S') <= current_date and datetime.datetime.strptime(
                        date, '%Y-%m-%d %H:%M:%S') > from_last_months:
                    modified += 1
            print("the modified_date is", modified_date)
            print("the modified_date is", current_date)
            print("the modified_date is", from_last_months)
            print("the modified_count is", modified)
            record.sudo().write({"total": len(total_record), 'modified_in_last_month': expire})

        else:
            cancelled_data = []
            rfq_not_sent_data = []
            email_not_sent_data = []
            total_data = record.execute_query2("total", record_category_wise)
            pending_data = record.execute_query2("pending", record_category_wise)
            if str(record.name) == 'purchase.order' or str(record.name) == 'purchase.req':
                cancelled_data = record.execute_query2("cancelled", record_category_wise)
            if str(record.name) == 'request.for.quotation':
                rfq_not_sent_data = record.execute_query2("confirm", record_category_wise)
            if str(record.name) == 'purchase.order':
                email_not_sent_data = record.execute_query2("unsent", record_category_wise)
            record.sudo().write(
                {"total": len(total_data), "pending": len(pending_data), 'cancelled': len(cancelled_data),
                 'rfq_not_sent': len(rfq_not_sent_data), 'email_not_sent': len(email_not_sent_data)})
            if len(pending_data) == 0:
                record.write({"color": 10})
            else:
                record.write({"color": 9})

    def execute_query2(self, label_name, record_category_wise):
        list_query_obj = []
        list_query_obj1 = []

        try:
            query = self.env["purchase.extension.dashboard.query"].search([("model_name", "=", str(self.name)),
                                                                           ("label_name", "=", label_name)]).query
            company_id = self.env.user.company_id.id
            print("qyueryyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy", query)
            if query:
                if label_name == 'total' and str(self.name) != 'pr.create.data' and str(self.name) != 'kpi.matrix':
                    if str(self.name) == 'material.req.slip':
                        query = str(query) + " where type = 'indent' and company_id=" + str(company_id)
                    else:
                        query = str(query) + " where company_id=" + str(company_id)
                elif label_name == 'pending' and str(self.name) != 'pr.create.data' and str(
                        self.name) != 'material.req.slip' and str(self.name) != 'kpi.matrix':
                    query = str(query) + " and company_id=" + str(company_id)
                elif label_name == 'pending' and str(self.name) == 'pr.create.data':
                    query = str(query) + " where company_id=" + str(company_id) + ")"
                    print("the final query is ", query)
                elif label_name == 'cancelled' and (str(self.name) == 'purchase.order' or str(self.name) == 'purchase_req'):
                    query = str(query) + " and company_id = " + str(company_id)

                elif label_name == 'confirm' and str(self.name) == 'request.for.quotation':
                    query = str(query) + " and company_id=" + str(company_id)

                elif label_name == 'unsent' and str(self.name) == 'purchase.order':
                    query = str(query) + " and company_id=" + str(company_id)
                # elif label_name == 'kip' and str(self.name) == 'kip.matrix':
                #     query = str(query) + " where company_id=" + str(company_id)

                self.env.cr.execute(query)
                list_query_dict = self.env.cr.dictfetchall()
                for query_dict in list_query_dict:
                    list_query_obj1.append(self.env[self.name].search([("id", "=", query_dict["id"])]))
                for obj in list_query_obj1:
                    if obj.id in record_category_wise:
                        list_query_obj.append(obj)
        except:
            list_query_obj = []

        # print("the record in categorywise is ", record_category_wise, len(record_category_wise))
        # print("the record in in query is   ", list_query_obj, len(list_query_obj))
        # print("the record in in listqueryobject1111 is   ", list_query_obj1, len(list_query_obj1))
        return list_query_obj

    @api.multi
    def get_cancelled_list_view(self):
        obj_list = []
        emp_dict = {}
        result = {}
        emp_id_user = ()
        flag = False
        emp_id = self._context.get("emp_id")
        user = self.env.user
        if user.has_group('purchase_extension.group_purchase_management'):
            flag = True
            pending_data = self.execute_query_for_management("cancelled")
            for item in pending_data:
                obj_list.append(item.id)

        elif user.has_group('purchase_extension.group_product_category_wise_acces'):
            record_category_wise = self.get_category_wise_record_list(self.name)
            flag = True
            pending_data = self.execute_query2("cancelled", record_category_wise)  # This is the new section 21-11-2019
            for item in pending_data:
                obj_list.append(item.id)

        else:
            emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
            emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
            emp_dict.update({emp_id: {}})
            emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
            if emp_id_val:
                emp_dict.get(emp_id).update(emp_id_val)
            obj_list = self.get_cancelled_obj_of_keys(emp_dict, obj_list)

        action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
        res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
        res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
        result = action[0].read()[0]
        result['views'] = [(res, 'list'), (res_form, 'form')]
        result['domain'] = [('id', 'in', obj_list)]
        result['target'] = 'main'
        result["status"] = "cancelled"
        if flag:
            return result
        else:
            if self.name == 'purchase.req':
                if len(emp_id_user) <= 0:
                    raise ValidationError(_('Please define employee for related user'))
                    return 0
                else:
                    return result
            else:
                return result

    def get_cancelled_obj_of_keys(self, emp_dict, obj_list):
        for key, val in emp_dict.items():
            objs = self.execute_query("cancelled", key)
            for obj in objs:
                if obj.id:
                    obj_list.append(obj.id)
            if val:
                obj_list = self.get_cancelled_obj_of_keys(val, obj_list)
        return obj_list

    @api.multi
    def get_unsent_list_view(self):
        obj_list = []
        emp_dict = {}
        result = {}
        emp_id_user = ()
        flag = False
        emp_id = self._context.get("emp_id")
        user = self.env.user
        if user.has_group('purchase_extension.group_purchase_management'):
            flag = True
            if str(self.name) == 'purchase.order':
                pending_data = self.execute_query_for_management("unsent")
            else:
                pending_data = self.execute_query_for_management("confirm")
            for item in pending_data:
                obj_list.append(item.id)

        elif user.has_group('purchase_extension.group_product_category_wise_acces'):
            record_category_wise = self.get_category_wise_record_list(self.name)
            flag = True
            if str(self.name) == 'purchase.order':
                pending_data = self.execute_query2("unsent", record_category_wise)  # This is the new section 21-11-2019
            else:
                pending_data = self.execute_query2("confirm", record_category_wise)
            for item in pending_data:
                obj_list.append(item.id)

        else:
            emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
            emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
            emp_dict.update({emp_id: {}})
            emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
            if emp_id_val:
                emp_dict.get(emp_id).update(emp_id_val)
            if str(self.name) == 'purchase.order':
                obj_list = self.get_unsent_obj_of_keys(emp_dict, obj_list)
            else:
                obj_list = self.get_confirm_obj_of_keys(emp_dict, obj_list)

        action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
        res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
        res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
        result = action[0].read()[0]
        result['views'] = [(res, 'list'), (res_form, 'form')]
        result['domain'] = [('id', 'in', obj_list)]
        result['target'] = 'main'
        result["status"] = "cancelled"
        if flag:
            return result
        else:
            if self.name == 'purchase.req':
                if len(emp_id_user) <= 0:
                    raise ValidationError(_('Please define employee for related user'))
                    return 0
                else:
                    return result
            else:
                return result

    def get_unsent_obj_of_keys(self, emp_dict, obj_list):
        for key, val in emp_dict.items():
            objs = self.execute_query("unsent", key)
            for obj in objs:
                if obj.id:
                    obj_list.append(obj.id)
            if val:
                obj_list = self.get_unsent_obj_of_keys(val, obj_list)
        return obj_list

    def get_confirm_obj_of_keys(self, emp_dict, obj_list):
        for key, val in emp_dict.items():
            objs = self.execute_query("confirm", key)
            for obj in objs:
                if obj.id:
                    obj_list.append(obj.id)
            if val:
                obj_list = self.get_confirm_obj_of_keys(val, obj_list)
        return obj_list


    # Trilok start 26-09-19
    def categ_wise_record_fun(self, record, record_category_wise):
        emp_dict = {}
        emp_total = {}
        query = """select * from res_groups_users_rel where gid in (select id from res_groups where 
                                   category_id in (select id from ir_module_category where name ilike 'Purchases')) and uid=%s""" % (
            self.env.user.id)
        record.env.cr.execute(query)
        condition_satisfied = record.env.cr.fetchall()
        if condition_satisfied:
            # for val in condition_satisfied:
        # for group in record.env.user.groups_id:
        #     if group:
        #         # if group.name == "User" or group.name == "Manager":
        #         if group.category_id.name == "Purchases":
            user_wise_list = []
            have_child = False
            if record.name:
                emp_id = record.env["hr.employee"].search([("user_id", "=", record.env.user.id)]).id
                if emp_id:
                    if str(record.name) == 'pr.create.data':
                        # pending_cr=[]
                        pending_cr = record.execute_query("pending", emp_id)
                        min_require_date = None
                        # for cr_obj in pending_cr:
                        #     if cr_obj.id in record_category_wise:
                        #         pending_cr.append(cr_obj)
                        if pending_cr:
                            for cr_obj in pending_cr:
                                    if cr_obj.require_date:
                                        if not min_require_date:
                                            min_require_date = cr_obj.require_date
                                        if cr_obj.require_date < min_require_date:
                                            min_require_date = cr_obj.require_date
                        if min_require_date:
                            min_require_date = min_require_date.split()[0]
                            record.sudo().write({"require_date": min_require_date, "pending": len(pending_cr),
                                                 "have_child": have_child, "emp_id": emp_id})
                        else:
                            record.sudo().write({"require_date": min_require_date, "pending": len(pending_cr),
                                                 "have_child": have_child, "emp_id": emp_id})
                        if len(pending_cr) == 0:
                            record.write({"color": 10})
                        else:
                            record.write({"color": 9})
                    else:
                        emp_objs = record.env["hr.employee"].search([("parent_id", "=", emp_id)])
                        if len(emp_objs) > 0:
                            have_child = True
                        emp_dict.update({emp_id: {}})
                        emp_id_val = record.get_employee_child(emp_objs, emp_dict.get(emp_id))
                        if emp_id_val:
                            emp_dict.get(emp_id).update(emp_id_val)
                        emp_total = record.get_list_of_keys(emp_dict, emp_total, 1, categ_dict =record_category_wise, categ_status =True)
                        emp_string = str(emp_dict)
                        sequence_list = []
                        for s in re.split("{|:|}|,| ", emp_string):
                            if s.isdigit():
                                sequence_list.append(int(s))
                        emp_total_sequence = []
                        for i in sequence_list:
                            for key, val in emp_total.items():
                                if i == key:
                                    emp_total_sequence.append([key, val])
                        for element in emp_total_sequence:
                            if emp_id == element[0]:
                                total = element[1].get("total")
                                pending = element[1].get("pending")
                                record.sudo().write({"total": total, "pending": pending,"have_child": have_child, "emp_id": emp_id})
                                if pending == 0:
                                    record.write({"color": 10})
                                else:
                                    record.write({"color": 9})
                            user_wise = (0, False, {
                                "emp_id": element[0],
                                "emp_name": record.env["hr.employee"].search([("id", "=", element[0])]).name,
                                "user_wise_total": element[1].get("total"),
                                "user_wise_pending": element[1].get("pending"),
                                "level": str(element[1].get('level')),
                            })
                            user_wise_list.append(user_wise)
                        line_obj = record.env["purchase.extension.dashboard.user.wise"].search(
                            [("purchase_ext_dashboard_id", "=", record.id)])
                        if len(line_obj) > 0:

                            if len(line_obj) == len(user_wise_list):
                                for i, line in enumerate(line_obj):
                                    line.sudo().write(user_wise_list[i][2])
                            elif len(line_obj) > len(user_wise_list):
                                for i, line in enumerate(line_obj):
                                    try:
                                        line.sudo().write(user_wise_list[i][2])
                                    except:
                                        query = "delete from purchase_extension_dashboard_user_wise where id =" + str(
                                            line.id)
                                        record.env.cr.execute(query)
                            elif len(line_obj) < len(user_wise_list):
                                a = 0
                                list_of_new_users = []
                                for i, line in enumerate(line_obj):
                                    line.sudo().write(user_wise_list[i][2])
                                    a = i
                                for j, user in enumerate(user_wise_list):
                                    if j > a:
                                        list_of_new_users.append(user)
                                record.sudo().write({"user_wise_id": list_of_new_users})
                        else:
                            record.sudo().write({"user_wise_id": user_wise_list})
                else:
                    record.write({"active": False})

    def execute_query1(self, label_name, emp_id, record_category_wise, categ_status):
        list_query_obj = []
        list_query_obj1 = []
        try:
            user_id = self.env["hr.employee"].search([("id", "=", emp_id)]).user_id[0]
            query = self.env["purchase.extension.dashboard.query"].search([("model_name", "=", str(self.name)),
                                                                           ("label_name", "=", label_name)]).query
            company_id = self.env.user.company_id.id
            if query:
                if label_name == 'total' and str(self.name) != 'pr.create.data':
                    query = str(query) + " where company_id=" + str(company_id) + " and create_uid=" + str(user_id.id)
                elif label_name == 'pending' and str(self.name) != 'pr.create.data':
                    query = str(query) + " and company_id=" + str(company_id) + " and create_uid=" + str(user_id.id)
                elif label_name == 'pending' and str(self.name) == 'pr.create.data':
                    query = str(query) + " where company_id=" + str(company_id) + " and create_uid=" + str(
                        user_id.id) + ")"
                self.env.cr.execute(query)
                # print("qyueryyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy", query)
                list_query_dict = self.env.cr.dictfetchall()
                for query_dict in list_query_dict:
                    list_query_obj1.append(self.env[self.name].search([("id", "=", query_dict["id"])]))
                for obj in list_query_obj1:
                    if obj.id in record_category_wise:
                        list_query_obj.append(obj)
        except:
            list_query_obj = []
        return list_query_obj

    def get_total1(self, emp_dict, categ_list_data, categ_status_check):
        val_user_dict1 = {
            "total": 0,
            "pending": 0,
        }
        for key, val in emp_dict.items():
            if categ_list_data and categ_status_check:
                val_user_dict = {
                    "total": len(self.execute_query1("total", key, categ_list_data, categ_status_check)),
                    "pending": len(self.execute_query1("pending", key, categ_list_data, categ_status_check)),
                }
            if val:
                val_user_dict2 = self.get_total(val)
                val_user_dict["total"] = int(val_user_dict["total"]) + int(val_user_dict2["total"])
                val_user_dict["pending"] = int(val_user_dict["pending"]) + int(val_user_dict2["pending"])
            if not val_user_dict["total"]:
                val_user_dict["total"] = 0
            if not val_user_dict["pending"]:
                val_user_dict["pending"] = 0
            val_user_dict1["total"] = int(val_user_dict1["total"]) + int(val_user_dict["total"])
            val_user_dict1["pending"] = int(val_user_dict1["pending"]) + int(val_user_dict["pending"])
        return val_user_dict1

    def get_delay_obj_of_keys1(self, emp_dict, obj_list,record_categ_wise, flag):
        for key, val in emp_dict.items():
            if record_categ_wise and flag:
                objs = self.execute_query1("pending", key, record_categ_wise, flag)
            # if len(objs) > 0:
                if objs:
                    for obj in objs:
                        if obj.id:
                            obj_list.append(obj.id)
                    # else:
                    #     if objs[0].id:
                    #         obj_list.append(objs[0].id)
                    if val:
                        obj_list = self.get_delay_obj_of_keys1(val, obj_list, record_categ_wise, flag)
        return obj_list

    def get_obj_of_keys1(self, emp_dict, obj_list, record_categ_wise, flag):
        for key, val in emp_dict.items():
            if record_categ_wise and flag:
                objs = self.execute_query1('total', key, record_categ_wise, flag)
            for obj in objs:
                if obj.id:
                    obj_list.append(obj.id)
            if val:
                if record_categ_wise and flag:
                    obj_list = self.get_obj_of_keys1(val, obj_list, record_categ_wise, flag)
        return obj_list
    #Trilok Ends here

    def management_hierarchy_level(self,record):
        emp_dict = {}
        emp_total = {}
        query="""select login, usr.id as user_id, grp.id group_id, grp.name, cat.name
        from res_users usr, res_groups_users_rel rel, res_groups grp, ir_module_category cat
        where usr.id = rel.uid
        and rel.gid = grp.id
        and grp.category_id = cat.id
        and cat.name = 'Purchases'
        and grp.name = 'Manager' and usr.id not in
        (select usr.id
        from res_users usr, res_groups_users_rel rel, res_groups grp, ir_module_category cat
        where usr.id = rel.uid
        and rel.gid = grp.id
        and grp.category_id = cat.id
        and cat.name = 'Purchases'
        and grp.name = 'Management') ; """
        record.env.cr.execute(query)
        objs = record.env.cr.dictfetchall()
        print("the value in the objs",objs)
        user_wise_list = []
        if objs[0]:
                emp_ids = record.env["hr.employee"].search([("user_id", "=", objs[0].get('user_id'))])
                if emp_ids:
                    emp_id = self.parent_of_emp(emp_ids)
                    # print("the value in emp_ids",emp_ids)
                    # print("the managet of employee is",emp_ids.parent_id)
                    have_child = True
                    # emp_dict.update({emp_id.id: {}})
                    emp_id_val = record.get_employee_child(emp_id, emp_dict)
                    # print ("the vlue hhhhhhhhhhhhhhhhhhhhhhhhhh",emp_id_val,emp_id.id)
                    if emp_id_val:
                        # print ("ifffffffffffffffffffffff")
                        emp_dict.get(emp_id).update(emp_id_val)
                    # print ("em dictttttttttttt111111111")
                    emp_total = record.get_list_of_keys(emp_dict, emp_total, 1,categ_status=True)
                    # print ("em 2222222222")
                    emp_string = str(emp_dict)
                    sequence_list = []
                    for s in re.split("{|:|}|,| ", emp_string):
                        if s.isdigit():
                            sequence_list.append(int(s))
                    emp_total_sequence = []
                    for i in sequence_list:
                        for key, val in emp_total.items():
                            # print ("i and keyyyyyyyyyyy",i,key,val)
                            if i == key:
                                emp_total_sequence.append([key, val])
                    print("the value in emp_total_sequence", emp_total_sequence)

                    for element in emp_total_sequence:
                        # print("the value in the emlenttttttttttttttttttttttt", element[0])
                        if emp_id.id == element[0]:
                            total = element[1].get("total")
                            pending = element[1].get("pending")
                            # print("empidddddddddddddd", emp_id.id)
                            record.sudo().write(
                                {"total": total, "pending": pending, "have_child": have_child, "emp_id": emp_id.id})
                            if pending == 0:
                                record.write({"color": 10})
                            else:
                                record.write({"color": 9})
                        # print("the value in the emlenttttttttttttttttttttttt",element[0])
                        # emp_ids = self.env['hr.employee'].browse(element[0])
                        # print ("emp idsssssssssssss",emp_ids,emp_ids.name)
                        # print(record.env["hr.employee"].search([('id', "=", element[0])]).name)
                        user_wise = (0, False, {
                            "emp_id": element[0],
                            "emp_name": record.env["hr.employee"].search([('id', "=", element[0])]).name,
                            # "emp_name":emp_ids.name,
                            "user_wise_total": element[1].get("total"),
                            "user_wise_pending": element[1].get("pending"),
                            "level": str(element[1].get('level')),
                        })
                        user_wise_list.append(user_wise)
                        print("the value in user_wise_list",user_wise_list)
                        print("the value in emp_dict",emp_dict)
                        print("the value in emp_total",emp_total)
                        # print (a)

                    line_obj = record.env["purchase.extension.dashboard.user.wise"].search(
                        [("purchase_ext_dashboard_id", "=", record.id)])
                    if len(line_obj) > 0:
                        # print ("botgh ;lennnnnnnnnnnnn")
                        if len(line_obj) == len(user_wise_list):
                            for i, line in enumerate(line_obj):
                                line.sudo().write(user_wise_list[i][2])
                        elif len(line_obj) > len(user_wise_list):
                            for i, line in enumerate(line_obj):
                                try:
                                    line.sudo().write(user_wise_list[i][2])
                                except:
                                    query = "delete from purchase_extension_dashboard_user_wise where id =" + str(
                                        line.id)
                                    record.env.cr.execute(query)
                        elif len(line_obj) < len(user_wise_list):
                            a = 0
                            list_of_new_users = []
                            for i, line in enumerate(line_obj):
                                line.sudo().write(user_wise_list[i][2])
                                a = i
                            for j, user in enumerate(user_wise_list):
                                # print ("a and jjjjjjjjj",a,j)
                                # if a > j:
                                if j > a:
                                    list_of_new_users.append(user)
                            # print ("recordddddddddddddddd",record)
                            # print ("user wise listttttttttt",user_wise_list)
                            # print (" list of new userrrrrrrrrrr",list_of_new_users)
                            record.sudo().write({"user_wise_id": list_of_new_users})
                    else:
                        record.sudo().write({"user_wise_id": user_wise_list})
                else:
                    record.write({"active": False})

    def parent_of_emp(self,emp):
        emp_id1 = emp.parent_id
        if emp_id1:
            emp_ids = self.env["hr.employee"].search([("id", "=", emp_id1.id)])
            emp_id2 = emp_ids.parent_id
            if emp_id2:
                emp_id3=self.parent_of_emp(emp_id2)
                return emp_id3

            else:
                return emp_ids
        return emp

    def po_amendment(self):
        pass

    def po_agreement(self):
        pass

    def quotation_comparison(self):
        pass

    def inactive_items(self):
        inactive_items = 0
        company_id = self.env.user.company_id.id
        query = 'select count(*) from product_template where company_id=%s and active = %s' % (company_id,False)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            inactive_items = result[0]['count']
        return inactive_items

    def inactive_vendors(self):
        inactive_vendors = 0
        company_id = self.env.user.company_id.id
        query = "select count(*) from res_partner where active = %s and company_id = %s and supplier=%s" %(False, company_id, True)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            inactive_vendors = result[0]['count']
        return inactive_vendors

    def not_having_mail_id(self):
        not_mail = 0
        company_id = self.env.user.company_id.id
        query = "select count(*) from res_partner where email_not_exist = %s and company_id = %s and supplier=%s" %(False, company_id, True)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            not_mail = result[0]['count']
        return not_mail

    def items_not_linked_with_hsn(self):
        items_not_with_hsn = 0
        company_id = self.env.user.company_id.id
        query = 'select count(*) from product_template where company_id= %s and hsn_id is null' %(company_id)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            items_not_with_hsn = result[0]['count']
        return items_not_with_hsn

    def data_from_kpi(self):
        inactive_items = self.inactive_items()
        inactive_vendor = self.inactive_vendors()
        without_email = self.not_having_mail_id()
        without_hsn = self.items_not_linked_with_hsn()

        names = self.env["kpi.matrix"].search([("id", ">", 0)])
        print("The print in the names ",names)
        if names:
            names.write({"name": 'kpi', "inactive_items": inactive_items,
                                                             "inactive_vendor": inactive_vendor, 'supplier_dont_have_email': without_email, 'item_not_linked_with_hsn': without_hsn})
        else:
            self.env['kpi.matrix'].sudo().create({"name": 'kpi', "inactive_items": inactive_items,
                                                             "inactive_vendor": inactive_vendor, 'supplier_dont_have_email': without_email, 'item_not_linked_with_hsn': without_hsn})
        print("creation Successfully")



class PurchaseExtensionDashboardQuery(models.Model):
    _description = "Query Detail"
    _name = "purchase.extension.dashboard.query"

    model_name = fields.Char("Model Name")
    # type = fields.Selection([
    #     ('activity_wise', 'Activity Wise'),
    #     ('user_wise', 'User Wise')
    # ], string="type")
    label_name = fields.Char("Label Name")
    query = fields.Text("Query")


class PurchaseExtensionDashboardUserWise(models.Model):
    _description = "User Detail"
    _name = "purchase.extension.dashboard.user.wise"

    emp_name = fields.Char("Name")
    emp_id = fields.Integer("employee id")
    user_wise_total = fields.Integer()
    user_wise_pending = fields.Integer()
    level = fields.Integer()
    purchase_ext_dashboard_id = fields.Many2one('purchase.extension.dashboard', 'Purchase dashboard')
    active=fields.Boolean('Active',default=True)

    @api.model
    def create(self, values):
        res = super(PurchaseExtensionDashboardUserWise, self).create(values)

        return res


class PurchaseExtensionDashboardUser(models.Model):
    _name = "res.users"
    _inherit = "res.users"

    @api.model
    def create(self, values):
        model_names = []
        # print("new user")
        res = super(PurchaseExtensionDashboardUser, self).create(values)
        names = self.env["purchase.extension.dashboard.query"].search([("id", ">", 0)])
        for name in names:
            model_names.append(name.model_name)
        model_names = set(model_names)
        for company in res.company_ids:
            for name in model_names:
                # print(res.id, name, "user and name")

                self.env['purchase.extension.dashboard'].sudo().create({"name": name, "user_id": res.id,
                                                             "company_id": company.id})
        print("tethe model names",model_names)
        return res

    @api.multi
    def write(self, values):
        model_names = []
        if "company_ids" in values:
            # print(values.get("company_ids"), "companyssssssssssss")
            if values.get("company_ids")[0][2]:
                for company_id in values.get("company_ids")[0][2]:
                    dashboard = self.env['purchase.extension.dashboard'].search([("user_id","=", self.id), ("company_id","=", company_id)])
                    if len(dashboard) == 0:
                        names = self.env["purchase.extension.dashboard.query"].search([("id", ">", 0)])
                        for name in names:
                            model_names.append(name.model_name)
                        model_names = set(model_names)
                        for name in model_names:
                            self.env['purchase.extension.dashboard'].sudo().create({"name": name, "user_id": self.id,
                                                                             "company_id": company_id})

        res = super(PurchaseExtensionDashboardUser, self).write(values)
        return res


class PurchaseExtensionDashboardEmployee(models.Model):
    _name = "hr.employee"
    _inherit = "hr.employee"

    user_id = fields.Many2one('res.users', 'User', related='resource_id.user_id', store=True)

    @api.multi
    @api.onchange("user_id")
    def onchange_code(self):
        # print(self.user_id.id, "uuuuussssssssssser", self.company_id.id)
        # print(self.user_id.company_id.id)
        if self.user_id.id and self.company_id.id:
            query = "select * from purchase_extension_dashboard where user_id =" + str(self.user_id.id)\
                    + "and company_id =" + str(self.company_id.id)
            self.env.cr.execute(query)
            dashboard = self.env.cr.dictfetchall()
            for record in dashboard:
                obj = self.env['purchase.extension.dashboard'].sudo().browse(record["id"])
                obj.write({"active": True})


class KPIMatrix(models.Model):
    _name = 'kpi.matrix'

    name = fields.Char("Name")
    inactive_items = fields.Integer("Inactive Items")
    inactive_vendor = fields.Integer("Inactive Vendor")
    supplier_dont_have_email = fields.Integer("Email Does Not Exist")
    item_not_linked_with_hsn = fields.Integer("Items Without HSN")
    company_id = fields.Many2one('res.company', 'Company', index=True,
                                 default=lambda self: self.env.user.company_id.id)








