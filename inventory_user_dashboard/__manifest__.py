# -*- coding: utf-8 -*-

{
    "name" : "INVENTORY USER DASHBOARD",
    "version" : "1.0",
    "depends" : ['web', 'purchase','purchase_extension','stock','stock_landed_costs','mrp'],
    "category" : "Inventory",
    "description": """
Inventory User Dashboard. This module adds:
  * Create MRS. 
""",
    "init_xml": [],
    "demo_xml": [],
    "data": [
            "data/run_seed.xml",
            "security/ir.model.access.csv",
            "security/security_views.xml",
            "views/user_dashboard_view.xml",
            "views/user_dashboard_query_view.xml",
            "views/inventory_dashboard_cron_view.xml",
            ],
'qweb': [
    ],
    "active": False,
    "installable": True
}
