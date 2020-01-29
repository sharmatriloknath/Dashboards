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


class PurchaseDynamicDashboard(models.Model):
    _description = "purchase Detail"
    _name = "purchase.dynamic.dashboard"

    active = fields.Boolean('Active', default=True, store=True)
    name = fields.Selection([
        ('material.req.slip', 'Purchase Indent'),
        ('purchase.req', 'Purchase Req'),
        ('purchase.order', 'Purchase Order'),
        ('request.for.quotation', 'Request For Quotation'),
        ('supplier.quotation', 'Supplier Quotation'),
        ('pr.create.data', 'Create PR'),
        ('purchase.requisition', 'Purchase Agreements'),
        ('purchase.requisition.amd', 'Purchase Amendment'),
        ('kpi.matrix', 'KPI Matrix')
    ], string="Name")
    computation = fields.Char(compute='_computation')
    total = fields.Integer("Total")
    user_id = fields.Many2one('res.users', 'User')
    company_id = fields.Many2one('res.company', 'Company')
    pending = fields.Integer("Pending")
    high_priority = fields.Integer("High Priority")
    color = fields.Integer('Color')
    view_type = fields.Boolean('Type', default=True)
    user_wise_id = fields.One2many("purchase.dynamic.dashboard.user.wise", "purchase_ext_dashboard_id")
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
    exhaust_commitment_value = fields.Integer("Exhaust Commitment Value", store = True)
    delay_total = fields.Integer("Delay Total", store = True)
    delay_pending = fields.Integer("Delay Pending", store = True)

    @api.multi
    def compute_by_scheduler(self):
        print("This is Executing-----------------------------------------------------")
        return {
            'type': 'ir.actions.window',
            'tag': 'reload',
        }

    @api.multi
    def _computation(self):
        model_used = []
        self.data_from_kpi()
        emp_dict = {}
        emp_total = {}
        for record in self:
            if record.name not in model_used:
                model_used.append(record.name)
                user_id1 = self._context.get("uid")
                user = self.env['res.users'].browse(user_id1)

                '''This code is for Management who can see all the records because he has complete access rights'''
                if user.has_group('purchase_extension.group_purchase_management'):

                    record.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s'" %(str(record.name)))
                    model_data = record.env.cr.dictfetchall()
                    if model_data:
                        complete_data = {}
                        for model in model_data:
                            if model['model_name'] == 'kpi.matrix':
                                total_record = record.execute_query_for_management_kpi(model)
                                print("the total record is",total_record)
                                if total_record:
                                    record.write({
                                        "inactive_item": total_record[0]['inactive_items'],
                                        "inactive_vendor": total_record[0]['inactive_vendor'],
                                        'supplier_without_email': total_record[0]['supplier_dont_have_email'],
                                        'items_without_hsn': total_record[0]['item_not_linked_with_hsn']})
                            else:
                                complete_data[model['label_name']] = (self.execute_management_query(model))
                                print("the total complete_data in the total ", complete_data.get('commitment'))

                            record.sudo().write(
                                {
                                    'total': len(complete_data.get('total', 0) if complete_data.get('total', 0) != 0 else []),
                                    'pending': len(complete_data.get('pending', 0) if complete_data.get('pending', 0) != 0 else []),
                                    'rfq_not_sent': len(complete_data.get('confirm', 0) if complete_data.get('confirm', 0) != 0 else []),
                                    'email_not_sent': len(complete_data.get('unsent', 0) if complete_data.get('unsent', 0) != 0 else []),
                                    'cancelled': len(complete_data.get('cancelled', 0) if complete_data.get('cancelled', 0) != 0 else []),
                                    'modified_in_last_month': len(complete_data.get('modified', 0) if complete_data.get('modified', 0) != 0 else []),
                                    'expire_in_two_month': len(complete_data.get('deadline', 0) if complete_data.get('deadline', 0) != 0 else []),
                                    # 'exhaust_commitment_value': complete_data.get('commitment')[0]['commitment'] if complete_data.get('commitment',0.0) !=0.0 else 0.0,
                                    'exhaust_commitment_value': len(complete_data.get('commitment', 0) if complete_data.get('commitment',0) != 0 else []),
                                    'require_date':complete_data.get('mindate')[0]['mindate'] if complete_data.get('mindate',None) !=None else None,
                                    'delay_total': len(complete_data.get('tdelay', 0) if complete_data.get('tdelay', 0) != 0 else []),
                                    'delay_pending': len(complete_data.get('pdelay', 0) if complete_data.get('pdelay', 0) != 0 else []),

                                }
                            )

                else:
                    if self.env.user.has_group('purchase_extension.group_product_category_wise_acces'):
                        record_category_wise = record.get_category_wise_record_list(record.name)
                        self.categ_wise_record_fun(record, record_category_wise)
                    else:
                        if record.user_id.id == self.env.user.id and record.company_id.id == record.env.user.company_id.id:
                            query = """select * from res_groups_users_rel where gid in (select id from res_groups where 
                                               category_id in (select id from ir_module_category where name ilike 'Purchases')) and uid=%s""" % (user.id)
                            record.env.cr.execute(query)
                            condition_satisfied = record.env.cr.fetchall()
                            if condition_satisfied:
                                user_wise_list = []
                                have_child = False
                                if record.name:
                                    if record.name == 'kpi.matrix':
                                        continue
                                    emp_id = record.env["hr.employee"].search([("user_id", "=", record.env.user.id)]).id
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
                                            unsent = element[1].get("unsent")
                                            confirm = element[1].get("confirm")
                                            cancelled = element[1].get("cancelled")
                                            modified = element[1].get("modified")
                                            deadline = element[1].get("deadline")
                                            tdelay = element[1].get("tdelay")
                                            pdelay = element[1].get("pdelay")
                                            # commitment = element[1].get("commitment")
                                            record.sudo().write(
                                                {"total": total, "pending": pending, "have_child": have_child,
                                                 "emp_id": emp_id, 'email_not_sent': unsent, 'rfq_not_sent': confirm, 'cancelled':cancelled,
                                                 'modified_in_last_month': modified,'expire_in_two_month': deadline, 'delay_total':tdelay, 'delay_pending':pdelay
                                                 })
                                            if pending == 0:
                                                record.write({"color": 10})
                                            else:
                                                record.write({"color": 9})

                                        user_wise = (0, False, {
                                            "emp_id": element[0],
                                            "emp_name": record.env["hr.employee"].search(
                                                [("id", "=", element[0])]).name,
                                            "user_wise_total": element[1].get("total"),
                                            "user_wise_pending": element[1].get("pending"),
                                            "level": str(element[1].get('level',0)),
                                        })
                                        user_wise_list.append(user_wise)
                                    line_obj = record.env["purchase.dynamic.dashboard.user.wise"].search(
                                        [("purchase_ext_dashboard_id", "=", record.id)])
                                    if len(line_obj) > 0:

                                        if len(line_obj) == len(user_wise_list):
                                            for i, line in enumerate(line_obj):
                                                print ("iiiiiiiiiiiiiiiiiiiiiiiiiii", i)
                                                print ("user_wise_listrrrrrr", user_wise_list)
                                                line.sudo().write(user_wise_list[i][2])
                                        elif len(line_obj) > len(user_wise_list):
                                            for i, line in enumerate(line_obj):
                                                try:
                                                    line.sudo().write(user_wise_list[i][2])
                                                except:
                                                    query = "delete from purchase_dynamic_dashboard_user_wise where id =" + str(
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

    def categ_wise_record_fun(self, record, record_category_wise):
        record.env.cr.execute(
            "select * from purchase_dynamic_dashboard_query where model_name='%s'" % (str(record.name)))
        model_data = record.env.cr.dictfetchall()
        if model_data:
            complete_data = {}
            for model in model_data:
                if model['model_name'] == 'kpi.matrix':
                    total_record = record.execute_query_for_management_kpi(model, record_category_wise)
                    print("the total record is", total_record)
                    if total_record:
                        record.write({
                            "inactive_item": total_record[0]['inactive_items'],
                            "inactive_vendor": total_record[0]['inactive_vendor'],
                            'supplier_without_email': total_record[0]['supplier_dont_have_email'],
                            'items_without_hsn': total_record[0]['item_not_linked_with_hsn']})
                else:
                    complete_data[model['label_name']] = (self.execute_management_query(model, record_category_wise))
                record.sudo().write(
                    {
                        'total': len(complete_data.get('total', 0) if complete_data.get('total', 0) != 0 else []),
                        'pending': len(complete_data.get('pending', 0) if complete_data.get('pending', 0) != 0 else []),
                        'confirm': len(complete_data.get('confirm', 0) if complete_data.get('confirm', 0) != 0 else []),
                        'cancelled': len(complete_data.get('cancelled', 0) if complete_data.get('cancelled', 0) != 0 else []),
                        'modified_in_last_month': len(complete_data.get('modified', 0) if complete_data.get('modified', 0) != 0 else []),
                        'expire_in_two_month': len(complete_data.get('deadline', 0) if complete_data.get('deadline', 0) != 0 else []),
                        # 'exhaust_commitment_value': complete_data.get('commitment', 0.0)[0]['commitment'] if complete_data.get('commitment', 0.0) != 0.0 else 0.0,
                        'exhaust_commitment_value': len(complete_data.get('commitment', 0) if complete_data.get('commitment', 0) != 0 else []),
                        'require_date': complete_data.get('mindate')[0]['mindate'] if complete_data.get('mindate',None) != None else None,
                        'delay_total': len(complete_data.get('tdelay', 0) if complete_data.get('tdelay', 0) != 0 else []),
                        'delay_pending': len(complete_data.get('pdelay', 0) if complete_data.get('pdelay', 0) != 0 else []),

                    }
                )

    @api.model
    def create_card_for_purchase_extension_user(self):
        model_names = []
        users = self.env["res.users"].search([("id", ">", 0)])
        names = self.env["purchase.dynamic.dashboard.query"].search([("id", ">", 0)])
        for name in names:
            model_names.append(name.model_name)
        model_names = set(model_names)
        for user in users:
            for company in user.company_ids:
                for name in model_names:
                    self.env['purchase.dynamic.dashboard'].create({"name": name, "user_id": user.id,
                                                                "company_id": company.id})

    def get_category_wise_record_list(self, model_name):
        categ_wise_record = []
        flag = True
        if str(model_name) == 'purchase.req':
            categ_wise_record = self.env.user.get_pr_domain(flag)

        elif str(model_name) == 'purchase.order':
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
            categ_wise_record = self.env.user.get_mrs_domain(flag)

        elif str(model_name) == 'pr.create.data':
            categ_wise_record = self.env.user.get_pr_data_domain(flag)

        return categ_wise_record

    def execute_management_query(self, query_model, categ_wise=False, emp_id=False, view_type=True):
        list_obj = []
        list_query_dict = {}
        company_id = self.env.user.company_id.id
        if view_type:
            query = str(query_model["query"]) + str(company_id)
        else:
            user_id = self.env["hr.employee"].search([("id", "=", emp_id)]).user_id[0]
            query = str(query_model["query"]) + str(company_id) + " and create_uid=" + str(user_id.id)
        self.env.cr.execute(query)
        list_query_dict = self.env.cr.dictfetchall()
        if list_query_dict:
            if categ_wise:
                # print(a)
                for list_query in list_query_dict:
                    # if list_query.get('id',)
                    if 'id' in list_query:
                        if list_query['id'] in categ_wise:
                            list_obj.append(list_query)
                    else:
                        list_obj.append(list_query)
                return list_obj
        return list_query_dict

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

    # def get_list_of_keys(self, emp_dict, emp_total, level):
    #     for key, val in emp_dict.items():
    #         total = len(self.execute_query("total", key))
    #         pending = len(self.execute_query("pending", key))
    #
    #         if not total:
    #             total = 0
    #         if not pending:
    #             pending = 0
    #         emp_total.update({key: {"total": total, "pending": pending, "level": level}})
    #         if val:
    #             val_dict = self.get_total(val)
    #             emp_total = self.get_list_of_keys(val, emp_total, level+1)
    #             if not val_dict["total"]:
    #                 val_dict["total"] = 0
    #             if not val_dict["pending"]:
    #                 val_dict["pending"] = 0
    #             emp_total.update({key: {"total": total + val_dict["total"], "pending": pending + val_dict["pending"],
    #                               "level": level}})
    #     return emp_total

    def get_list_of_keys(self, emp_dict, emp_total, level):

        # print("get list of keysssssssssssssssssssssssssss", level)
        for key, val in emp_dict.items():
            self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s'" % (str(self.name)))
            model_data = self.env.cr.dictfetchall()
            if model_data:
                complete_data = {}
                for model in model_data:
                    complete_data[model['label_name']] = self.execute_query_user(model, key)
                # print("the commitm value dict isn the modle is",complete_data.get('commitment'))

                total = len(complete_data.get('total', 0) if complete_data.get('total', 0) != 0 else [])
                pending = len(complete_data.get('pending', 0) if complete_data.get('pending', 0) != 0 else [])
                confirm = len(complete_data.get('confirm', 0) if complete_data.get('confirm', 0) != 0 else [])
                cancelled = len(complete_data.get('cancelled', 0) if complete_data.get('cancelled', 0) != 0 else [])
                unsent = len(complete_data.get('unsent', 0) if complete_data.get('unsent', 0) != 0 else [])
                modified = len(complete_data.get('modified', 0) if complete_data.get('modified', 0) != 0 else [])
                deadline = len(complete_data.get('deadline', 0) if complete_data.get('deadline', 0) != 0 else [])
                tdelay = len(complete_data.get('tdelay', 0) if complete_data.get('tdelay', 0) != 0 else [])
                pdelay = len(complete_data.get('pdelay', 0) if complete_data.get('pdelay', 0) != 0 else [])
                # commitment = complete_data.get('commitment')[0]['commitment'] if complete_data.get('commitment') !=None else 0.0,
                # print("the vlue in the commitmenrrrrrrrrrrrrrrrrrrrrrrrrrt",commitment)
                emp_total.update({key: {"total": total, "pending": pending, "level": level, 'unsent': unsent,
                                        'confirm': confirm, 'cancelled': cancelled, 'modified':modified,
                                        'deadline': deadline, 'tdelay': tdelay, 'pdelay': pdelay}})
                if val:
                    val_dict = self.get_total(val)
                    # print("the val in the data is val_dict", val_dict)
                    emp_total = self.get_list_of_keys(val, emp_total, level+1)
                    if not val_dict['total']:
                        val_dict['total'] = 0
                    if not val_dict['pending']:
                        val_dict['pending'] = 0
                    if not val_dict['confirm']:
                        val_dict['confirm'] = 0
                    if not val_dict['cancelled']:
                        val_dict['cancelled'] = 0
                    if not val_dict['unsent']:
                        val_dict['unsent'] = 0
                    if not val_dict['modified']:
                        val_dict['modified'] = 0
                    if not val_dict['deadline']:
                        val_dict['deadline'] = 0
                    if not val_dict['tdelay']:
                        val_dict['tdelay'] = 0
                    if not val_dict['pdelay']:
                        val_dict['pdelay'] = 0
                    # if not val_dict['commitment']:
                    #     val_dict['commitment'] = 0
                    emp_total.update(
                        {key: {
                            'total': total + val_dict["total"],
                            'pending': pending + val_dict["pending"],
                            'confirm': confirm + val_dict["confirm"],
                            'cancelled': cancelled + val_dict["cancelled"],
                            'unsent': unsent + val_dict["unsent"],
                            'modified': modified + val_dict["modified"],
                            'deadline': deadline + val_dict["deadline"],
                            'tdelay': tdelay + val_dict["tdelay"],
                            'pdelay': pdelay + val_dict["pdelay"],
                            'level': level,
                            # 'commitment': deadline + val_dict["commitment"],
                        }})
        return emp_total


    # def get_total(self, emp_dict):
    #     val_user_dict1 = {
    #         "total": 0,
    #         "pending": 0,
    #     }
    #     for key, val in emp_dict.items():
    #         val_user_dict = {
    #             "total": len(self.execute_query("total", key)),
    #             "pending": len(self.execute_query("pending", key)),
    #             }
    #         if val:
    #             val_user_dict2 = self.get_total(val)
    #             val_user_dict["total"] = int(val_user_dict["total"]) + int(val_user_dict2["total"])
    #             val_user_dict["pending"] = int(val_user_dict["pending"]) + int(val_user_dict2["pending"])
    #         if not val_user_dict["total"]:
    #             val_user_dict["total"] = 0
    #         if not val_user_dict["pending"]:
    #             val_user_dict["pending"] = 0
    #         val_user_dict1["total"] = int(val_user_dict1["total"]) + int(val_user_dict["total"])
    #         val_user_dict1["pending"] = int(val_user_dict1["pending"]) + int(val_user_dict["pending"])
    #     return val_user_dict1

    def get_total(self, emp_dict):
        val_user_dict1 = {
            "total": 0,
            "pending": 0,
            "unsent": 0,
            "confirm": 0,
            "cancelled": 0,
            "modified": 0,
            "deadline": 0,
            "tdelay": 0,
            "pdelay": 0,
            # "commitment": 0,
        }
        for key, val in emp_dict.items():
            self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s'" % (str(self.name)))
            model_data = self.env.cr.dictfetchall()
            if model_data:
                complete_data = {}
                for model in model_data:
                    complete_data[model['label_name']] = self.execute_query_user(model, key)
                # print("the value in the user commmitment", complete_data)
                val_user_dict = {
                        'total': len(complete_data.get('total', 0) if complete_data.get('total', 0) != 0 else []),
                        'pending': len(complete_data.get('pending', 0) if complete_data.get('pending', 0) != 0 else []),
                        'confirm': len(complete_data.get('confirm', 0) if complete_data.get('confirm', 0) != 0 else []),
                        'cancelled': len(complete_data.get('cancelled', 0) if complete_data.get('cancelled', 0) != 0 else []),
                        'unsent': len(complete_data.get('unsent', 0) if complete_data.get('unsent', 0) != 0 else []),
                        'modified': len(complete_data.get('modified', 0) if complete_data.get('modified', 0) != 0 else []),
                        'deadline': len(complete_data.get('deadline', 0) if complete_data.get('deadline', 0) != 0 else []),
                        'tdelay': len(complete_data.get('tdelay', 0) if complete_data.get('tdelay', 0) != 0 else []),
                        'pdelay': len(complete_data.get('pdelay', 0) if complete_data.get('pdelay', 0) != 0 else []),
                        # 'commitment' : complete_data.get('commitment')[0]['commitment'] if complete_data.get('commitment') != None else 0.0,

                    }
                if val:
                    val_user_dict2 = self.get_total(val)
                    # print("the value in the commitment", val_user_dict['commitment'])
                    # print("the value in the val_user_dict2", val_user_dict2['commitment'])
                    # print("the value in the val_user_dict", val_user_dict)
                    val_user_dict['total'] = int(val_user_dict['total']) + int(val_user_dict2['total'])
                    val_user_dict['pending'] = int(val_user_dict['pending']) + int(val_user_dict2['pending'])
                    val_user_dict['confirm'] = int(val_user_dict['confirm']) + int(val_user_dict2['confirm'])
                    val_user_dict['cancelled'] = int(val_user_dict['cancelled']) + int(val_user_dict2['cancelled'])
                    val_user_dict['unsent'] = int(val_user_dict['unsent']) + int(val_user_dict2['unsent'])
                    val_user_dict['modified'] = int(val_user_dict['modified']) + int(val_user_dict2['modified'])
                    val_user_dict['deadline'] = int(val_user_dict['deadline']) + int(val_user_dict2['deadline'])
                    val_user_dict['tdelay'] = int(val_user_dict['tdelay']) + int(val_user_dict2['tdelay'])
                    val_user_dict['pdelay'] = int(val_user_dict['pdelay']) + int(val_user_dict2['pdelay'])
                    # val_user_dict['commitment'] = float(val_user_dict.get('commitment') if val_user_dict.get('commitment') != None else 0.0) + float(val_user_dict2['commitment'])

                if not val_user_dict['total']:
                    val_user_dict['total'] = 0
                if not val_user_dict['pending']:
                    val_user_dict['pending'] = 0
                if not val_user_dict['confirm']:
                    val_user_dict['confirm'] = 0
                if not val_user_dict['cancelled']:
                    val_user_dict['cancelled'] = 0
                if not val_user_dict['unsent']:
                    val_user_dict['unsent'] = 0
                if not val_user_dict['modified']:
                    val_user_dict['modified'] = 0
                if not val_user_dict['deadline']:
                    val_user_dict['deadline'] = 0
                if not val_user_dict['tdelay']:
                    val_user_dict['tdelay'] = 0
                if not val_user_dict['pdelay']:
                    val_user_dict['pdelay'] = 0
                # if not val_user_dict['commitment']:
                #     val_user_dict['commitment'] = 0.0

                val_user_dict1['total'] = int(val_user_dict1['total']) + int(val_user_dict['total'])
                val_user_dict1['pending'] = int(val_user_dict1['pending']) + int(val_user_dict['pending'])
                val_user_dict1['confirm'] = int(val_user_dict1['confirm']) + int(val_user_dict['confirm'])
                val_user_dict1['cancelled'] = int(val_user_dict1['cancelled']) + int(val_user_dict['cancelled'])
                val_user_dict1['unsent'] = int(val_user_dict1['unsent']) + int(val_user_dict['unsent'])
                val_user_dict1['modified'] = int(val_user_dict1['modified']) + int(val_user_dict['modified'])
                val_user_dict1['deadline'] = int(val_user_dict1['deadline']) + int(val_user_dict['unsent'])
                val_user_dict1['tdelay'] = int(val_user_dict1['tdelay']) + int(val_user_dict['tdelay'])
                val_user_dict1['pdelay'] = int(val_user_dict1['pdelay']) + int(val_user_dict['pdelay'])
                # val_user_dict1['commitment'] = float(val_user_dict1['commitment']) + float(val_user_dict['commitment'])
        return val_user_dict1

    def execute_query_for_management_kpi(self, query_model, categ_wise=False):
        list_obj = []
        list_query_dict = {}
        company_id = self.env.user.company_id.id
        query = str(query_model["query"]) + str(company_id)
        self.env.cr.execute(query)
        list_query_dict = self.env.cr.dictfetchall()
        if list_query_dict:
            if categ_wise:
                for list_query in list_query_dict:
                    if list_query['id'] in categ_wise:
                        list_obj.append(list_query)
                return list_obj
        return list_query_dict

    def execute_query_user(self, query_model, emp_id):
        list_query_dict = {}
        employee_id = self.env["hr.employee"].search([("id", "=", emp_id)])
        if employee_id:
            if employee_id.user_id:
                user_id=employee_id.user_id[0]
                company_id = self.env.user.company_id.id
                query = str(query_model["query"]) + str(company_id) + " and create_uid=" + str(user_id.id)
                if query:
                    self.env.cr.execute(query)
                    list_query_dict = self.env.cr.dictfetchall()
                    if list_query_dict:
                       return list_query_dict
        return list_query_dict

    @api.multi
    def change_view_type(self):
        self.view_type = self._context.get("view_type")

    def execute_query1(self, label_name, emp_id):
        list_query_obj = []
        employee_id = self.env["hr.employee"].search([("id", "=", emp_id)])
        # user_id = self.env["hr.employee"].search([("id", "=", emp_id)]).user_id[0]
        company_id = self.env.user.company_id.id

        self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
                            "and label_name='%s'" % (str(self.name), label_name))
        record = self.env.cr.dictfetchall()
        if record:
            if employee_id:
                if employee_id.user_id:
                    user_id = employee_id.user_id[0]
                    query = str(record[0]["query"]) + str(company_id)+ " and create_uid="+str(user_id.id)
                    self.env.cr.execute(query)
                    list_query_dict = self.env.cr.dictfetchall()
                    if list_query_dict:
                        for query_dict in list_query_dict:
                            list_query_obj.append(self.env[self.name].search([("id", "=", query_dict["id"])]))
        return list_query_obj

    def inactive_items(self):
        inactive_items = 0
        company_id = self.env.user.company_id.id
        query = 'select count(*) from product_template where company_id=%s and active = %s' % (company_id, False)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            inactive_items = result[0]['count']
        return inactive_items

    def inactive_vendors(self):
        inactive_vendors = 0
        company_id = self.env.user.company_id.id
        query = "select count(*) from res_partner where active = %s and company_id = %s and supplier=%s" % (
        False, company_id, True)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            inactive_vendors = result[0]['count']
        return inactive_vendors

    def not_having_mail_id(self):
        not_mail = 0
        company_id = self.env.user.company_id.id
        query = "select count(*) from res_partner where email is null and company_id = %s and supplier=%s and active=%s and parent_id is null" % (
        company_id, True, True)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            not_mail = result[0]['count']
        return not_mail

    def items_not_linked_with_hsn(self):
        items_not_with_hsn = 0
        company_id = self.env.user.company_id.id
        query = 'select count(*) from product_template where company_id= %s and active=%s and hsn_id is null' % (company_id, True)
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
        print("The print in the names ", names)
        if names:
            names.write({"name": 'kpi', "inactive_items": inactive_items,
                         "inactive_vendor": inactive_vendor, 'supplier_dont_have_email': without_email,
                         'item_not_linked_with_hsn': without_hsn})
        else:
            self.env['kpi.matrix'].sudo().create({"name": 'kpi', "inactive_items": inactive_items,
                                                  "inactive_vendor": inactive_vendor,
                                                  'supplier_dont_have_email': without_email,
                                                  'item_not_linked_with_hsn': without_hsn})
        print("creation Successfully")

    #The Fuctions For View On Action
    def get_obj_of_keys(self, emp_dict, obj_list, type=False):

        print("Typeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", type)
        for key, val in emp_dict.items():
            objs = self.execute_query1(type, key)
            for obj in objs:
                if obj.id:
                    obj_list.append(obj)
            if val:
                obj_list = self.get_obj_of_keys(val, obj_list, type)
        return obj_list

    @api.multi
    def get_inactive_item_list_view(self):
        result = {}
        data = self.env['product.template'].search([('company_id', '=', self.env.user.company_id.id), ('active', '=', False)])
        print("dataaaaaaaaaaaaaaaaaaaa", data)

        if data:
            all_agreements_ids = []
            if data:
                all_agreements_ids = data.ids
            action = self.env.ref('product_extension.product_template_raw_material_action_raw1')
            res = self.env.ref('product_extension.product_template_raw_material_tree_view').id
            res_form = self.env.ref('product_extension.product_template_raw_material_form_view').id
            result = action[0].read()[0]
            result['views'] = [(res, 'list'), (res_form, 'form')]
            result['domain'] = [('id', 'in',  tuple(all_agreements_ids))]
            result['target'] = 'current'
        return result

    @api.multi
    def get_inactive_vendor_list_view(self):
        result = {}
        data = self.env['res.partner'].search(
            [('company_id', '=', self.env.user.company_id.id), ('active', '=', False), ('supplier', '=', True)])
        if data:
            print("the value int the data",data)
            all_agreements_ids = data.ids
            action = self.env.ref('purchase_extension.action_partner_supplier_form_arke_ext1')
            res = self.env.ref('base.view_partner_tree').id
            res_form = self.env.ref('base.view_partner_form').id
            result = action[0].read()[0]
            result['views'] = [(res, 'list'), (res_form, 'form')]
            result['domain'] = [('id', 'in', tuple(all_agreements_ids))]
            result['target'] = 'current'
        return result

    @api.multi
    def get_supplier_without_email_list_view(self):
        result = {}
        obj_list = []
        company_id = self.env.user.company_id.id
        query = "select * from res_partner where email is null and company_id = %s and supplier=%s and active =%s and parent_id is null" % (
            company_id, True, True)
        self.env.cr.execute(query)
        total_data = self.env.cr.dictfetchall()
        if total_data:
            for obj in total_data:
                obj_list.append(self.env['res.partner'].search([("id", "=", obj["id"])]))
        print("the data in the ", obj_list)
        action = self.env.ref('purchase_extension.action_partner_supplier_form_arke_ext')
        res = self.env.ref('base.view_partner_tree').id
        res_form = self.env.ref('base.view_partner_form').id
        result = action[0].read()[0]
        result['views'] = [(res, 'list'), (res_form, 'form')]
        result['domain'] = [('id', 'in', [obj.id for obj in obj_list])]
        result['target'] = 'current'
        return result

    @api.multi
    def get_items_without_hsn_list_view(self):
        result = {}
        data = self.env['product.template'].search(
            [('company_id', '=', self.env.user.company_id.id), ('hsn_id', '=', False)])
        if data:
            all_agreements_ids = []
            if data:
                all_agreements_ids = data.ids
            action = self.env.ref('product_extension.product_template_raw_material_action_raw')
            res = self.env.ref('product_extension.product_template_raw_material_tree_view').id
            res_form = self.env.ref('product_extension.product_template_raw_material_form_view').id
            result = action[0].read()[0]
            result['views'] = [(res, 'list'), (res_form, 'form')]
            result['domain'] = [('id', 'in', tuple(all_agreements_ids))]
            result['target'] = 'current'
        return result

    # @api.multi
    # def get_total_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     user = self.env.user
    #     emp_id = self._context.get("emp_id")
    #     view = self.view_type
    #     print("the value in the self.view_type is,", self.view_type)
    #     self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                           "and label_name='%s'" % (str(self.name), 'total'))
    #
    #     if user.has_group('purchase_extension.group_purchase_management'):
    #         model_dict = {}
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], categ_wise=False, emp_id=emp_id, view_type=view)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #         print("the data",obj_list)
    #     elif user.has_group('purchase_extension.group_product_category_wise_acces'):
    #         record_categ_wise = self.get_category_wise_record_list(self.name)
    #         self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'total'))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], categ_wise=record_categ_wise, emp_id=emp_id, view_type=view)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     else:
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list, type='total')
    #     if self.name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_pending_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     user = self.env.user
    #     self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'pending'))
    #
    #     if user.has_group('purchase_extension.group_purchase_management'):
    #         model_dict = {}
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0])
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     elif user.has_group('purchase_extension.group_product_category_wise_acces'):
    #         record_categ_wise = self.get_category_wise_record_list(self.name)
    #         self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'pending'))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             # if self.name == 'pr.create.data':
    #             #     total_data = self.execute_management_query(model_data[0])
    #             #     print("the length or the data is",len(total_data))
    #             #     if total_data:
    #             #         for obj in total_data:
    #             #             obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #             # else:
    #             total_data = self.execute_management_query(model_data[0], record_categ_wise)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     else:
    #         emp_id = self._context.get("emp_id")
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list, type='pending')
    #     if self.name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_cancelled_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     user = self.env.user
    #     self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'cancelled'))
    #
    #     if user.has_group('purchase_extension.group_purchase_management'):
    #         model_dict = {}
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0])
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #         print("the data", obj_list)
    #     elif user.has_group('purchase_extension.group_product_category_wise_acces'):
    #         record_categ_wise = self.get_category_wise_record_list(self.name)
    #         self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'cancelled'))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], record_categ_wise)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     else:
    #         emp_id = self._context.get("emp_id")
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list, type='cancelled')
    #     if self.name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_unsent_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     user = self.env.user
    #     self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'unsent'))
    #
    #     if user.has_group('purchase_extension.group_purchase_management'):
    #         model_dict = {}
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0])
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #         print("the data", obj_list)
    #     elif user.has_group('purchase_extension.group_product_category_wise_acces'):
    #         record_categ_wise = self.get_category_wise_record_list(self.name)
    #         self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'unsent'))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], record_categ_wise)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     else:
    #         emp_id = self._context.get("emp_id")
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list, type='unsent')
    #     if self.name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_confirm_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     user = self.env.user
    #     self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'confirm'))
    #
    #     if user.has_group('purchase_extension.group_purchase_management'):
    #         model_dict = {}
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0])
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #         print("the data", obj_list)
    #     elif user.has_group('purchase_extension.group_product_category_wise_acces'):
    #         record_categ_wise = self.get_category_wise_record_list(self.name)
    #         self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'confirm'))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], record_categ_wise)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     else:
    #         emp_id = self._context.get("emp_id")
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list, type = 'confirm')
    #     if self.name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_modified_in_last_month(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     user = self.env.user
    #     self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'modified'))
    #
    #     if user.has_group('purchase_extension.group_purchase_management'):
    #         model_dict = {}
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0])
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #         print("the data", obj_list)
    #     elif user.has_group('purchase_extension.group_product_category_wise_acces'):
    #         record_categ_wise = self.get_category_wise_record_list(self.name)
    #         self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'modified'))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], record_categ_wise)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     else:
    #         emp_id = self._context.get("emp_id")
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list, type='modified')
    #     if self.name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_expire_in_two_month_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     user = self.env.user
    #     self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'deadline'))
    #
    #     if user.has_group('purchase_extension.group_purchase_management'):
    #         model_dict = {}
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0])
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #         print("the data", obj_list)
    #     elif user.has_group('purchase_extension.group_product_category_wise_acces'):
    #         record_categ_wise = self.get_category_wise_record_list(self.name)
    #         self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'deadline'))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], record_categ_wise)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     else:
    #         emp_id = self._context.get("emp_id")
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list, type='deadline')
    #     if self.name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_exhaust_commitment_value_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     user = self.env.user
    #     self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'commitment'))
    #
    #     if user.has_group('purchase_extension.group_purchase_management'):
    #         model_dict = {}
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0])
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #         print("the data", obj_list)
    #     elif user.has_group('purchase_extension.group_product_category_wise_acces'):
    #         record_categ_wise = self.get_category_wise_record_list(self.name)
    #         self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'commitment'))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], record_categ_wise)
    #             print("the data inside model_data is", total_data)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     else:
    #         emp_id = self._context.get("emp_id")
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list, type='commitment')
    #     if self.name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result

        # obj_list = []
        # company_id = self.env.user.company_id.id
        # query = '''select * from purchase_order where purchase_req_id in (select id from purchase_requisition where type_id =1) and state in ('purchase','done') and company_id=%s''' %(company_id)
        # self.env.cr.execute(query)
        # total_data = self.env.cr.dictfetchall()
        # print("the total data is", total_data)
        # if total_data:
        #     for obj in total_data:
        #         obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
        # print("the total data is", obj_list)
        # if self.name:
        #     action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
        #     res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
        #     res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
        #     result = action[0].read()[0]
        #     result['views'] = [(res, 'list'), (res_form, 'form')]
        #     result['domain'] = [('id', 'in', [val.id for val in obj_list])]
        #     result['target'] = 'current'
        # return result

    @api.multi
    def get_require_date_list_view(self):
        obj_list = []
        objs =[]
        emp_dict = {}
        result = {}
        user = self.env.user
        self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
                            "and label_name='%s'" % (str(self.name), 'pending'))
        model_dict = {}
        model_data = self.env.cr.dictfetchall()
        if user.has_group('purchase_extension.group_purchase_management'):
            if model_data:
                total_data = self.execute_management_query(model_data[0])
                if total_data:
                    for obj in total_data:
                        objs.append(self.env[self.name].search([("id", "=", obj["id"])]))
            print("the data", objs)
        else:
            emp_id = self._context.get("emp_id")
            if model_data:
                total_data = self. execute_query_user(model_data[0], emp_id)
                if total_data:
                    for obj in total_data:
                        objs.append(self.env[self.name].search([("id", "=", obj["id"])]))
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
            result['domain'] = [('id', 'in',  obj_list)]
            result['target'] = 'current'
        return result

    # @api.multi
    # def get_total_delay_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     user = self.env.user
    #     self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'tdelay'))
    #
    #     if user.has_group('purchase_extension.group_purchase_management'):
    #         model_dict = {}
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0])
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #         print("the data", obj_list)
    #     elif user.has_group('purchase_extension.group_product_category_wise_acces'):
    #         record_categ_wise = self.get_category_wise_record_list(self.name)
    #         self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'tdelay'))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], record_categ_wise)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     else:
    #         emp_id = self._context.get("emp_id")
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list, type='tdelay')
    #     if self.name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_pending_delay_view(self):
    #
    #     model_name_dict = {''}
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     user = self.env.user
    #     print("the vlue in the fffffffffffffff",self._context.get("emp_id"))
    #     self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'pdelay'))
    #
    #     if user.has_group('purchase_extension.group_purchase_management'):
    #         model_dict = {}
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0])
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #         print("the data", obj_list)
    #     elif user.has_group('purchase_extension.group_product_category_wise_acces'):
    #         record_categ_wise = self.get_category_wise_record_list(self.name)
    #         self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'pdelay'))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], record_categ_wise)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     else:
    #         emp_id = self._context.get("emp_id")
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list, type='pdelay')
    #     if self.name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result

    @api.multi
    def get_label_list_view(self):
        obj_list = []
        emp_dict = {}
        result = {}
        user = self.env.user
        emp_id = self._context.get("emp_id")
        label_name = self._context.get("label_name")
        view = self.view_type
        self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
                            "and label_name='%s'" % (str(self.name), label_name))

        if user.has_group('purchase_extension.group_purchase_management'):
            model_dict = {}
            model_data = self.env.cr.dictfetchall()
            if model_data:
                total_data = self.execute_management_query(model_data[0], categ_wise=False, emp_id=emp_id,
                                                           view_type=view)
                if total_data:
                    for obj in total_data:
                        obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))

        elif user.has_group('purchase_extension.group_product_category_wise_acces'):
            record_categ_wise = self.get_category_wise_record_list(self.name)
            self.env.cr.execute("select * from purchase_dynamic_dashboard_query where model_name='%s' "
                                "and label_name='%s'" % (str(self.name), label_name))
            model_data = self.env.cr.dictfetchall()
            if model_data:
                total_data = self.execute_management_query(model_data[0], categ_wise=record_categ_wise, emp_id=emp_id,
                                                           view_type=view)
                if total_data:
                    for obj in total_data:
                        obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
        else:
            emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
            emp_dict.update({emp_id: {}})
            emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
            if emp_id_val:
                emp_dict.get(emp_id).update(emp_id_val)
            obj_list = self.get_obj_of_keys(emp_dict, obj_list, type=label_name)
        if self.name:
            # For Action
            if self.name == 'material.req.slip':
                action = self.env.ref('purchase_extension.action_purchase_indent_mrs')
            elif self.name == 'purchase.req':
                action = self.env.ref("purchase_extension.action_purchase_req")

            elif self.name == 'request.for.quotation' and label_name == 'pending':
                action = self.env.ref("purchase_extension.action_pr_report")
            elif self.name == 'supplier.quotation' and label_name == 'pending':
                action = self.env.ref("purchase_extension.action_rfq_report_view")
            else:
                action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])

            # For Tree View
            if self.name == 'request.for.quotation' and label_name == 'pending':
                res = self.env.ref("purchase_extension.view_pr_report_tree").id
                # res_form = self.env.ref("purchase_extension.view_pr_report_tree")
            elif self.name == 'supplier.quotation' and label_name == 'pending':
                res = self.env.ref("purchase_extension.view_rfq_report_view_tree").id
            else:
                res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id

            # For Form View
            # if self.name == 'supplier.quotation' and label_name == 'pending':
            #     res_form = self.env.ref("purchase_extension.view_supplier_quotation_form").id
            # else:
            res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id

            result = action[0].read()[0]
            if self.name == 'request.for.quotation' and label_name == 'pending':
                result['views'] = [(res, 'list')]
            elif self.name == 'supplier.quotation' and label_name == 'pending':
                result['views'] = [(res, 'list')]
            else:
                result['views'] = [(res, 'list'), (res_form, 'form')]
                result['domain'] = [('id', 'in', [val.id for val in obj_list])]
            result['target'] = 'current'
        return result


class PurchaseExtensionDashboardUser(models.Model):
    _name = "res.users"
    _inherit = "res.users"

    @api.model
    def create(self, values):
        model_names = []
        # print("new user")
        res = super(PurchaseExtensionDashboardUser, self).create(values)
        names = self.env["purchase.dynamic.dashboard.query"].search([("id", ">", 0)])
        for name in names:
            model_names.append(name.model_name)
        model_names = set(model_names)
        for company in res.company_ids:
            for name in model_names:
                # print(res.id, name, "user and name")

                self.env['purchase.dynamic.dashboard'].sudo().create({"name": name, "user_id": res.id,
                                                             "company_id": company.id})
        return res

    @api.multi
    def write(self, values):
        model_names = []
        if "company_ids" in values:
            if values.get("company_ids")[0][2]:
                for company_id in values.get("company_ids")[0][2]:
                    dashboard = self.env['purchase.dynamic.dashboard'].search([("user_id","=", self.id), ("company_id", "=", company_id)])
                    if len(dashboard) == 0:
                        names = self.env["purchase.dynamic.dashboard.query"].search([("id", ">", 0)])
                        for name in names:
                            model_names.append(name.model_name)
                        model_names = set(model_names)
                        for name in model_names:
                            self.env['purchase.dynamic.dashboard'].sudo().create({"name": name, "user_id": self.id,
                                                                             "company_id": company_id})

        res = super(PurchaseExtensionDashboardUser, self).write(values)
        return res


class PurchaseDynamicDashboardQuery(models.Model):
    _description = "Query Detail"
    _name = "purchase.dynamic.dashboard.query"

    model_name = fields.Char("Model Name", store=True)
    label_name = fields.Char("Label Name")
    query = fields.Text("Query")
    col_name = fields.Char("Column Name")

    @api.model
    def create(self, vals):
        if 'model_name' in vals and vals.get('model_name') and 'label_name' in vals and vals.get('label_name') and 'query' in vals and vals.get('query'):
            data = self.env["purchase.dynamic.dashboard.query"].search([('model_name', '=', vals.get('model_name')), ('label_name', '=', vals.get('label_name')), ('query', '=',vals.get('query'))])
            if data:
                raise ValidationError("Record Already Exist....")

        res = super(PurchaseDynamicDashboardQuery, self).sudo().create(vals)

        user_dict = []
        names = []
        dynamic_db = self.env['purchase.dynamic.dashboard']
        objs = self.env["purchase.dynamic.dashboard"].search([('id', '>', 0)], order='id desc')
        for unique in objs:

            if {'user_id': unique.user_id.id, 'company_id': unique.company_id.id} not in user_dict:
                user_dict.append({'user_id': unique.user_id.id, 'company_id': unique.company_id.id})

            if unique.name not in names:
                names.append(unique.name)
        if res.model_name not in names:
            for dict in user_dict:
                dynamic_db.create({'name': res.model_name,
                                   'user_id': dict['user_id'],
                                   'company_id': dict['company_id']})
        return res


class PurchaseDynamicDashboardEmployee(models.Model):
    _name = "hr.employee"
    _inherit = "hr.employee"

    user_id = fields.Many2one('res.users', 'User', related='resource_id.user_id', store=True)

    @api.multi
    @api.onchange("user_id")
    def onchange_code(self):
        if self.user_id.id and self.company_id.id:
            query = "select * from purchase_dynamic_dashboard where user_id =" + str(self.user_id.id)\
                    + "and company_id =" + str(self.company_id.id)
            self.env.cr.execute(query)
            dashboard = self.env.cr.dictfetchall()
            for record in dashboard:
                obj = self.env['purchase.dynamic.dashboard'].sudo().browse(record["id"])
                obj.write({"active": True})


class PurchaseDynamicDashboardUserWise(models.Model):
    _description = "User Detail"
    _name = "purchase.dynamic.dashboard.user.wise"

    emp_name = fields.Char("Name")
    emp_id = fields.Integer("employee id")
    user_wise_total = fields.Integer()
    user_wise_pending = fields.Integer()
    level = fields.Integer()
    purchase_ext_dashboard_id = fields.Many2one('purchase.dynamic.dashboard', 'Purchase dashboard')
    active=fields.Boolean('Active',default=True)

    @api.model
    def create(self, values):
        res = super(PurchaseDynamicDashboardUserWise, self).create(values)
        return res


class KPIMatrix(models.Model):
    _name = 'kpi.matrix'

    name = fields.Char("Name")
    inactive_items = fields.Integer("Inactive Items")
    inactive_vendor = fields.Integer("Inactive Vendor")
    supplier_dont_have_email = fields.Integer("Email Does Not Exist")
    item_not_linked_with_hsn = fields.Integer("Items Without HSN")
    company_id = fields.Many2one('res.company', 'Company', index=True,
                                 default=lambda self: self.env.user.company_id.id)
