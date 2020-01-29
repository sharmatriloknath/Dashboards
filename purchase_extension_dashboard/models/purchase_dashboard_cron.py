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


class PurchaseExtensionDashboardCron(models.Model):
    _description = "Cron Detail"
    _name = "purchase.extension.dashboard.cron"

    time_interval = fields.Selection([
        (1, '1 minutes'),
        (30, '30 minutes'),
        (60, '60 minutes'),
        (90, '90 minutes'),
        (120, '120 minutes'),
    ], string="Time Interval")

    @api.multi
    @api.onchange('time_interval')
    def onchange_interval(self):
        model_id = self.env["ir.model"].search([("model", "=", "purchase.dynamic.dashboard")]).id
        cron = self.env["ir.cron"].sudo().search([("model_id", "=", model_id), ("user_id", "=", self.env.user.id)])
        if cron:
            cron.sudo().write({"interval_number": self.time_interval, "interval_type": "minutes"})
        else:
            cron.sudo().create({"name": "update purchase dashboard", "state": "code", "user_id": self.env.user.id,
                         "model_id": model_id, "interval_number": self.time_interval, "interval_type": "minutes",
                         "priority": 5, "numbercall": -1, "active": True,
                         "code": "model.compute_by_scheduler()"})

    @api.model
    def create(self, values):
        interval = self.env["purchase.extension.dashboard.cron"].search([("create_uid", "=", self.env.user.id)])
        if interval:
            raise ValidationError(_('Time Interval already exist!'))
        return super(PurchaseExtensionDashboardCron, self).create(values)



