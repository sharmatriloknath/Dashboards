# -*- coding: utf-8 -*-

{
    "name" : "Sales Dashboard",
    "version" : "1.0",
    "depends" : ['web', 'crm_extension', 'sale'],
    "category" : "Sales Dashboard",
    "description": """
Sales Dashboard. This module adds:
""",
    "init_xml": [],
    "demo_xml": [],
    "data": [
            "security/ir.model.access.csv",
            "security/security_views.xml",
            "data/run_seed.xml",
            "views/sales_dashboard_view.xml",
            "views/sales_dashboard_query.xml",
            ],
'qweb': [
    ],
    "active": False,
    "installable": True
}
