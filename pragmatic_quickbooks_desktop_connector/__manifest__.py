{
    'name': 'Odoo QuickBooks Desktop (QBD) Connector',
    'version': '17.0.1.9',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'www.pragtech.co.in',
    'category': 'Sales, Invoice',
    'summary': 'Synchronise data between Odoo and Quickbooks Desktop. Odoo Quickbooks Desktop Connector Odoo Quickbooks Desktop connector Quickbooks Odoo Quickbooks Odoo connector odoo quickbooks integration',
    'description': """
QuickBooks Desktop Odoo (QBD) Connector
=======================================
This connector will help user to import/export following objects in quickbooks.
    * Accounts
    * Customer
    * Product
    * Bill of Material
    * Sales Order
    * Invoices.
<keywords>
Odoo Quickbooks Desktop Connector
Odoo Quickbooks
Odoo Quickbooks Desktop 
Quickbooks
Quickbooks desktop
Quickbooks desktop connector
Quickbooks Odoo
Quickbooks Odoo connector
odoo quickbooks integration
    """,
    'depends': ['base', 'mrp', 'contacts', 'sale_management', 'base_setup', 'account', 'stock', 'purchase', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'data/shipping_method_product.xml',
        'data/tax_group_data.xml',
        'views/res_company_views.xml',
        'views/ir_sequence.xml',
        'views/account_view.xml',
        'views/res_partner_view.xml',
        'views/product_view.xml',
        'views/sale_order_view.xml',
        'views/qbd_payment_method_view.xml',
        'views/qbd_tax_code_view.xml',
        'views/invoice.xml',
        'views/purchase_view.xml',
        'views/qbd_logger.xml',
        'views/serveractions.xml',
        'views/schedular.xml',
        'views/inventory_cron.xml',
        'wizards/message_view.xml',
        'views/shipping_method.xml',
        'views/sales_person.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pragmatic_quickbooks_desktop_connector/static/src/style.css',
        ],
    },
    'live_test_url': 'http://www.pragtech.co.in/company/proposal-form.html?id=103&name=quickbook-connector',
    'images': ['images/animated-quickbook-desktop.gif'],
    'price': 300,
    'currency': 'USD',
    'license': 'OPL-1',
    'auto_install': False,
    'application': False,
    'installable': True,
}
