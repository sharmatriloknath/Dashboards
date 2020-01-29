# from odoo import api, fields, models
#
#
# class PurchaseExtensionDashboardCron(models.Model):
# 		_description = "Cron Detail"
# 		_name = "hr.holidays.status.cron"
#
# 		time_interval = fields.name = fields.Selection([
# 		    (1, '1 day'),
# 		    (30, '30 days'),
# 		], string="Time Interval")
#
# 		@api.onchange('time_interval')
# 		def onchange_interval(self):
# 			model_id = self.env["ir.model"].search ([("model", "=", "hr.holidays.status")]).id
# 			cron = self.env["ir.cron"].sudo ().search ([("model_id", "=", model_id), ("user_id", "=", self.env.user.id)])
# 			if cron:
# 				cron.sudo ().write ({"interval_number": self.time_interval, "interval_type": "minutes"})
# 			else:
# 				cron.sudo ().create ({"name": "Leave Allocation", "state": "code", "user_id": self.env.user.id,
# 				                      "model_id": model_id, "interval_number": self.time_interval, "interval_type": "minutes",
# 				                      "priority": 0, "numbercall": 1, "active": True,
# 				                      "code": "model.run_scheduler_leaves_alloc()"})