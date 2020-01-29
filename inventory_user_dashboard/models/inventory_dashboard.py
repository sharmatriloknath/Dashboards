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


class InventoryUserDashboard(models.Model):
    _description = "Inventory Detail"
    _name = "inventory.user.dashboard"

    active = fields.Boolean('Active', default=True, store=True)
    name = fields.Selection([
        ('material.req.slip', 'MRS'),
        ('product.template', 'Items'),
        ('stock.warehouse.orderpoint', 'Reordering Rules'),
        ('receipt.at.gate', 'Receipt At Gate'),
        ('receipt.at.qc', 'Receipt At QC'),
        ('receipt.at.main', 'Receipt At Main'),
        ('material.issue', 'Material Issue'),
        ('rows.and.coloum', 'Bin'),

    ], string="Name")
    computation = fields.Char(compute="_computation")
    total = fields.Integer("Total")
    user_id = fields.Many2one('res.users', 'User')
    company_id = fields.Many2one('res.company', 'Company')
    pending = fields.Integer("Pending")
    color = fields.Integer('Color')
    view_type = fields.Boolean('Type', default=True)
    user_wise_id = fields.One2many("inventory.user.dashboard.user.wise", "inventory_user_dashboard_id")
    have_child = fields.Boolean('Have Child', default=False)
    emp_id = fields.Integer("Employee Id")
    validate = fields.Integer("Pending Validate")
    rejected = fields.Integer("Rejected Receipts")
    returns = fields.Integer("Pending Returns")
    verification = fields.Integer("Pending Vendor Verification")
    mstock = fields.Integer("Items Below Minimum Stock")
    hsn = fields.Integer("Items Without HSN")
    allocated = fields.Integer("Allocated Bin Count")
    unallocated = fields.Integer("No Bin Assigned")
    pallocated = fields.Integer("Partially Allocated")
    approved  = fields.Integer("Approved")
    trigger = fields.Integer("Rules Triggered")

    @api.multi
    def _computation(self):
        model_used = []
        emp_dict = {}
        emp_total = {}
        for record in self:
            if record.name not in model_used:
                model_used.append(record.name)
                user_id1 = self._context.get("uid")
                user = self.env['res.users'].browse(user_id1)

                '''This code is for Management who can see all the records because he has complete access rights'''
                if user.has_group('purchase_extension.group_stock_management'):
                    record.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s'" % (str(record.name)))
                    model_data = record.env.cr.dictfetchall()
                    if model_data:
                        complete_data = {}
                        for model in model_data:
                            complete_data[model['label_name']] = (self.execute_management_query(model))
                            record.sudo().write(
                                {
                                    'total': len(complete_data.get('total', 0) if complete_data.get('total', 0) != 0 else []),
                                    'pending': len(complete_data.get('pending', 0) if complete_data.get('pending',0) != 0 else []),
                                    'approved': len(complete_data.get('approved', 0) if complete_data.get('approved',0) != 0 else []),
                                    'rejected': len(complete_data.get('rejected', 0) if complete_data.get('rejected',0) != 0 else []),
                                    'validate': len(complete_data.get('validate', 0) if complete_data.get('validate',0) != 0 else []),
                                    'returns': len(complete_data.get('returns', 0) if complete_data.get('returns',0) != 0 else []),
                                    'verification': len(complete_data.get('verification', 0) if complete_data.get('verification',0) != 0 else []),
                                    'mstock': len(complete_data.get('mstock', 0) if complete_data.get('mstock',0) != 0 else []),
                                    'hsn': len(complete_data.get('hsn', 0) if complete_data.get('hsn',0) != 0 else []),
                                    'allocated': len(complete_data.get('allocated', 0) if complete_data.get('allocated',0) != 0 else []),
                                    'unallocated': len(complete_data.get('unallocated', 0) if complete_data.get('unallocated',0) != 0 else []),
                                    'pallocated': len(complete_data.get('pallocated', 0) if complete_data.get('pallocated',0) != 0 else []),
                                    'trigger': len(complete_data.get('trigger', 0) if complete_data.get('trigger',0) != 0 else []),
                                }
                            )

                else:
                    if record.user_id.id == self.env.user.id and record.company_id.id == record.env.user.company_id.id:
                        query = """select * from res_groups_users_rel where gid in (select id from res_groups where 
                                              category_id in (select id from ir_module_category where name ilike 'Purchases')) and uid=%s""" % (user.id)
                        record.env.cr.execute(query)
                        condition_satisfied = record.env.cr.fetchall()
                        if condition_satisfied:
                            if record.name != 'material.req.slip':
                                record.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s'" % (str(record.name)))
                                model_data = record.env.cr.dictfetchall()
                                if model_data:
                                    complete_data = {}
                                    for model in model_data:
                                        complete_data[model['label_name']] = (self.execute_management_query(model))
                                        record.sudo().write(
                                            {
                                                'total': len(complete_data.get('total', 0) if complete_data.get('total',0) != 0 else []),
                                                'pending': len(complete_data.get('pending', 0) if complete_data.get('pending',0) != 0 else []),
                                                'rejected': len(complete_data.get('rejected', 0) if complete_data.get('rejected',0) != 0 else []),
                                                'validate': len(complete_data.get('validate', 0) if complete_data.get('validate',0) != 0 else []),
                                                'returns': len(complete_data.get('returns', 0) if complete_data.get('returns',0) != 0 else []),
                                                'verification': len(complete_data.get('verification', 0) if complete_data.get('verification', 0) != 0 else []),
                                                'mstock': len(complete_data.get('mstock', 0) if complete_data.get('mstock',0) != 0 else []),
                                                'hsn': len(complete_data.get('hsn', 0) if complete_data.get('hsn',0) != 0 else []),
                                                'allocated': len(complete_data.get('allocated', 0) if complete_data.get('allocated',0) != 0 else []),
                                                'unallocated': len(complete_data.get('unallocated', 0) if complete_data.get('unallocated',0) != 0 else []),
                                                'pallocated': len(complete_data.get('pallocated', 0) if complete_data.get('pallocated',0) != 0 else []),
                                                'trigger': len(complete_data.get('trigger', 0) if complete_data.get('trigger',0) != 0 else []),
                                            }
                                        )
                            else:
                                # print(a)
                                user_wise_list = []
                                have_child = False
                                if record.name:
                                    emp_id = record.env["hr.employee"].search(
                                        [("user_id", "=", record.env.user.id)]).id
                                    if emp_id:
                                        emp_objs = record.env["hr.employee"].search([("parent_id", "=", emp_id)])
                                        if len(emp_objs) > 0:
                                            have_child = True
                                        emp_dict.update({emp_id: {}})
                                        emp_id_val = record.get_employee_child(emp_objs, emp_dict.get(emp_id))
                                        if emp_id_val:
                                            emp_dict.get(emp_id).update(emp_id_val)
                                        emp_total = record.get_list_of_keys(emp_dict, emp_total, 1)

                                        # shubham
                                        i = 2
                                        for key, val in emp_total.items():
                                            if emp_id == key:
                                                total = val.get("total")
                                                pending = val.get("pending")
                                                approved = val.get("approved")
                                                record.write(
                                                    {"total": total, "pending": pending, "have_child": have_child,
                                                     "emp_id": emp_id, "approved": approved})
                                                if pending == 0:
                                                    record.write({"color": 10})
                                                else:
                                                    record.write({"color": 9})
                                            user_wise = (0, False, {
                                                "emp_id": key,
                                                "emp_name": record.env["hr.employee"].search(
                                                    [("id", "=", key)]).name,
                                                "user_wise_total": val.get("total"),
                                                "user_wise_pending": val.get("pending"),
                                                "level": str(val.get('level')),
                                            })
                                            user_wise_list.append(user_wise)
                                        line_obj = record.env["inventory.user.dashboard.user.wise"].search(
                                            [("inventory_user_dashboard_id", "=", record.id)])
                                        if len(line_obj) > 0:
                                            # for i, line in enumerate(line_obj):
                                            #     line.write(user_wise_list[i][2])
                                            if len(line_obj) == len(user_wise_list):
                                                for i, line in enumerate(line_obj):
                                                    print("iiiiiiiiiiiiiiiiiiiiiiiiiii", i)
                                                    print("user_wise_listrrrrrr", user_wise_list)
                                                    line.sudo().write(user_wise_list[i][2])
                                            elif len(line_obj) > len(user_wise_list):
                                                for i, line in enumerate(line_obj):
                                                    try:
                                                        line.sudo().write(user_wise_list[i][2])
                                                    except:
                                                        query = "delete from inventory_user_dashboard_user_wise where id =" + str(line.id)
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
                                            record.write({"user_wise_id": user_wise_list})
                                    else:
                                        record.write({"active": False})

    def execute_management_query(self, query_model, emp_id=False, view_type=True):
        list_query_dict = {}
        company_id = self.env.user.company_id.id
        if view_type:
            query = str(query_model["query"]) + str(company_id)
        else:
            user_id = self.env["hr.employee"].search([("id", "=", emp_id)]).user_id[0]
            query = str(query_model["query"]) + str(company_id) + " and create_uid=" + str(user_id.id)
        self.env.cr.execute(query)
        list_query_dict = self.env.cr.dictfetchall()
        return list_query_dict

    @api.model
    def create_card_for_inventory_user(self):
        model_names = []
        users = self.env["res.users"].search([("id", ">", 0)])
        names = self.env["inventory.user.dashboard.query"].search([("id", ">", 0)])
        for name in names:
            model_names.append(name.model_name)
        model_names = set(model_names)
        for user in users:
            for company in user.company_ids:
                for name in model_names:
                    self.env['inventory.user.dashboard'].create({"name": name, "user_id": user.id,
                                                                     "company_id": company.id})

    @api.multi
    def compute_by_scheduler(self):
        return {
            'type': 'ir.actions.window',
            'tag': 'reload',
        }

    def execute_query(self, label_name, emp_id):
        list_query_obj = []
        # try:
        employee_id = self.env["hr.employee"].search([("id", "=", emp_id)])
        query = self.env["inventory.user.dashboard.query"].search([("model_name", "=", str(self.name)),
                                                                       ("label_name", "=", label_name)]).query
        company_id = self.env.user.company_id.id
        if employee_id:
            if employee_id.user_id:
                user_id = employee_id.user_id[0]
                if query:
                    if label_name:
                        query = str(query) + str(company_id) + " and create_uid=" + str(user_id.id)
                    self.env.cr.execute(query)
                    list_query_dict = self.env.cr.dictfetchall()
                    for query_dict in list_query_dict:
                        list_query_obj.append(self.env[self.name].search([("id", "=", query_dict["id"])]))
        # except:
        #     list_query_obj = []
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
            "approved":0
        }
        for key, val in emp_dict.items():
            val_user_dict = {
                "total": len(self.execute_query("total", key)),
                "pending": len(self.execute_query("pending", key)),
                "approved": len(self.execute_query("approved", key)),
                }
            if val:
                val_user_dict2 = self.get_total(val)
                val_user_dict["total"] = int(val_user_dict["total"]) + int(val_user_dict2["total"])
                val_user_dict["pending"] = int(val_user_dict["pending"]) + int(val_user_dict2["pending"])
                val_user_dict["approved"] = int(val_user_dict["approved"]) + int(val_user_dict2["approved"])
            if not val_user_dict["total"]:
                val_user_dict["total"] = 0
            if not val_user_dict["pending"]:
                val_user_dict["pending"] = 0
            if not val_user_dict["approved"]:
                val_user_dict["approved"] = 0
            val_user_dict1["total"] = int(val_user_dict1["total"]) + int(val_user_dict["total"])
            val_user_dict1["pending"] = int(val_user_dict1["pending"]) + int(val_user_dict["pending"])
            val_user_dict1["approved"] = int(val_user_dict1["approved"]) + int(val_user_dict["approved"])
        return val_user_dict1

    def get_list_of_keys(self, emp_dict, emp_total, level):
        for key, val in emp_dict.items():
            total = len(self.execute_query("total", key))
            pending = len(self.execute_query("pending", key))
            approved = len(self.execute_query("approved", key))
            if not total:
                total = 0
            if not pending:
                pending = 0
            if not approved:
                approved = 0
            emp_total.update({key: {"total": total, "pending": pending, "level": level, "approved": approved}})
            if val:
                val_dict = self.get_total(val)
                emp_total = self.get_list_of_keys(val, emp_total, level+1)
                if not val_dict["total"]:
                    val_dict["total"] = 0
                if not val_dict["pending"]:
                    val_dict["pending"] = 0
                if not val_dict["approved"]:
                    val_dict["approved"] = 0
                emp_total.update({key: {"total": total + val_dict["total"], "pending": pending + val_dict["pending"],
                                  "level": level, "approved": approved + val_dict["approved"]}})
        return emp_total

    @api.multi
    def get_data_for_view(self):
        obj_list = []
        result = {}
        emp_id = self._context.get("emp_id")
        label_name = self._context.get("label_name")
        # print("the value in the emp_id is", emp_id)
        # print("the value in the label_name is", label_name)
        self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
                            "and label_name='%s'" % (str(self.name), label_name))
        model_data = self.env.cr.dictfetchall()
        if model_data:
            total_data = self.execute_management_query(model_data[0], emp_id)
            if total_data:
                if self.name:
                    name = self.name
                    if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
                        name = 'stock.picking'
                    elif name == 'rows.and.coloum' and label_name in ['unallocated', 'pallocated']:
                        name = 'product.product'
                    elif name == 'product.template' and label_name == 'mstock':
                        name = 'product.product'
                for obj in total_data:
                    obj_list.append(self.env[name].search([("id", "=", obj["id"])]))
        if self.name:
            name = self.name
            if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
                name = 'stock.picking'

            elif name == 'rows.and.coloum' and label_name in ['unallocated', 'pallocated']:
                name = 'product.product'

            elif name == 'product.template' and label_name == 'mstock':
                name = 'product.product'

            if self.name == 'receipt.at.gate':
                action = self.env["ir.actions.act_window"].search([("res_model", "=", name), ("name", "=", "Receipt At Gate")])
            elif self.name == 'receipt.at.qc':
                action = self.env["ir.actions.act_window"].search([("res_model", "=", name), ("name", "=", "Quality Receipts")])
            elif self.name == 'receipt.at.main':
                action = self.env["ir.actions.act_window"].search([("res_model", "=", name), ("name", "=", "Main Store Receipts")])
            elif self.name == 'stock.warehouse.orderpoint':
                # action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
                action = self.env.ref('stock.action_orderpoint_form')
            elif self.name == 'product.template' and label_name != 'mstock':
                action = self.env["ir.actions.act_window"].search([("res_model", "=", name), ("name", '=', 'Raw Material')])
            elif self.name == 'product.template' and label_name == 'mstock':
                action = self.env["ir.actions.act_window"].search(
                    [("res_model", "=", name), ("name", '=', 'Item Variants Raw Materials')])
            else:
                action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])

            if name == 'product.product' and label_name in ['unallocated', 'pallocated']:
                # res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree")), ('id','=', 2381)]).id
                res = self.env.ref('purchase_extension.view_assign_location_product_wise_tree').id
                # res_form = self.env.ref('purchase_extension.wizard_assign_location_product_wise').id

            elif self.name == 'receipt.at.qc':
                res = self.env.ref('purchase_extension.view_quality_picking_tree').id
                res_form = self.env.ref('purchase_extension.view_stock_picking_quality_check_form').id

            elif self.name == 'receipt.at.gate':
                res = self.env.ref('purchase_extension.view_incoming_shipment_gate_tree').id
                res_form = self.env.ref('purchase_extension.view_stock_picking_gate_new_form').id

            elif self.name == 'receipt.at.main':
                res = self.env.ref('purchase_extension.view_main_store_picking_tree').id
                res_form = self.env.ref('purchase_extension.view_stock_picking_main_store_form').id

            else:
                res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
                res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
            result = action[0].read()[0]
            # Because Assign Location has No Form View That is why this check is.
            if name == 'product.product' and label_name in ['unallocated', 'pallocated']:
                result['views'] = [(res, 'list')]
            else:
                result['views'] = [(res, 'list'), (res_form, 'form')]
            result['domain'] = [('id', 'in', [val.id for val in obj_list])]
            result['target'] = 'current'
            # result['domain'] = [('id', 'in', obj_list)]
            # print("the value  in hte ojh", obj_list)
        return result

    @api.multi
    def get_list_view(self):
        obj_list = []
        emp_dict = {}
        result = {}
        emp_id = self._context.get("emp_id")
        label_name = self._context.get("label_name")
        # print("the value in the contest is", emp_id)
        # print("the value in the string valule is", label_name)
        view = self.view_type
        user = self.env.user
        emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
        emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
        emp_dict.update({emp_id: {}})
        if self.name:
            name = self.name
            if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
                name = 'stock.picking'

            elif name =='rows.and.coloum' and label_name in ['unallocated', 'pallocated']:
                name = 'product.product'

            elif name == 'product.template' and label_name == 'mstock':
                name = 'product.product'

        if self.name == 'material.req.slip':
            emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
            if emp_id_val:
                emp_dict.get(emp_id).update(emp_id_val)
            obj_list = self.get_data_of_keys(emp_dict, obj_list, label_name)
        else:
            self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
                                "and label_name='%s'" % (str(self.name), label_name))
            model_data = self.env.cr.dictfetchall()
            if model_data:
                total_data = self.execute_management_query(model_data[0], emp_id, view_type=view)
                if total_data:
                    for obj in total_data:
                        obj_list.append(self.env[name].search([("id", "=", obj["id"])]).id)
                    # print("the value in the obj_list other models ", obj_list)
        if name:
            if self.name == 'receipt.at.gate':
                action = self.env["ir.actions.act_window"].search([("res_model", "=", name), ("name", "=", "Receipt At Gate")])
            elif self.name == 'receipt.at.qc':
                action = self.env["ir.actions.act_window"].search([("res_model", "=", name), ("name", "=", "Quality Receipts")])
            elif self.name == 'receipt.at.main':
                action = self.env["ir.actions.act_window"].search([("res_model", "=", name), ("name", "=", "Main Store Receipts")])
            elif self.name == 'stock.warehouse.orderpoint':
                # action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
                action = self.env.ref('stock.action_orderpoint_form')
            elif self.name == 'product.template' and label_name != 'mstock':
                action = self.env["ir.actions.act_window"].search([("res_model", "=", name), ("name", '=', 'Raw Material')])
            elif self.name == 'material.req.slip':
                action = self.env.ref('purchase_extension.action_material_req_slip')
            else:
                action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])

            if self.name == 'receipt.at.qc':
                res = self.env.ref('purchase_extension.view_quality_picking_tree').id
                res_form = self.env.ref('purchase_extension.view_stock_picking_quality_check_form').id

            elif self.name == 'receipt.at.gate':
                res = self.env.ref('purchase_extension.view_incoming_shipment_gate_tree').id
                res_form = self.env.ref('purchase_extension.view_stock_picking_gate_new_form').id

            elif self.name == 'receipt.at.main':
                res = self.env.ref('purchase_extension.view_main_store_picking_tree').id
                res_form = self.env.ref('purchase_extension.view_stock_picking_main_store_form').id
            else:
                res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
                res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
            result = action[0].read()[0]
            result['views'] = [(res, 'list'), (res_form, 'form')]
            result['domain'] = [('id', 'in', obj_list)]
            result['target'] = 'current'
        return result

    def get_data_of_keys(self, emp_dict, obj_list, label_name):
        for key, val in emp_dict.items():
            objs = self.execute_query(label_name, key)
            for obj in objs:
                if obj.id:
                    obj_list.append(obj.id)
            if val:
                obj_list = self.get_data_of_keys(val, obj_list, label_name)
        return obj_list

    @api.multi
    def change_view_type(self):
        self.view_type = self._context.get("view_type")

    # def get_obj_of_keys(self, emp_dict, obj_list):
    #     for key, val in emp_dict.items():
    #         objs = self.execute_query("total", key)
    #         for obj in objs:
    #             if obj.id:
    #                 obj_list.append(obj.id)
    #         if val:
    #             obj_list = self.get_obj_of_keys(val, obj_list)
    #     return obj_list
    #
    # @api.multi
    # def get_total_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     label_name = self._context.get("label_name")
    #     print("the value in the contest is", emp_id)
    #     print("the value in the stirtng valule is", label_name)
    #     view = self.view_type
    #     user = self.env.user
    #     emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #     # emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
    #     emp_dict.update({emp_id: {}})
    #     if self.name == 'material.req.slip':
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list)
    #     else:
    #         self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), label_name))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], emp_id, view_type=view)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', obj_list)]
    #         result['target'] = 'current'
    #     # if len(emp_id_user) <= 0:
    #     #     raise ValidationError(_('Please define employee for related user'))
    #     #     return 0
    #     # else:
    #     #     return result
    #     return result
    #
    # def get_delay_obj_of_keys(self, emp_dict, obj_list):
    #     for key, val in emp_dict.items():
    #         objs = self.execute_query("pending", key)
    #         # if len(objs) > 0:
    #         for obj in objs:
    #             if obj.id:
    #                 obj_list.append(obj.id)
    #         # else:
    #         #     if objs[0].id:
    #         #         obj_list.append(objs[0].id)
    #         if val:
    #             obj_list = self.get_delay_obj_of_keys(val, obj_list)name_get
    #     return obj_list
    #
    # @api.multi
    # def get_pending_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     view = self.view_type
    #     user = self.env.user
    #     emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #     # emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
    #     emp_dict.update({emp_id: {}})
    #     if self.name == 'material.req.slip':
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_delay_obj_of_keys(emp_dict, obj_list)
    #     else:
    #         self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'pending'))
    #         model_data = self.env.cr.dictfetchall()
    #         if self.name:
    #             name = self.name
    #             if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #                 name = 'stock.picking'
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], emp_id, view_type=view)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', obj_list)]
    #         result['target'] = 'current'
    #     # if len(emp_id_user) <= 0:
    #     #     raise ValidationError(_('Please define employee for related user'))
    #     #     return 0
    #     # else:
    #     #     return result
    #     return result
    #
    # @api.multi
    # def get_pending_validate_list_view(self):
    #     obj_list = []
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'validate'))
    #     model_data = self.env.cr.dictfetchall()
    #     if model_data:
    #         total_data = self.execute_management_query(model_data[0], emp_id)
    #         if total_data:
    #             for obj in total_data:
    #                 obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_allocated_list_view(self):
    #     obj_list = []
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'allocated'))
    #     model_data = self.env.cr.dictfetchall()
    #     if model_data:
    #         total_data = self.execute_management_query(model_data[0], emp_id)
    #         if total_data:
    #             for obj in total_data:
    #                 obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_unallocated_list_view(self):
    #     obj_list = []
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'unallocated'))
    #     model_data = self.env.cr.dictfetchall()
    #     if model_data:
    #         total_data = self.execute_management_query(model_data[0], emp_id)
    #         if total_data:
    #             for obj in total_data:
    #                 obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_pallocated_list_view(self):
    #     obj_list = []
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'pallocated'))
    #     model_data = self.env.cr.dictfetchall()
    #     if model_data:
    #         total_data = self.execute_management_query(model_data[0], emp_id)
    #         if total_data:
    #             for obj in total_data:
    #                 obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_triggered_list_view(self):
    #     obj_list = []
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'trigger'))
    #     model_data = self.env.cr.dictfetchall()
    #     if model_data:
    #         total_data = self.execute_management_query(model_data[0], emp_id)
    #         if total_data:
    #             for obj in total_data:
    #                 obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_pending_returns_list_view(self):
    #     obj_list = []
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'returns'))
    #     model_data = self.env.cr.dictfetchall()
    #     if model_data:
    #         total_data = self.execute_management_query(model_data[0], emp_id)
    #         if total_data:
    #             for obj in total_data:
    #                 obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_verification_list_view(self):
    #     obj_list = []
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'verification'))
    #     model_data = self.env.cr.dictfetchall()
    #     if model_data:
    #         total_data = self.execute_management_query(model_data[0], emp_id)
    #         if total_data:
    #             for obj in total_data:
    #                 obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_rejected_list_view(self):
    #     obj_list = []
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'rejected'))
    #     model_data = self.env.cr.dictfetchall()
    #     if model_data:
    #         total_data = self.execute_management_query(model_data[0], emp_id)
    #         if total_data:
    #             for obj in total_data:
    #                 obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_without_hsn_list_view(self):
    #     obj_list = []
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'hsn'))
    #     model_data = self.env.cr.dictfetchall()
    #     if model_data:
    #         total_data = self.execute_management_query(model_data[0], emp_id)
    #         if total_data:
    #             for obj in total_data:
    #                 obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_below_minimum_stock_list_view(self):
    #     obj_list = []
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (str(self.name), 'mstock'))
    #     model_data = self.env.cr.dictfetchall()
    #     if model_data:
    #         total_data = self.execute_management_query(model_data[0], emp_id)
    #         if total_data:
    #             for obj in total_data:
    #                 obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         if name in ['receipt.at.gate', 'receipt.at.qc', 'receipt.at.main']:
    #             name = 'stock.picking'
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result
    #
    # @api.multi
    # def get_approved_list_view(self):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     emp_id = self._context.get("emp_id")
    #     view = self.view_type
    #     user = self.env.user
    #     emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #     # emp_id_user = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
    #     emp_dict.update({emp_id: {}})
    #     if self.name == 'material.req.slip':
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_approved_of_keys(emp_dict, obj_list)
    #     else:
    #         self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                             "and label_name='%s'" % (str(self.name), 'approved'))
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], emp_id, view_type=view)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     if self.name:
    #         name = self.name
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", name)])
    #         res = self.env["ir.ui.view"].search([("model", "=", name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', obj_list)]
    #         result['target'] = 'current'
    #     return result
    #
    # def get_approved_of_keys(self, emp_dict, obj_list):
    #     for key, val in emp_dict.items():
    #         objs = self.execute_query("approved", key)
    #         for obj in objs:
    #             if obj.id:
    #                 obj_list.append(obj.id)
    #         if val:
    #             obj_list = self.get_approved_of_keys(val, obj_list)
    #     return obj_list
    #
    # @api.multi
    # def get_dynamic_javascript_label_view(self, emp_id, model_name, label_name):
    #     obj_list = []
    #     emp_dict = {}
    #     result = {}
    #     user = self.env.user
    #     self.env.cr.execute("select * from inventory_user_dashboard_query where model_name='%s' "
    #                         "and label_name='%s'" % (model_name, label_name))
    #
    #     if user.has_group('purchase_extension.group_purchase_management'):
    #         model_dict = {}
    #         model_data = self.env.cr.dictfetchall()
    #         if model_data:
    #             total_data = self.execute_management_query(model_data[0], emp_id)
    #             if total_data:
    #                 for obj in total_data:
    #                     obj_list.append(self.env[self.name].search([("id", "=", obj["id"])]))
    #     else:
    #         # emp_id = self._context.get("emp_id")
    #         emp_objs = self.env["hr.employee"].search([("parent_id", "=", emp_id)])
    #         emp_dict.update({emp_id: {}})
    #         emp_id_val = self.get_employee_child(emp_objs, emp_dict.get(emp_id))
    #         if emp_id_val:
    #             emp_dict.get(emp_id).update(emp_id_val)
    #         obj_list = self.get_obj_of_keys(emp_dict, obj_list, type=label_name)
    #     if model_name:
    #         action = self.env["ir.actions.act_window"].search([("res_model", "=", model_name)])
    #         res = self.env["ir.ui.view"].search([("model", "=",model_name), ("type", "in", ("list", "tree"))])[0].id
    #         res_form = self.env["ir.ui.view"].search([("model", "=", model_name), ("type", "=", "form")])[0].id
    #         result = action[0].read()[0]
    #         result['views'] = [(res, 'list'), (res_form, 'form')]
    #         result['domain'] = [('id', 'in', [val.id for val in obj_list])]
    #         result['target'] = 'current'
    #     return result


class InventoryUserDashboardQuery(models.Model):
    _description = "Query Detail"
    _name = "inventory.user.dashboard.query"

    model_name = fields.Char("Model Name")
    # type = fields.Selection([
    #     ('activity_wise', 'Activity Wise'),
    #     ('user_wise', 'User Wise')
    # ], string="type")
    label_name = fields.Char("Label Name")
    query = fields.Text("Query")
    col_name = fields.Char("Column Name")

    @api.model
    def create(self, vals):
        if 'model_name' in vals and vals.get('model_name') and 'label_name' in vals and vals.get(
                'label_name') and 'query' in vals and vals.get('query'):
            data = self.env["inventory.user.dashboard.query"].search(
                [('model_name', '=', vals.get('model_name')), ('label_name', '=', vals.get('label_name')),
                 ('query', '=', vals.get('query'))])
            if data:
                raise ValidationError("Record Already Exist....")

        res = super(InventoryUserDashboardQuery, self).create(vals)

        user_dict = []
        names = []
        dynamic_db = self.env['inventory.user.dashboard']
        objs = self.env["inventory.user.dashboard"].search([('id', '>', 0)], order='id desc')
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


class InventoryUserDashboardUserWise(models.Model):
    _description = "User Detail"
    _name = "inventory.user.dashboard.user.wise"

    emp_name = fields.Char("Name")
    emp_id = fields.Integer("employee id")
    user_wise_total = fields.Integer()
    user_wise_pending = fields.Integer()
    level = fields.Integer()
    inventory_user_dashboard_id = fields.Many2one('inventory.user.dashboard', 'Inventory User dashboard')


class InventoryUserDashboardUser(models.Model):
    _name = "res.users"
    _inherit = "res.users"

    @api.model
    def create(self, values):
        model_names = []
        # print("new user")
        res = super(InventoryUserDashboardUser, self).create(values)
        names = self.env["inventory.user.dashboard.query"].search([("id", ">", 0)])
        for name in names:
            model_names.append(name.model_name)
        model_names = set(model_names)
        for company in res.company_ids:
            for name in model_names:
                # print(res.id, name, "user and name")
                self.env['inventory.user.dashboard'].sudo().create({"name": name, "user_id": res.id,
                                                                         "company_id": company.id})
        return res

    @api.multi
    def write(self, values):
        model_names = []
        if "company_ids" in values:
            # print(values.get("company_ids"), "companyssssssssssss")
            if values.get("company_ids")[0][2]:
                for company_id in values.get("company_ids")[0][2]:
                    dashboard = self.env['inventory.user.dashboard'].search([("user_id","=", self.id), ("company_id","=", company_id)])
                    if len(dashboard) == 0:
                        names = self.env["inventory.user.dashboard.query"].search([("id", ">", 0)])
                        for name in names:
                            model_names.append(name.model_name)
                        model_names = set(model_names)
                        for name in model_names:
                            self.env['inventory.user.dashboard'].sudo().create({"name": name, "user_id": self.id,
                                                                             "company_id": company_id})

        res = super(InventoryUserDashboardUser, self).write(values)
        return res


class InventoryUserDashboardEmployee(models.Model):
    _name = "hr.employee"
    _inherit = "hr.employee"

    user_id = fields.Many2one('res.users', 'User', related='resource_id.user_id', store=True)

    @api.multi
    @api.onchange("user_id")
    def onchange_code(self):
        # print(self.user_id.id, "uuuuussssssssssser", self.company_id.id)
        # print(self.user_id.company_id.id)
        if self.user_id.id and self.company_id.id:
            query = "select * from inventory_user_dashboard where user_id =" + str(self.user_id.id)\
                    + "and company_id =" + str(self.company_id.id)
            self.env.cr.execute(query)
            dashboard = self.env.cr.dictfetchall()
            for record in dashboard:
                obj = self.env['inventory.user.dashboard'].sudo().browse(record["id"])
                obj.write({"active": True})


