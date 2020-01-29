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
import random


class SalesDashboard(models.Model):
    _description = "Sales Detail"
    _name = "sales.dashboard"

    active = fields.Boolean('Active', default=True, store=True)
    name = fields.Selection([
        ('crm.enquiry', 'Enquiries'),
        ('sale.quotation', 'Quotations'),
        ('sale.order', 'Sales Orders'),
        ('pick', 'Pick'),
        ('sale.agreement', 'Sale Agreement'),
        ('res.partner', 'Customers'),
        ('sale.agreement', 'Sale Agreement'),
        ('product.template', 'Finish Goods'),
        ('pack', 'Pack'),
        ('dispatch', 'Dispatch')

    ], string="Name")
    computation = fields.Char(compute="_computation")
    user_id = fields.Many2one('res.users', 'User')
    company_id = fields.Many2one('res.company', 'Company')
    total = fields.Integer("Total")
    pending = fields.Integer("Pending")
    sent = fields.Integer("Sent")
    color = fields.Integer('Color')
    view_type = fields.Boolean('Type', default=True)
    emp_id = fields.Integer("Employee Id")
    approved = fields.Integer("Approved")
    confirm = fields.Integer("Confirm")
    cancel = fields.Integer("Cancel")
    draft = fields.Integer("Draft")
    hsn = fields.Integer("Not Having HSN")
    not_validated = fields.Integer("Not Validated")
    no_email = fields.Integer("Not Email")
    ready = fields.Integer("Ready")
    partially = fields.Integer("Partially")
    amendment = fields.Integer("Amendment")

    @api.multi
    def _computation(self):
        for record in self:
            if record.user_id.id == self.env.user.id and record.company_id.id == record.env.user.company_id.id:
                record.env.cr.execute("select * from sales_dashboard_query where model_name='%s'" % (str(record.name)))
                model_data = record.env.cr.dictfetchall()
                if model_data:
                    complete_data = {}
                    for model in model_data:
                        complete_data[model['label_name']] = (self.execute_management_query(model))
                        record.sudo().write(
                            {
                                'total': len(complete_data.get('total', 0) if complete_data.get('total', 0) != 0 else []),
                                'pending': len(complete_data.get('pending', 0) if complete_data.get('pending', 0) != 0 else []),
                                'approved': len(complete_data.get('approved', 0) if complete_data.get('approved', 0) != 0 else []),
                                'sent': len(complete_data.get('sent', 0) if complete_data.get('sent', 0) != 0 else []),
                                'confirm': len(complete_data.get('confirm', 0) if complete_data.get('confirm', 0) != 0 else []),
                                'cancel': len(complete_data.get('cancel', 0) if complete_data.get('cancel', 0) != 0 else []),
                                'draft': len(complete_data.get('draft', 0) if complete_data.get('draft', 0) != 0 else []),
                                'hsn': len(complete_data.get('hsn', 0) if complete_data.get('hsn', 0) != 0 else []),
                                'not_validated': len(complete_data.get('not_validated', 0) if complete_data.get('not_validated', 0) != 0 else []),
                                'no_email': len(complete_data.get('no_email', 0) if complete_data.get('no_email', 0) != 0 else []),
                                'ready': len(complete_data.get('ready', 0) if complete_data.get('ready', 0) != 0 else []),
                                'partially': len(complete_data.get('partially', 0) if complete_data.get('partially', 0) != 0 else []),
                                'amendment': len(complete_data.get('amendment', 0) if complete_data.get('amendment', 0) != 0 else []),
                                'color': random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9])
                            }
                        )

    def execute_management_query(self, query_model):
        list_query_dict = {}
        company_id = self.env.user.company_id.id
        query = str(query_model["query"]) + str(company_id)
        if query:
            self.env.cr.execute(query)
            list_query_dict = self.env.cr.dictfetchall()
        return list_query_dict

    @api.model
    def create_card_for_sales_user(self):
        model_names = []
        users = self.env["res.users"].search([("id", ">", 0)])
        names = self.env["sales.dashboard.query"].search([("id", ">", 0)])
        for name in names:
            model_names.append(name.model_name)
        model_names = set(model_names)
        for user in users:
            for company in user.company_ids:
                for name in model_names:
                    self.env['sales.dashboard'].create({"name": name, "user_id": user.id,
                                                                     "company_id": company.id})

    @api.multi
    def compute_by_scheduler(self):
        return {
            'type': 'ir.actions.window',
            'tag': 'reload',
        }

    @api.multi
    def get_list_view(self):
        obj_list = []
        result = {}
        label_name = self._context.get("label_name")
        self.env.cr.execute("select * from sales_dashboard_query where model_name='%s' and label_name='%s'" % (str(self.name), label_name))
        model_data = self.env.cr.dictfetchall()
        if model_data:
            total_data = self.execute_management_query(model_data[0])
            if total_data:
                name = self.name
                if name in ['pick', 'pack', 'dispatch']:
                    name = 'stock.picking'
                if name == 'sale.order' and label_name == 'amendment':
                    name = 'sale.order.amend.new'
                for obj in total_data:
                    obj_list.append(self.env[name].search([("id", "=", obj["id"])]).id)
        if self.name:
            if self.name == 'sale.order':
                if label_name == 'amendment':
                    action = self.env.ref('crm_extension.action_sale_order_amend_new')
                else:
                    action = self.env.ref('crm_extension.action_orders_new')
            elif self.name == 'res.partner':
                action = self.env.ref('base.action_partner_form')
            elif self.name == 'pick':
                action = self.env.ref('crm_extension.action_picking_so_transfer')
            elif self.name == 'pack':
                action = self.env.ref('crm_extension.action_picking_arkes_pack')
            elif self.name == 'dispatch':
                action = self.env.ref('crm_extension.action_picking_arkes_dispatch_advice')
            else:
                action = self.env["ir.actions.act_window"].search([("res_model", "=", self.name)])
            if self.name == 'sale.quotation':
                res = self.env.ref('crm_extension.sale_quotation_tree').id
                res_form = self.env.ref('crm_extension.sale_quotation_form').id
            elif self.name == 'sale.order':
                if label_name == 'amendment':
                    res = self.env.ref('crm_extension.sale_order_amend_new_tree').id
                    res_form = self.env.ref('crm_extension.sale_order_amend_new_form').id
                else:
                    res = self.env.ref('sale.view_order_tree').id
                    res_form = self.env.ref('sale.view_order_form').id
            elif self.name == 'res.partner':
                res = self.env.ref('base.view_partner_tree').id
                res_form = self.env.ref('base.view_partner_form').id
            elif self.name == 'pick':
                res = self.env.ref('crm_extension.so_transfer_new_tree').id
                res_form = self.env.ref('crm_extension.view_stock_picking_transfer_so_form').id
            elif self.name == 'pack':
                res = self.env.ref('crm_extension.so_transfer_new_tree').id
                res_form = self.env.ref('crm_extension.view_stock_picking_pack_new_form').id
            elif self.name == 'dispatch':
                res = self.env.ref('crm_extension.so_transfer_new_tree').id
                res_form = self.env.ref('crm_extension.view_stock_picking_pack_new_form').id
            else:
                res = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "in", ("list", "tree"))])[0].id
                res_form = self.env["ir.ui.view"].search([("model", "=", self.name), ("type", "=", "form")])[0].id
            result = action[0].read()[0]
            result['views'] = [(res, 'list'), (res_form, 'form')]
            result['domain'] = [('id', 'in', obj_list)]
            result['target'] = 'current'
        return result

    @api.multi
    def change_view_type(self):
        self.view_type = self._context.get("view_type")


class SalesDashboardQuery(models.Model):
    _description = "Query Detail"
    _name = "sales.dashboard.query"

    model_name = fields.Char("Model Name")
    label_name = fields.Char("Label Name")
    query = fields.Text("Query")
    col_name = fields.Char("Column Name")

    @api.model
    def create(self, vals):
        if 'model_name' in vals and vals.get('model_name') and 'label_name' in vals and vals.get(
                'label_name') and 'query' in vals and vals.get('query'):
            data = self.env["sales.dashboard.query"].search(
                [('model_name', '=', vals.get('model_name')), ('label_name', '=', vals.get('label_name')),
                 ('query', '=', vals.get('query'))])
            if data:
                raise ValidationError("Record Already Exist....")

        res = super(SalesDashboardQuery, self).create(vals)

        user_dict = []
        names = []
        dynamic_db = self.env['sales.dashboard']
        objs = self.env["sales.dashboard"].search([('id', '>', 0)], order='id desc')
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


class SalesDashboardUser(models.Model):
    _name = "res.users"
    _inherit = "res.users"

    @api.model
    def create(self, values):
        model_names = []
        # print("new user")
        res = super(SalesDashboardUser, self).create(values)
        names = self.env["sales.dashboard.query"].search([("id", ">", 0)])
        for name in names:
            model_names.append(name.model_name)
        model_names = set(model_names)
        for company in res.company_ids:
            for name in model_names:
                self.env['sales.dashboard'].sudo().create({"name": name, "user_id": res.id,
                                                                         "company_id": company.id})
        return res

    @api.multi
    def write(self, values):
        model_names = []
        if "company_ids" in values:
            if values.get("company_ids")[0][2]:
                for company_id in values.get("company_ids")[0][2]:
                    dashboard = self.env['sales.dashboard'].search([("user_id","=", self.id), ("company_id","=", company_id)])
                    if len(dashboard) == 0:
                        names = self.env["sales.dashboard.query"].search([("id", ">", 0)])
                        for name in names:
                            model_names.append(name.model_name)
                        model_names = set(model_names)
                        for name in model_names:
                            self.env['sales.dashboard'].sudo().create({"name": name, "user_id": self.id,
                                                                             "company_id": company_id})

        res = super(SalesDashboardUser, self).write(values)
        return res

