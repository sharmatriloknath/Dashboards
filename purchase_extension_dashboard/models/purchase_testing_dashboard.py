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
from datetime import datetime as dt
from lxml import etree
from threading import Timer
import re


class PurchaseExtensionDashboardTesting(models.Model):
    _description = "purchase Detail Testing"
    _name = "purchase.extension.dashboard.testing"

    active = fields.Boolean('Active', default=True, store=True)
    name = fields.Selection([
        ('material.req.slip', 'MRS'),
        ('purchase.req', 'PR'),
        ('purchase.order', 'PO'),
        ('request.for.quotation', 'RFQ'),
        ('supplier.quotation', 'Quotation'),
        ('pr.create.data', 'Create PR'),
    ], string="Name")
    computation = fields.Char(compute="_computation")
    total = fields.Integer("Total")
    user_id = fields.Many2one('res.users', 'User')
    company_id = fields.Many2one('res.company', 'Company')
    pending = fields.Integer("Pending")
    high_priority = fields.Integer("High Priority")
    color = fields.Integer('Color')
    view_type = fields.Boolean('Type', default=True)
    user_wise_id = fields.One2many("purchase.extension.dashboard.user.wise.testing", "purchase_ext_dashboard_id_testing")
    have_child = fields.Boolean('Have Child', default=False)
    emp_id = fields.Integer("employee id")
    require_date = fields.Date(string='Require Date')
    level_type = fields.Char("Level Type")
    level_val = fields.Integer("Level Value")
    level_type_list = fields.Char("All Level Type")
    level_val_list = fields.Char("All Val Type")
    temp_context = fields.Boolean('temp_context', default=False)


    @api.multi
    def _computation(self):
        emp_dict = {}
        emp_total = {}
        useful_type_dict = {}
        useful_val_dict = {}
        allow_group_list = set([i.id for i in self for j in i.env.user.groups_id if j and j.category_id.name == "Purchases"])

        for record in self:

            if record.user_id.id == record.env.user.id and record.company_id.id == record.env.user.company_id.id and record.id in allow_group_list and record.name:

                user_wise_list = []
                have_child = False
                emp_id = record.env["hr.employee"].search([("user_id", "=", record.env.user.id)]).id
                if emp_id:
                    if str(record.name) == 'pr.create.data':
                        pending_cr = record.execute_query(record.level_type, emp_id)
                        min_require_date = None
                        for cr_obj in pending_cr:
                            if cr_obj.require_date :
                                if not min_require_date:
                                    min_require_date = cr_obj.require_date
                                if cr_obj.require_date < min_require_date:
                                    min_require_date = cr_obj.require_date
                        if min_require_date:
                            min_require_date = min_require_date.split()[0]

                            record.sudo().write(
                                {"require_date": min_require_date, "pending": len(pending_cr), "have_child": have_child,
                                 "emp_id": emp_id, "level_type": record.level_type, "level_val": len(pending_cr)})

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

                                record.sudo().write(
                                    {"total": total, "pending": pending, "have_child": have_child,
                                     "emp_id": emp_id, "level_type": record.level_type,
                                     "level_val": element[1].get(record.level_type,-1)})

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
                        line_obj = record.env["purchase.extension.dashboard.user.wise.testing"].search(
                            [("purchase_ext_dashboard_id_testing", "=", record.id)])
                        if len(line_obj) > 0:

                            if len(line_obj) == len(user_wise_list):
                                for i, line in enumerate(line_obj):
                                    line.sudo().write(user_wise_list[i][2])
                            elif len(line_obj) > len(user_wise_list):
                                for i, line in enumerate(line_obj):
                                    try:
                                        line.sudo().write(user_wise_list[i][2])
                                    except:
                                        query = "delete from purchase_extension_dashboard_user_wise_testing where id ="+ str(line.id)
                                        record.env.cr.execute(query)
                            elif len(line_obj) < len(user_wise_list):
                                a = 0
                                list_of_new_users = []
                                for i, line in enumerate(line_obj):
                                    line.sudo().write(user_wise_list[i][2])
                                    a = i
                                for j, user in enumerate(user_wise_list):
                                    if a > j:
                                       list_of_new_users.append(user)
                                record.sudo().write({"user_wise_id": list_of_new_users})
                        else:
                            record.sudo().write({"user_wise_id": user_wise_list})

                    if not record.temp_context and record.name not in useful_type_dict:
                        useful_type_dict[record.name] = [record.level_type]
                        useful_val_dict[record.name] = [record.level_val]
                    elif not record.temp_context and record.level_type not in useful_type_dict[record.name]:
                        useful_type_dict[record.name].append(record.level_type)
                        useful_val_dict[record.name].append(record.level_val)

                else:
                    record.write({"active": False})

        if len(useful_type_dict) > 0:
            done_dict = []
            for record in self:
                if record.name not in done_dict:
                    done_dict.append(record.name)
                    record.sudo().write({
                        "level_type_list": ",".join(useful_type_dict[record.name]),
                        "level_val_list": ",".join(list(map(str,useful_val_dict[record.name])))
                    })
        elif record.temp_context:
            self.env.cr.execute("""update purchase_extension_dashboard_testing 
                                            set temp_context = %s 
                                            where user_id = %s and name = '%s'""" % (
                False, record.user_id.id, record.name))

    @api.model
    def create_card_for_user(self):
        model_names = []
        users = self.env["res.users"].search([("id", ">", 0)])
        names = self.env["purchase.extension.dashboard.query.testing"].search([("id", ">", 0)])


        for name in names:
            model_names.append(name.model_name)
        model_names = set(model_names)
        for user in users:
            for company in user.company_ids:
                for name in model_names:
                    self.env.cr.execute(
                        """select distinct label_name from purchase_extension_dashboard_query_testing where model_name = '%s'""" %name)
                    match_recs = self.env.cr.dictfetchall()
                    for i in match_recs:
                        self.env['purchase.extension.dashboard.testing'].create({"name": name, "user_id": user.id,
                                                                     "company_id": company.id, "level_type":i.get('label_name')})

    @api.multi
    def compute_by_scheduler(self):
        return {
            'type': 'ir.actions.window',
            'tag': 'reload',
        }


    def execute_query(self, label_name, emp_id):
        list_query_obj = []
        try:
            user_id = self.env["hr.employee"].search([("id", "=", emp_id)]).user_id[0]
            query = self.env["purchase.extension.dashboard.query.testing"].search([("model_name", "=", str(self.name)),
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

    def get_list_of_keys(self, emp_dict, emp_total, level):
        for key, val in emp_dict.items():
            total = len(self.execute_query("total", key))
            pending = len(self.execute_query("pending", key))
            if not total:
                total = 0
            if not pending:
                pending = 0
            emp_total.update({key: {"total": total, "pending": pending, "level": level}})
            if val:
                val_dict = self.get_total(val)
                emp_total = self.get_list_of_keys(val, emp_total, level+1)
                if not val_dict["total"]:
                    val_dict["total"] = 0
                if not val_dict["pending"]:
                    val_dict["pending"] = 0
                emp_total.update({key: {"total": total + val_dict["total"], "pending": pending + val_dict["pending"],
                                  "level": level}})
        return emp_total

    def get_obj_of_keys(self, emp_dict, obj_list):
        for key, val in emp_dict.items():
            objs = self.execute_query("total", key)
            for obj in objs:
                if obj.id:
                    obj_list.append(obj.id)
            if val:
                obj_list = self.get_obj_of_keys(val, obj_list)
        return obj_list

    @api.multi
    def get_total_list_view(self):
        obj_list = []
        emp_dict = {}
        result = {}
        emp_id = self._context.get("emp_id")
        emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
        emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
        emp_dict.update({emp_id: {}})
        emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
        if emp_id_val:
            emp_dict.get(emp_id).update(emp_id_val)
        obj_list = self.get_obj_of_keys(emp_dict, obj_list)
        if self.name:
            action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
            res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
            res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
            result = action[0].read()[0]
            result['views'] = [(res, 'list'), (res_form, 'form')]
            result['domain'] = [('id', 'in', obj_list)]
            result['target'] = 'main'
            result["status"] = "total"
        if self.name == 'purchase.req':
            if len(emp_id_user) <= 0:
                raise ValidationError(_('Please define employee for related user'))
                return 0
            else:
                return result
        else:
            return result

    def get_delay_obj_of_keys(self, emp_dict, obj_list, level_type):
        for key, val in emp_dict.items():
            objs = self.execute_query(level_type, key)

            for obj in objs:
                if obj.id:
                    obj_list.append(obj.id)

            if val:
                obj_list = self.get_delay_obj_of_keys(val, obj_list, level_type)
        return obj_list

    @api.multi
    def get_require_date_list_view(self):
        obj_list = []
        result = {}
        emp_id = self._context.get("emp_id")
        emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
        objs = self.execute_query("pending", emp_id)
        min_require_date = None
        for cr_obj in objs:
            if not min_require_date:
                min_require_date = cr_obj.require_date
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
        if (self.name == 'pr.create.data'):
            if len(emp_id_user)<=0:
                raise ValidationError(_('Please define employee for related user'))
                return 0
            else:
                return result
        else:
            return result

    @api.multi
    def get_pending_list_view(self):
        obj_list = []
        emp_dict = {}
        result = {}
        emp_id = self._context.get("emp_id")
        level_type = self._context.get("level_type")
        emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
        emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
        emp_dict.update({emp_id: {}})
        emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
        if emp_id_val:
            emp_dict.get(emp_id).update(emp_id_val)

        obj_list = self.get_delay_obj_of_keys(emp_dict, obj_list, level_type)


        if self.name:
            action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
            res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
            res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
            result = action[0].read()[0]
            result['views'] = [(res, 'list'), (res_form, 'form')]
            result['domain'] = [('id', 'in', obj_list)]
            result['target'] = 'main'
            result["status"] = level_type

        if self.name == 'purchase.req' or self.name == 'pr.create.data':
            if len(emp_id_user)<=0:
                raise ValidationError(_('Please define employee for related user'))
                return 0
            else:
                return result
        else:
            return result

    @api.multi
    def change_view_type(self):
        self.view_type = self._context.get("view_type")
        self.temp_context = self._context.get("temp_context")
        self.env.cr.execute("""update purchase_extension_dashboard_testing 
                                set temp_context = %s 
                                where user_id = %s and name = '%s'""" %(self.temp_context, self.user_id.id, self.name))



class PurchaseExtensionDashboardQueryTesting(models.Model):
    _description = "Query Detail"
    _name = "purchase.extension.dashboard.query.testing"

    model_name = fields.Char("Model Name")
    label_name = fields.Char("Label Name")
    query = fields.Text("Query")



class PurchaseExtensionDashboardUserWiseTesting(models.Model):
    _description = "User Detail"
    _name = "purchase.extension.dashboard.user.wise.testing"

    emp_name = fields.Char("Name")
    emp_id = fields.Integer("employee id")
    user_wise_total = fields.Integer()
    user_wise_pending = fields.Integer()
    level = fields.Integer()
    purchase_ext_dashboard_id_testing = fields.Many2one('purchase.extension.dashboard.testing', 'Purchase dashboard')
    active=fields.Boolean('Active',default=True)


class PurchaseExtensionDashboardUser(models.Model):
    _name = "res.users"
    _inherit = "res.users"

    @api.model
    def create(self, values):
        model_names = []
        # print("new user")
        res = super(PurchaseExtensionDashboardUser, self).create(values)
        names = self.env["purchase.extension.dashboard.query.testing"].search([("id", ">", 0)])
        for name in names:
            model_names.append(name.model_name)
        model_names = set(model_names)
        for company in res.company_ids:
            for name in model_names:
                # print(res.id, name, "user and name")
                self.env['purchase.extension.dashboard.testing'].create({"name": name, "user_id": res.id,
                                                                         "company_id": company.id})
        return res

    @api.multi
    def write(self, values):
        model_names = []
        if "company_ids" in values:
            # print(values.get("company_ids"), "companyssssssssssss")
            if values.get("company_ids")[0][2]:
                for company_id in values.get("company_ids")[0][2]:
                    ##### abhishek-14-8-2019, define model_names = [] because it gives error when 2nd company allowed to user from User form
                    model_names = []
                    dashboard = self.env['purchase.extension.dashboard.testing'].search([("user_id","=", self.id), ("company_id","=", company_id)])
                    if len(dashboard) == 0:
                        names = self.env["purchase.extension.dashboard.query.testing"].search([("id", ">", 0)])
                        for name in names:
                            model_names.append(name.model_name)
                        model_names = set(model_names)
                        for name in model_names:
                            self.env['purchase.extension.dashboard.testing'].create({"name": name, "user_id": self.id,
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
            query = "select * from purchase_extension_dashboard_testing where user_id =" + str(self.user_id.id)\
                    + "and company_id =" + str(self.company_id.id)
            self.env.cr.execute(query)
            dashboard = self.env.cr.dictfetchall()
            for record in dashboard:
                obj = self.env['purchase.extension.dashboard.testing'].sudo().browse(record["id"])
                obj.write({"active": True})


