# -*- coding: utf-8 -*-

{
    "name" : "PURCHASE DASHBOARD",
    "version" : "1.0",
    "depends" : ['web', 'purchase','purchase_extension','stock','stock_landed_costs', 'product_extension'],
    "category" : "Purchase",
    "description": """
Purchase Extension Dashboard. This module adds:
  * Create MRS. 
""",
    "init_xml": [],
    "demo_xml": [],
    "data": [
            "data/run_seed.xml",
            "security/ir.model.access.csv",
            "security/security_views.xml",
            # "views/purchase_dashboard_query_view.xml",
            "views/dynamic_dashboard.xml",
            "views/dynamic_query.xml",
            "views/purchase_dashboard_cron_view.xml",
            # "data/purchase_dashboard_refresher.xml",
            ],
'qweb': [
    ],
    "active": False,
    "installable": True
}
