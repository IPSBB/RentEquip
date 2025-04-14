from unicodedata import name
from odoo import api, fields, models, _
import requests
import ast
import json
from datetime import datetime, timedelta
import time
from odoo.exceptions import UserError, ValidationError
import re
import logging
from dateutil.parser import *

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def action_pos_session_closing_control(self):
        """
        Override the method to include export logic when closing a POS session.
        Use specific filters for session closing export.
        """
        # Call the super method to perform the original closing control logic
        # Either catch the parameter from function arguments or pass no parameters
        res = super(PosSession, self).action_pos_session_closing_control()

        # Get the current company
        company = self.env.user.company_id

        # Only allow for specific company
        if company.name != 'Fasteners Barbados Ltd.':
            return res

        # Get the current date
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Prepare filters specifically for session closing
        filters = [
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('date_order', '>=', f"{current_date} 00:00:00"),
            ('date_order', '<=', f"{current_date} 23:59:59"),
            ('quickbooks_id', '=', False),
            ('session_id', '=', self.id)  # Ensure orders belong to the current session
        ]

        # Get export limits from company configuration
        limit = int(company.export_pos_limit) if hasattr(company,
                                                         'export_pos_limit') and company.export_pos_limit else 100

        # Find orders to export
        orders = self.env['pos.order'].search(filters, limit=limit)

        # Export the filtered POS orders if any exist
        if orders:
            orders.export_pos_orders(export_context='session_close')

        return res

class PointOfSale(models.Model):
    _inherit = "pos.order"

    quickbooks_id = fields.Char("Quickbook id ", copy=False)
    sale_no = fields.Char('QBD Sale No.', copy=False)
    invoice_no = fields.Char('QBD Invoice No.', copy=False)

    def export_pos_orders(self, order_id=False, export_context='manual'):
        print("in the export_pos_ordersssssssssssssssssssssssssssss")
        """
        Export POS orders to QuickBooks Desktop
        Consolidates orders by date for paid/done orders
        Exports invoiced orders as QuickBooks invoices

        :param order_id: Optional specific order ID to export
        :return: True if successful
        """
        paid_order_data_list = []
        invoiced_order_data_list = []
        loger_dict = {}

        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id

        # Only allow for specific company
        if company.name != 'Fasteners Barbados Ltd.':
            raise UserError(_("QuickBooks integration is only available for Fasteners Barbados Ltd."))

        # Verify URL is configured properly
        if not company.url:
            raise UserError(_("QuickBooks URL is not configured. Please set the URL in company settings."))

        # Ensure URL is a string and properly formatted
        qb_url = str(company.url) if company.url else ""
        if qb_url.endswith('/'):
            qb_url = qb_url[:-1]

        if not qb_url:
            raise UserError(_("QuickBooks URL is not properly configured. Please check the URL in company settings."))

        # DEBUG: Inspect date formats
        # First, check a few sample POS orders to understand date format
        sample_orders = self.search([('state', 'in', ['paid', 'done', 'invoiced'])], limit=5)
        if sample_orders:
            print("====== DEBUG: SAMPLE POS ORDER DATES ======")
            for order in sample_orders:
                print(f"Order ID: {order.id}")
                print(f"  date_order raw value: {order.date_order}")
                print(f"  date_order type: {type(order.date_order)}")
                print(f"  date_order as string: {str(order.date_order)}")
                if hasattr(order.date_order, 'strftime'):
                    print(f"  date_order formatted: {order.date_order.strftime('%Y-%m-%d %H:%M:%S')}")
            print("==========================================")

        # DEBUG: Check company date format
        print("====== DEBUG: COMPANY DATE SETTINGS ======")
        if hasattr(company, 'export_pos_order_date'):
            print(f"export_pos_order_date: {company.export_pos_order_date}")
            print(f"export_pos_order_date type: {type(company.export_pos_order_date)}")
        if hasattr(company, 'export_pos_order_end_date'):
            print(f"export_pos_order_end_date: {company.export_pos_order_end_date}")
            print(f"export_pos_order_end_date type: {type(company.export_pos_order_end_date)}")
        print("==========================================")

        # Prepare filters based on export context
        if export_context == 'manual':
            # Initialize base filters
            filters = [
                ('state', 'in', ['paid', 'done', 'invoiced'])
            ]

            # Check for updated records if configured
            if hasattr(company, 'export_updated_record') and company.export_updated_record:
                filters.append(('quickbooks_id', '!=', False))
                filters.append(('is_updated', '=', True))
            else:
                # Default to only unexported orders
                filters.append(('quickbooks_id', '=', False))

            # Check for date range with datetime fields, fixing format confusion
            if hasattr(company, 'export_pos_order_date') and company.export_pos_order_date:
                try:
                    # Get the datetime objects from the company fields
                    start_date = company.export_pos_order_date

                    # Check for date format confusion (MM/DD vs DD/MM)
                    # If start_date is in September (month 9) but UI shows April (04),
                    # we need to swap month and day
                    if start_date.month > 12 or (start_date.month == 9 and start_date.day == 4):
                        # Create a new datetime with month and day swapped
                        start_date = datetime(start_date.year, start_date.day, start_date.month,
                                              start_date.hour, start_date.minute, start_date.second)
                        print(f"Start date adjusted for format confusion: {start_date}")

                    # Check if end date is set, otherwise use start date + 23:59:59
                    if hasattr(company, 'export_pos_order_end_date') and company.export_pos_order_end_date:
                        end_date = company.export_pos_order_end_date

                        # Same check for the end date
                        if end_date.month > 12 or (end_date.month == 4 and end_date.day == 9):
                            # Create a new datetime with month and day swapped
                            end_date = datetime(end_date.year, end_date.day, end_date.month,
                                                end_date.hour, end_date.minute, end_date.second)
                            print(f"End date adjusted for format confusion: {end_date}")
                    else:
                        # Use the original logic of adding 23:59:59 to the start date
                        start_day = datetime(
                            start_date.year, start_date.month, start_date.day)
                        end_date = start_day + timedelta(hours=23, minutes=59, seconds=59)

                    # Ensure start date is before end date
                    if start_date > end_date:
                        print(f"Warning: Start date {start_date} is after end date {end_date}, swapping them")
                        start_date, end_date = end_date, start_date

                    # Add filters with corrected dates
                    filters.append(('date_order', '>=', start_date))
                    filters.append(('date_order', '<=', end_date))

                    print(f"Using corrected date range: {start_date} to {end_date}")
                    _logger.info(f"Filtering POS orders by date range: {start_date} to {end_date}")

                except Exception as e:
                    error_msg = f"Error processing date filters: {str(e)}"
                    print(error_msg)
                    _logger.error(error_msg)
                    # Continue with basic filters if date processing fails

        elif export_context == 'session_close':
            current_date = datetime.now().strftime('%Y-%m-%d')
            # Filters for session closing export
            filters = [
                ('state', 'in', ['paid', 'done', 'invoiced']),
                ('date_order', '>=', f"{current_date} 00:00:00"),
                ('date_order', '<=', f"{current_date} 23:59:59"),
                ('quickbooks_id', '=', False)
            ]

        # Get export limits from company configuration
        limit = int(company.export_pos_limit) if hasattr(company,
                                                         'export_pos_limit') and company.export_pos_limit else 100

        # Get orders to export
        if order_id:
            orders = self.browse([order_id]) if isinstance(order_id, int) else order_id
        else:
            orders = self.search(filters, limit=limit)

        _logger.info(f"POS ORDERS===>>>>>>>>>>>>>>>> {orders}")

        # Return if no orders found
        if not orders:
            _logger.info("No POS orders found to export")
            return True

        # Separate invoiced from non-invoiced orders
        paid_orders = orders.filtered(lambda o: o.state in ['paid', 'done'])
        invoiced_orders = orders.filtered(lambda o: o.state == 'invoiced')

        # Process paid/done orders as receipts
        if paid_orders:
            # Group orders by date AND customer
            orders_by_date_customer = {}
            for order in paid_orders:
                # Extract date part only
                order_date = order.date_order.strftime('%Y-%m-%d')
                # Get customer ID (use 0 for no customer)
                customer_id = order.partner_id.id if order.partner_id else 0

                # Create composite key of date and customer
                date_customer_key = f"{order_date}_{customer_id}"

                if date_customer_key not in orders_by_date_customer:
                    orders_by_date_customer[date_customer_key] = {
                        'date': order_date,
                        'orders': []
                    }

                orders_by_date_customer[date_customer_key]['orders'].append(order)

            _logger.info(f"Grouped paid orders by date and customer: {len(orders_by_date_customer)} groups")

            # Process each date-customer group to create consolidated entries for receipts
            for key, group in orders_by_date_customer.items():
                order_dict = self.get_consolidated_pos_dict(group['date'], group['orders'], company)
                if order_dict:
                    paid_order_data_list.append(order_dict)

        # Process invoiced orders as invoices
        if invoiced_orders:
            # Group invoiced orders by date AND customer
            invoices_by_date_customer = {}
            for order in invoiced_orders:
                order_date = order.date_order.strftime('%Y-%m-%d')
                customer_id = order.partner_id.id if order.partner_id else 0
                date_customer_key = f"{order_date}_{customer_id}"

                if date_customer_key not in invoices_by_date_customer:
                    invoices_by_date_customer[date_customer_key] = {
                        'date': order_date,
                        'orders': []
                    }

                invoices_by_date_customer[date_customer_key]['orders'].append(order)

            _logger.info(f"Grouped invoiced orders by date and customer: {len(invoices_by_date_customer)} groups")

            # Process each date-customer group to create consolidated entries for invoices
            for key, group in invoices_by_date_customer.items():
                invoice_dict = self.get_consolidated_pos_invoice_dict(group['date'], group['orders'], company)
                if invoice_dict:
                    invoiced_order_data_list.append(invoice_dict)

        # Export paid orders as sales receipts
        if paid_order_data_list:
            _logger.info(f"Sending {len(paid_order_data_list)} consolidated POS orders to QuickBooks")

            headers = {'content-type': "application/json"}
            data = {'pos_orders_list': paid_order_data_list}

            endpoint = f"{qb_url}/pos_orders"
            _logger.info(f"Sending request to: {endpoint}")

            try:
                response = requests.request('POST', endpoint,
                                            data=json.dumps(data),
                                            headers=headers,
                                            verify=False)

                _logger.info(f"Response status: {response.status_code}")
                _logger.info(f"Response status: {response.text}")

                if response.status_code != 200:
                    raise UserError(_("Error communicating with QuickBooks: %s") % response.text)

                # Parse response
                try:
                    resp = ast.literal_eval(response.text)
                    _logger.info(f"Parsed response type: {type(resp)}")

                    if isinstance(resp, dict):
                        if resp.get("Message"):
                            raise UserError(_("Error from QuickBooks: %s") % resp.get("Message"))

                        for res in resp.get('Data', []):
                            if 'odoo_id' in res and res.get('quickbooks_id'):
                                # Check if odoo_id is a list or an integer
                                order_ids = res.get('odoo_id')

                                # Convert to list if it's an integer (single order case)
                                if isinstance(order_ids, int):
                                    order_ids = [order_ids]
                                # Handle string representation of integer
                                elif isinstance(order_ids, str) and order_ids.isdigit():
                                    order_ids = [int(order_ids)]

                                for order_id in order_ids:
                                    pos_id = self.browse(int(order_id))
                                    if pos_id:
                                        pos_id.write({
                                            'quickbooks_id': res.get('quickbooks_id'),
                                            'sale_no': res.get('qbd_receipt_no', '')
                                        })

                                        # Create log entry
                                        self.env['qbd.loger'].create({
                                            'operation': 'Export POS Order Receipt',
                                            'odoo_id': order_id,
                                            'qbd_id': res.get('quickbooks_id'),
                                            'message': f"Exported as part of consolidated receipt for {res.get('order_date', '')}",
                                        })

                                        # Create order invoice logger entry
                                        self.env['qbd.orderinvoice.logger'].create({
                                            'odoo_id': order_id,
                                        })

                        # Update company with last export date if provided
                        if 'last_modified_date' in res and res.get('last_modified_date'):
                            date_parsed = parse(res.get('last_modified_date'))
                            company.write({
                                'export_pos_order_date': date_parsed
                            })
                    else:
                        raise UserError(_("Invalid response format from QuickBooks"))

                except (ValueError, SyntaxError) as e:
                    error_msg = f"Failed to parse QuickBooks response: {str(e)}, Response: {response.text[:200]}"
                    _logger.error(error_msg)
                    raise UserError(_(error_msg))

            except requests.exceptions.RequestException as e:
                error_msg = f"Error connecting to QuickBooks: {str(e)}"
                _logger.error(error_msg)
                raise UserError(_(error_msg))

        # Export invoiced orders as invoices
        if invoiced_order_data_list:
            _logger.info(f"Sending {len(invoiced_order_data_list)} consolidated POS invoices to QuickBooks")

            headers = {'content-type': "application/json"}
            data = {'pos_invoices_list': invoiced_order_data_list}
            print('invoice data:        ', data)

            endpoint = f"{qb_url}/pos_invoices"
            _logger.info(f"Sending request to: {endpoint}")

            try:
                response = requests.request('POST', endpoint,
                                            data=json.dumps(data),
                                            headers=headers,
                                            verify=False)

                _logger.info(f"Response status: {response.status_code}")
                _logger.info(f"Response status: {response.text}")

                if response.status_code != 200:
                    raise UserError(_("Error communicating with QuickBooks: %s") % response.text)

                # Parse response
                try:
                    resp = ast.literal_eval(response.text)
                    _logger.info(f"Parsed response type: {type(resp)}")

                    if isinstance(resp, dict):
                        if resp.get("Message"):
                            raise UserError(_("Error from QuickBooks: %s") % resp.get("Message"))

                        for res in resp.get('Data', []):
                            if 'odoo_id' in res and res.get('quickbooks_id'):
                                # Check if odoo_id is a list or an integer
                                order_ids = res.get('odoo_id')

                                # Convert to list if it's an integer (single order case)
                                if isinstance(order_ids, int):
                                    order_ids = [order_ids]
                                # Handle string representation of integer
                                elif isinstance(order_ids, str) and order_ids.isdigit():
                                    order_ids = [int(order_ids)]

                                for order_id in order_ids:
                                    pos_id = self.browse(int(order_id))
                                    if pos_id:
                                        pos_id.write({
                                            'quickbooks_id': res.get('quickbooks_id'),
                                            'invoice_no': res.get('qbd_invoice_no', '')
                                        })

                                        # Create log entry
                                        self.env['qbd.loger'].create({
                                            'operation': 'Export POS Order Invoice',
                                            'odoo_id': order_id,
                                            'qbd_id': res.get('quickbooks_id'),
                                            'message': f"Exported as part of consolidated invoice for {res.get('order_date', '')}",
                                        })

                                        # Create order invoice logger entry
                                        self.env['qbd.orderinvoice.logger'].create({
                                            'odoo_id': order_id,
                                        })

                        # Update company with last export date if provided
                        if 'last_modified_date' in res and res.get('last_modified_date'):
                            date_parsed = parse(res.get('last_modified_date'))
                            company.write({
                                'export_pos_order_date': date_parsed
                            })
                    else:
                        raise UserError(_("Invalid response format from QuickBooks"))

                except (ValueError, SyntaxError) as e:
                    error_msg = f"Failed to parse QuickBooks response: {str(e)}, Response: {response.text[:200]}"
                    _logger.error(error_msg)
                    raise UserError(_(error_msg))

            except requests.exceptions.RequestException as e:
                error_msg = f"Error connecting to QuickBooks: {str(e)}"
                _logger.error(error_msg)
                raise UserError(_(error_msg))

        return True

    def get_consolidated_pos_dict(self, date, orders, company):
        """
        Create a consolidated dictionary for all POS orders on a single date for a specific customer

        :param date: Date string in YYYY-MM-DD format
        :param orders: List of POS order records for this date and customer
        :param company: Company record
        :return: Dictionary with consolidated order data
        """
        if not orders:
            return False

        # Calculate totals and get order data
        taxable_total = 0.0
        non_taxable_total = 0.0
        taxable_qty = 0
        non_taxable_qty = 0
        order_ids = []
        payment_methods = {}

        # All orders should be for the same customer
        customer = orders[0].partner_id

        # DEBUG: Log order processing start
        _logger.info(f"Processing orders for {customer.name if customer else 'No customer'}, "
                     f"QB ID={customer.quickbooks_id if customer and hasattr(customer, 'quickbooks_id') else 'None'}")
        _logger.info(f"Processing {len(orders)} orders: {[o.id for o in orders]}")

        # Get customer information
        customer_name = 'Cash Customer'
        customer_qb_id = ''

        # Check if there's no customer
        if not customer:
            # Try to find an existing 'Walk-in Customer' or create one
            walk_in_customer = self.env['res.partner'].search([('name', '=', 'Walk-in Customer')], limit=1)

            if not walk_in_customer:
                # Create a default walk-in customer
                walk_in_customer = self.env['res.partner'].create({
                    'name': 'Walk-in Customer',
                    'company_type': 'person',
                })

            # Set the customer to the walk-in customer
            customer = walk_in_customer
            customer_name = customer.name

            # Check if the walk-in customer has a QuickBooks ID
            if hasattr(customer, 'quickbooks_id') and not customer.quickbooks_id:
                # Export the walk-in customer to QuickBooks
                customer.export_partners(customer)
                if customer.quickbooks_id:
                    customer_qb_id = customer.quickbooks_id
            elif hasattr(customer, 'quickbooks_id'):
                customer_qb_id = customer.quickbooks_id
        else:
            customer_name = customer.name

            # Check if customer has QuickBooks ID - if not, export the customer first
            if hasattr(customer, 'quickbooks_id') and not customer.quickbooks_id:
                # Export partner if not available in QuickBooks
                customer.export_partners(customer)
                # After export, refresh the QB ID
                if customer.quickbooks_id:
                    customer_qb_id = customer.quickbooks_id
            elif hasattr(customer, 'quickbooks_id'):
                customer_qb_id = customer.quickbooks_id

        for order in orders:
            # Collect all order IDs
            order_ids.append(order.id)

            # Determine taxable amount based on tax lines
            for line in order.lines:
                has_tax = False
                if hasattr(line, 'tax_ids_after_fiscal_position') and line.tax_ids_after_fiscal_position:
                    has_tax = bool(line.tax_ids_after_fiscal_position)
                elif hasattr(line, 'tax_ids') and line.tax_ids:
                    has_tax = bool(line.tax_ids)
                elif hasattr(line, 'tax_id') and line.tax_id:
                    has_tax = bool(line.tax_id)

                if has_tax:
                    taxable_total += line.price_subtotal
                    taxable_qty += line.qty if hasattr(line, 'qty') else 1
                else:
                    non_taxable_total += line.price_subtotal
                    non_taxable_qty += line.qty if hasattr(line, 'qty') else 1

            # Summarize payment methods
            for payment in order.payment_ids:
                method_name = payment.payment_method_id.name
                method_qb_id = payment.payment_method_id.quickbooks_id if hasattr(payment.payment_method_id,
                                                                                  'quickbooks_id') else ''

                if method_name not in payment_methods:
                    payment_methods[method_name] = {
                        'amount': 0.0,
                        'qb_id': method_qb_id
                    }
                payment_methods[method_name]['amount'] += payment.amount

        # Create payment summary
        payments = []
        for method_name, data in payment_methods.items():
            payments.append({
                'payment_method': method_name,
                'payment_method_qb_id': data['qb_id'],
                'amount': data['amount'],
                'payment_date': date,
            })

        # Create the consolidated record with ALL order_ids included
        order_dict = {
            'pos_order_qbd_id': '',  # Always empty for new exports
            'default_tax_on_order': company.qb_default_tax.name,
            'odoo_id': order_ids,  # Include ALL order IDs
            'order_date': date,
            'qbd_memo': f"POS Summary {date} - {customer_name}",
            'partner_name': customer_qb_id,
            'customer_quickbooks_id': customer_qb_id,
            'customer_name': customer_name,
            'confirmation_date': date,
            'is_paid': True,
            'amount_total': taxable_total + non_taxable_total,
            'payments': payments,
        }

        # Collect taxes from order lines
        taxable_line_taxes = []
        for order in orders:
            for line in order.lines:
                if hasattr(line, 'tax_ids_after_fiscal_position') and line.tax_ids_after_fiscal_position:
                    taxable_line_taxes.extend(line.tax_ids_after_fiscal_position)

        # Get product lines
        order_dict.update({
            'order_lines': self.get_consolidated_pos_order_lines(taxable_total, non_taxable_total,
                                                                 taxable_qty, non_taxable_qty, company,
                                                                 taxable_line_taxes)
        })

        _logger.info(f"Consolidated POS order for {customer_name} on {date} with {len(order_ids)} orders: {order_ids}")
        return order_dict

    def get_consolidated_pos_invoice_dict(self, date, orders, company):
        """
        Create a consolidated dictionary for all invoiced POS orders on a single date for a specific customer

        :param date: Date string in YYYY-MM-DD format
        :param orders: List of invoiced POS order records for this date and customer
        :param company: Company record
        :return: Dictionary with consolidated invoice data
        """
        if not orders:
            return False

        # Calculate totals and get order data
        taxable_total = 0.0
        non_taxable_total = 0.0
        taxable_qty = 0
        non_taxable_qty = 0
        order_ids = []

        # All orders should be for the same customer
        customer = orders[0].partner_id

        # DEBUG: Log order processing start
        _logger.info(f"Processing invoiced orders for {customer.name if customer else 'No customer'}, "
                     f"QB ID={customer.quickbooks_id if customer and hasattr(customer, 'quickbooks_id') else 'None'}")
        _logger.info(f"Processing {len(orders)} invoiced orders: {[o.id for o in orders]}")

        # Get customer information
        customer_name = 'Cash Customer'
        customer_qb_id = ''

        # Check if there's no customer
        if not customer:
            # Try to find an existing 'Walk-in Customer' or create one
            walk_in_customer = self.env['res.partner'].search([('name', '=', 'Walk-in Customer')], limit=1)

            if not walk_in_customer:
                # Create a default walk-in customer
                walk_in_customer = self.env['res.partner'].create({
                    'name': 'Walk-in Customer',
                    'company_type': 'person',
                })

            # Set the customer to the walk-in customer
            customer = walk_in_customer
            customer_name = customer.name

            # Check if the walk-in customer has a QuickBooks ID
            if hasattr(customer, 'quickbooks_id') and not customer.quickbooks_id:
                # Export the walk-in customer to QuickBooks
                customer.export_partners(customer)
                if customer.quickbooks_id:
                    customer_qb_id = customer.quickbooks_id
            elif hasattr(customer, 'quickbooks_id'):
                customer_qb_id = customer.quickbooks_id
        else:
            customer_name = customer.name

            # Check if customer has QuickBooks ID - if not, export the customer first
            if hasattr(customer, 'quickbooks_id') and not customer.quickbooks_id:
                # Export partner if not available in QuickBooks
                customer.export_partners(customer)
                # After export, refresh the QB ID
                if customer.quickbooks_id:
                    customer_qb_id = customer.quickbooks_id
            elif hasattr(customer, 'quickbooks_id'):
                customer_qb_id = customer.quickbooks_id

        for order in orders:
            # Collect all order IDs
            order_ids.append(order.id)

            # Determine taxable amount based on tax lines
            for line in order.lines:
                has_tax = False
                if hasattr(line, 'tax_ids_after_fiscal_position') and line.tax_ids_after_fiscal_position:
                    has_tax = bool(line.tax_ids_after_fiscal_position)
                elif hasattr(line, 'tax_ids') and line.tax_ids:
                    has_tax = bool(line.tax_ids)
                elif hasattr(line, 'tax_id') and line.tax_id:
                    has_tax = bool(line.tax_id)

                if has_tax:
                    taxable_total += line.price_subtotal
                    taxable_qty += line.qty if hasattr(line, 'qty') else 1
                else:
                    non_taxable_total += line.price_subtotal
                    non_taxable_qty += line.qty if hasattr(line, 'qty') else 1

        # Get invoice number if available (from the first order with an invoice)
        invoice_number = ""
        invoice_date = date
        for order in orders:
            if hasattr(order, 'account_move') and order.account_move:
                invoice_number = order.account_move.name
                invoice_date = order.account_move.invoice_date.strftime(
                    '%Y-%m-%d') if order.account_move.invoice_date else date
                break

        # Create the consolidated invoice record with ALL order_ids included
        invoice_dict = {
            'pos_invoice_qbd_id': '',  # Always empty for new exports
            'default_tax_on_order': company.qb_default_tax.name,
            'odoo_id': order_ids,  # Include ALL order IDs
            'order_date': invoice_date,
            'invoice_number': invoice_number,
            'qbd_memo': f"POS Invoice {date} - {customer_name}",
            'partner_name': customer_qb_id,
            'customer_quickbooks_id': customer_qb_id,
            'customer_name': customer_name,
            'confirmation_date': date,
            'is_paid': False,  # Invoices are not considered paid yet
            'amount_total': taxable_total + non_taxable_total
        }

        # Collect taxes from order lines
        taxable_line_taxes = []
        for order in orders:
            for line in order.lines:
                if hasattr(line, 'tax_ids_after_fiscal_position') and line.tax_ids_after_fiscal_position:
                    taxable_line_taxes.extend(line.tax_ids_after_fiscal_position)

        # Get product lines (reusing the same consolidated approach as receipts)
        invoice_dict.update({
            'order_lines': self.get_consolidated_pos_order_lines(taxable_total, non_taxable_total,
                                                                 taxable_qty, non_taxable_qty, company,
                                                                 taxable_line_taxes)
        })

        _logger.info(
            f"Consolidated POS invoice for {customer_name} on {date} with {len(order_ids)} orders: {order_ids}")
        return invoice_dict

    def get_consolidated_pos_order_lines(self, taxable_total, non_taxable_total,
                                         taxable_qty, non_taxable_qty, company, taxable_line_taxes=None):
        """
        Get consolidated product lines for POS orders
        Creates two line items: taxable and non-taxable

        :param taxable_total: Total amount for taxable sales
        :param non_taxable_total: Total amount for non-taxable sales
        :param taxable_qty: Total quantity for taxable items
        :param non_taxable_qty: Total quantity for non-taxable items
        :param company: Company record
        :param taxable_line_taxes: Taxes from taxable lines
        :return: List of line dictionaries
        """
        # Get the tax codes
        tax_code = self.env['qbd.tax.code'].search([('name', '=', 'TAX')], limit=1)
        non_tax_code = self.env['qbd.tax.code'].search([('name', '=', 'NON')], limit=1)

        # Set default tax code names to use if not found
        tax_code_name = tax_code.name if tax_code else 'TAX'
        non_tax_code_name = non_tax_code.name if non_tax_code else 'NON'

        # Get the special products
        taxable_product = self.env['product.product'].search([('default_code', '=', 'TAXABLE-SALES')], limit=1)
        non_taxable_product = self.env['product.product'].search([('default_code', '=', 'NON-TAXABLE-SALES')], limit=1)

        if not taxable_product or not non_taxable_product:
            raise UserError(
                _('Products "POS Taxable Sales" and "POS Non-Taxable Sales" must be configured for POS export'))

        # Check and export products if they don't have quickbooks_id
        if taxable_product and not taxable_product.quickbooks_id:
            # Export product first
            taxable_product.export_products([taxable_product])

        if non_taxable_product and not non_taxable_product.quickbooks_id:
            # Export product first
            non_taxable_product.export_products([non_taxable_product])

        # Create line items array
        order_lines = []

        # Determine tax ID from POS product line taxes
        tax_id = ''
        if taxable_line_taxes:
            # Use the first tax's QuickBooks ID if available
            first_tax = taxable_line_taxes[0]
            tax_id = first_tax.quickbooks_id if hasattr(first_tax, 'quickbooks_id') else ''

        # Add taxable line if exists
        if taxable_total > 0:
            taxable_line = {
                'product_name': taxable_product.quickbooks_id,
                'name': 'POS Taxable Sales',
                'quantity': taxable_qty,
                'price_unit': taxable_total / taxable_qty if taxable_qty > 0 else 0,
                'price_subtotal': taxable_total,
                'tax_code': tax_code_name,
                'tax_id': tax_id,
            }
            order_lines.append(taxable_line)

        # Add non-taxable line if exists
        if non_taxable_total > 0:
            non_taxable_line = {
                'product_name': non_taxable_product.quickbooks_id,
                'name': 'POS Non-Taxable Sales',
                'quantity': non_taxable_qty,
                'price_unit': non_taxable_total / non_taxable_qty if non_taxable_qty > 0 else 0,
                'price_subtotal': non_taxable_total,
                'tax_code': non_tax_code_name,
                'tax_id': '',
            }
            order_lines.append(non_taxable_line)

        return order_lines


class PosPaymentMethods(models.Model):
    _inherit = "pos.payment.method"

    name = fields.Char('Name')
    quickbooks_id = fields.Char("Quickbook id ", copy=False)

    def create_qbd_payment_methods(self, payment_methods_data):
        PosPaymentMethod = self.env['pos.payment.method']

        if payment_methods_data:
            for payment_method in payment_methods_data:
                vals = {}

                if isinstance(payment_method, str):
                    continue

                if 'payment_type' in payment_method and payment_method.get('payment_type'):
                    # Case insensitive search using ILIKE
                    pos_payment_method = PosPaymentMethod.search([
                        ('name', 'ilike', payment_method.get('payment_type'))
                    ], limit=1)

                    if not pos_payment_method:
                        # Create new payment method in pos.payment.method
                        vals.update({
                            'name': payment_method.get('payment_type'),
                            'quickbooks_id': payment_method.get('quickbooks_id')
                        })

                        if vals:
                            PosPaymentMethod.create(vals)
                    else:
                        # Update existing payment method
                        vals.update({
                            'quickbooks_id': payment_method.get('quickbooks_id')
                        })
                        pos_payment_method.write(vals)

        return True


class PointOfSaleLine(models.Model):
    _inherit = "pos.order.line"

    qbd_tax_code = fields.Many2one('qbd.tax.code')

    @api.model
    def create(self, vals):
        line = super().create(vals)
        if line.tax_ids_after_fiscal_position:
            line.with_context(bypass_qbd=True).write({
                'qbd_tax_code': line.tax_ids_after_fiscal_position[0].qbd_tax_code
            })
        return line

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('bypass_qbd'):
            for line in self:
                if line.tax_ids_after_fiscal_position:
                    line.with_context(bypass_qbd=True).write({
                        'qbd_tax_code': line.tax_ids_after_fiscal_position[0].qbd_tax_code
                    })
        return res
