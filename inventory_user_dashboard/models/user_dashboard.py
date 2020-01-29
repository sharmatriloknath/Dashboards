# from odoo import api, fields, models, tools, _
# from odoo.http import Controller, request
# import time, datetime
# from odoo.exceptions import UserError
# from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
# from odoo.exceptions import ValidationError, RedirectWarning, except_orm
# from odoo.addons import decimal_precision as dp
# from odoo.tools.float_utils import float_is_zero, float_compare
# from odoo.tools import pycompat
# from odoo.tools.float_utils import float_round
# from datetime import timedelta
# import datetime
# import dateutil.relativedelta
# from datetime import datetime as dt
# from lxml import etree
# from threading import Timer
#
#
# class InventoryUserDashboard(models.Model):
#     _description = "Inventory Detail"
#     _name = "inventory.user.dashboard"
#
#     active = fields.Boolean('Active', default=True, store=True)
#     name = fields.Selection([
#         ('material.req.slip', 'MRS'),
#     ], string="Name")
#     computation = fields.Char(compute="_computation")
#     total = fields.Integer("Total")
#     user_id = fields.Many2one('res.users', 'User')
#     company_id = fields.Many2one('res.company', 'Company')
#     pending = fields.Integer("Pending")
#     color = fields.Integer('Color')
#     view_type = fields.Boolean('Type', default=True)
#     user_wise_id = fields.One2many("inventory.user.dashboard.user.wise", "inventory_user_dashboard_id")
#     have_child = fields.Boolean('Have Child', default=False)
#     emp_id = fields.Integer("employee id")
#
#     @api.multi
#     def _computation(self):
#         # shubham
#         i = 1
#         emp_dict = {}
#         emp_total = {}
#         # print("edssssssssssss")
#         for record in self:
#             if record.user_id.id == record.env.user.id:
#                 if record.company_id.id == record.env.user.company_id.id:
#                     for group in record.env.user.groups_id:
#                         # shubham
#                         if i == 1:
#                             if group:
#                                 if group.name == "User" or group.name == "Manager":
#                                     user_wise_list = []
#                                     have_child = False
#                                     if record.name:
#                                         emp_id = record.env["hr.employee"].search(
#                                             [("user_id", "=", record.env.user.id)]).id
#                                         if emp_id:
#                                             emp_objs = record.env["hr.employee"].search([("parent_id", "=", emp_id)])
#                                             if len(emp_objs) > 0:
#                                                 have_child = True
#                                             emp_dict.update({emp_id: {}})
#                                             emp_id_val = record.get_employee_child(emp_objs, emp_dict.get(emp_id))
#                                             if emp_id_val:
#                                                 emp_dict.get(emp_id).update(emp_id_val)
#                                             emp_total = record.get_list_of_keys(emp_dict, emp_total, 1)
#
#                                             # shubham
#                                             i = 2
#                                             for key, val in emp_total.items():
#                                                 if emp_id == key:
#                                                     total = val.get("total")
#                                                     pending = val.get("pending")
#                                                     record.write(
#                                                         {"total": total, "pending": pending, "have_child": have_child,
#                                                          "emp_id": emp_id})
#                                                     if pending == 0:
#                                                         record.write({"color": 10})
#                                                     else:
#                                                         record.write({"color": 9})
#                                                 user_wise = (0, False, {
#                                                     "emp_id": key,
#                                                     "emp_name": record.env["hr.employee"].search(
#                                                         [("id", "=", key)]).name,
#                                                     "user_wise_total": val.get("total"),
#                                                     "user_wise_pending": val.get("pending"),
#                                                     "level": str(val.get('level')),
#                                                 })
#                                                 user_wise_list.append(user_wise)
#                                             line_obj = record.env["inventory.user.dashboard.user.wise"].search(
#                                                 [("inventory_user_dashboard_id", "=", record.id)])
#                                             if len(line_obj) > 0:
#                                                 for i, line in enumerate(line_obj):
#                                                     line.write(user_wise_list[i][2])
#                                             else:
#                                                 record.write({"user_wise_id": user_wise_list})
#                                         else:
#                                             record.write({"active": False})
#
#
#
#     @api.model
#     def create_card_for_inventory_user(self):
#         model_names = []
#         users = self.env["res.users"].search([("id", ">", 0)])
#         names = self.env["inventory.user.dashboard.query"].search([("id", ">", 0)])
#         for name in names:
#             model_names.append(name.model_name)
#         model_names = set(model_names)
#         for user in users:
#             for company in user.company_ids:
#                 for name in model_names:
#                     self.env['inventory.user.dashboard'].create({"name": name, "user_id": user.id,
#                                                                      "company_id": company.id})
#
#     @api.multi
#     def compute_by_scheduler(self):
#         # print("ruuuuuuuuuuuuuuuuuuuuuuuunnnnnnnnnnnnn")
#         return {
#             'type': 'ir.actions.window',
#             'tag': 'reload',
#         }
#
#     def execute_query(self, label_name, emp_id):
#         list_query_obj = []
#         try:
#             user_id = self.env["hr.employee"].search([("id", "=", emp_id)]).user_id[0]
#             query = self.env["inventory.user.dashboard.query"].search([("model_name", "=", str(self.name)),
#                                                                            ("label_name", "=", label_name)]).query
#             company_id = self.env.user.company_id.id
#             if query:
#                 if label_name == 'total':
#                     query = str(query) + " where company_id=" + str(company_id) + " and create_uid=" + str(user_id.id)
#                 elif label_name == 'pending':
#                     query = str(query) + " and company_id=" + str(company_id) + " and create_uid=" + str(user_id.id)
#                     # print(query, "query")
#                 self.env.cr.execute(query)
#                 list_query_dict = self.env.cr.dictfetchall()
#                 for query_dict in list_query_dict:
#                     list_query_obj.append(self.env[self.name].search([("id", "=", query_dict["id"])]))
#             # print("list", list_query_obj)
#         except:
#             list_query_obj = []
#         return list_query_obj
#
#     def get_employee_child(self, emp_objs, emp_dict):
#         if emp_objs:
#             for emp_obj in emp_objs:
#                 emp_dict.update({emp_obj.id: {}})
#                 emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_obj.id)])
#                 emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_obj.id))
#                 if emp_obj and emp_id_val:
#                     emp_dict.get(emp_obj.id).update(emp_id_val)
#         else:
#             return emp_dict
#
#     def get_total(self, emp_dict):
#         val_user_dict1 = {
#             "total": 0,
#             "pending": 0,
#         }
#         for key, val in emp_dict.items():
#             val_user_dict = {
#                 "total": len(self.execute_query("total", key)),
#                 "pending": len(self.execute_query("pending", key)),
#                 }
#             if val:
#                 val_user_dict2 = self.get_total(val)
#                 val_user_dict["total"] = int(val_user_dict["total"]) + int(val_user_dict2["total"])
#                 val_user_dict["pending"] = int(val_user_dict["pending"]) + int(val_user_dict2["pending"])
#             if not val_user_dict["total"]:
#                 val_user_dict["total"] = 0
#             if not val_user_dict["pending"]:
#                 val_user_dict["pending"] = 0
#             val_user_dict1["total"] = int(val_user_dict1["total"]) + int(val_user_dict["total"])
#             val_user_dict1["pending"] = int(val_user_dict1["pending"]) + int(val_user_dict["pending"])
#         return val_user_dict1
#
#     def get_list_of_keys(self, emp_dict, emp_total, level):
#         for key, val in emp_dict.items():
#             total = len(self.execute_query("total", key))
#             pending = len(self.execute_query("pending", key))
#             if not total:
#                 total = 0
#             if not pending:
#                 pending = 0
#             emp_total.update({key: {"total": total, "pending": pending, "level": level}})
#             if val:
#                 val_dict = self.get_total(val)
#                 emp_total = self.get_list_of_keys(val, emp_total, level+1)
#                 if not val_dict["total"]:
#                     val_dict["total"] = 0
#                 if not val_dict["pending"]:
#                     val_dict["pending"] = 0
#                 emp_total.update({key: {"total": total + val_dict["total"], "pending": pending + val_dict["pending"],
#                                   "level": level}})
#         return emp_total
#
#
#     def get_obj_of_keys(self, emp_dict, obj_list):
#         for key, val in emp_dict.items():
#             # print("get obj of keys.....................LLLLLLLLLLLL")
#             # user_id = self.env["hr.employee"].search([("id", "=", key)]).user_id[0]
#             # print(self.name, "check")
#             objs =  objs = self.execute_query("total", key)
#             # print(objs,"gdgdgfghfgh")
#             # if len(objs) > 0:
#             for obj in objs:
#                 if obj.id:
#                     obj_list.append(obj.id)
#             # else:
#             #     if objs.id:
#             #         obj_list.append(objs.id)
#             if val:
#                 obj_list = self.get_obj_of_keys(val, obj_list)
#         return obj_list
#
#     @api.multi
#     def get_total_list_view(self):
#         obj_list = []
#         emp_dict = {}
#         result = {}
#         emp_id = self._context.get("emp_id")
#         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
#         # ravi at 4/4/2019 start
#         emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
#         # ravi at 4/4/2019
#         emp_dict.update({emp_id: {}})
#         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
#         if emp_id_val:
#             emp_dict.get(emp_id).update(emp_id_val)
#         obj_list = self.get_obj_of_keys(emp_dict, obj_list)
#         if self.name:
#             action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
#             res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
#             res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
#             result = action[0].read()[0]
#             result['views'] = [(res, 'list'), (res_form, 'form')]
#             result['domain'] = [('id', 'in', obj_list)]
#             result['target'] = 'main'
#         # ravi at 4/4/2018 start
#         if len(emp_id_user)<=0:
#             raise ValidationError(_('Please define employee for related user'))
#             return 0
#         else:
#             return result
#
#         # return result
#         # ravi at 4/4/2018 end
#
#     def get_delay_obj_of_keys(self, emp_dict, obj_list):
#         for key, val in emp_dict.items():
#             objs = self.execute_query("pending", key)
#             # if len(objs) > 0:
#             for obj in objs:
#                 if obj.id:
#                     obj_list.append(obj.id)
#             # else:
#             #     if objs[0].id:
#             #         obj_list.append(objs[0].id)
#             if val:
#                 obj_list = self.get_delay_obj_of_keys(val, obj_list)
#         return obj_list
#
#     @api.multi
#     def get_pending_list_view(self):
#         obj_list = []
#         emp_dict = {}
#         result = {}
#         emp_id = self._context.get("emp_id")
#         # print(emp_id)
#         # ravi at 4/4/2019 start
#         emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
#         # ravi at 4/4/2019
#         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
#         emp_dict.update({emp_id: {}})
#         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
#         if emp_id_val:
#             emp_dict.get(emp_id).update(emp_id_val)
#         obj_list = self.get_delay_obj_of_keys(emp_dict, obj_list)
#         if self.name:
#             action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
#             # print(self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))]), "obj")
#             res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
#             res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
#             result = action[0].read()[0]
#             result['views'] = [(res, 'list'), (res_form, 'form')]
#             result['domain'] = [('id', 'in', obj_list)]
#             result['target'] = 'main'
#         # ravi at 4/4/2018 start
#         if len(emp_id_user)<=0:
#             raise ValidationError(_('Please define employee for related user'))
#             return 0
#         else:
#             return result
#         # return result
#         # ravi at 4/4/2018 end
#
#     @api.multi
#     def change_view_type(self):
#         self.view_type = self._context.get("view_type")
#
#
# class InventoryUserDashboardQuery(models.Model):
#     _description = "Query Detail"
#     _name = "inventory.user.dashboard.query"
#
#     model_name = fields.Char("Model Name")
#     # type = fields.Selection([
#     #     ('activity_wise', 'Activity Wise'),
#     #     ('user_wise', 'User Wise')
#     # ], string="type")
#     label_name = fields.Char("Label Name")
#     query = fields.Text("Query")
#
#
#
# class InventoryUserDashboardUserWise(models.Model):
#     _description = "User Detail"
#     _name = "inventory.user.dashboard.user.wise"
#
#     emp_name = fields.Char("Name")
#     emp_id = fields.Integer("employee id")
#     user_wise_total = fields.Integer()
#     user_wise_pending = fields.Integer()
#     level = fields.Integer()
#     inventory_user_dashboard_id = fields.Many2one('inventory.user.dashboard', 'Inventory User dashboard')
#
#
# class InventoryUserDashboardUser(models.Model):
#     _name = "res.users"
#     _inherit = "res.users"
#
#     @api.model
#     def create(self, values):
#         model_names = []
#         # print("new user")
#         res = super(InventoryUserDashboardUser, self).create(values)
#         names = self.env["inventory.user.dashboard.query"].search([("id", ">", 0)])
#         for name in names:
#             model_names.append(name.model_name)
#         model_names = set(model_names)
#         for company in res.company_ids:
#             for name in model_names:
#                 # print(res.id, name, "user and name")
#                 self.env['inventory.user.dashboard'].sudo().create({"name": name, "user_id": res.id,
#                                                                          "company_id": company.id})
#         return res
#
#     @api.multi
#     def write(self, values):
#         model_names = []
#         if "company_ids" in values:
#             # print(values.get("company_ids"), "companyssssssssssss")
#             if values.get("company_ids")[0][2]:
#                 for company_id in values.get("company_ids")[0][2]:
#                     dashboard = self.env['inventory.user.dashboard'].search([("user_id","=", self.id), ("company_id","=", company_id)])
#                     if len(dashboard) == 0:
#                         names = self.env["inventory.user.dashboard.query"].search([("id", ">", 0)])
#                         for name in names:
#                             model_names.append(name.model_name)
#                         model_names = set(model_names)
#                         for name in model_names:
#                             self.env['inventory.user.dashboard'].sudo().create({"name": name, "user_id": self.id,
#                                                                              "company_id": company_id})
#
#         res = super(InventoryUserDashboardUser, self).write(values)
#         return res
#
#
# class InventoryUserDashboardEmployee(models.Model):
#     _name = "hr.employee"
#     _inherit = "hr.employee"
#
#     user_id = fields.Many2one('res.users', 'User', related='resource_id.user_id', store=True)
#
#     @api.multi
#     @api.onchange("user_id")
#     def onchange_code(self):
#         # print(self.user_id.id, "uuuuussssssssssser", self.company_id.id)
#         # print(self.user_id.company_id.id)
#         if self.user_id.id and self.company_id.id:
#             query = "select * from inventory_user_dashboard where user_id =" + str(self.user_id.id)\
#                     + "and company_id =" + str(self.company_id.id)
#             self.env.cr.execute(query)
#             dashboard = self.env.cr.dictfetchall()
#             for record in dashboard:
#                 obj = self.env['inventory.user.dashboard'].sudo().browse(record["id"])
#                 obj.write({"active": True})
#
#
