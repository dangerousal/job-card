# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class JobInvoiceLine(models.Model):
    _name = "job.invoice.line"

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'task_id.partner_id', 'task_id.custom_currency_id')
    def _compute_price(self):
        currency = self.task_id and self.task_id.custom_currency_id or None
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.task_id.partner_id)
        if taxes:
            for taxe in taxes['taxes']:
                self.tax_amount += taxe['amount']
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        self.price_total = taxes['total_included'] if taxes else self.price_subtotal
        if self.task_id.custom_currency_id and self.task_id.custom_currency_id != self.task_id.company_id.currency_id:
            price_subtotal_signed = self.task_id.custom_currency_id.with_context(date=self.task_id.create_date).compute(price_subtotal_signed, self.task_id.company_id.currency_id)
            
    @api.one
    @api.depends('invoice_id')
    def _compute_invoice(self):
        for rec in self:
            if not rec.invoice_id or rec.invoice_id.state == 'cancel':
                rec.is_invoice = False
            else:
                rec.is_invoice = True
    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.name = self.product_id.name
        self.price_unit = self.product_id.lst_price
        self.uom_id = self.product_id.uom_id.id
        
        company = self.task_id.company_id
        product = self.product_id
        invoice_line_obj = self.env['account.invoice.line']
        account = invoice_line_obj.get_invoice_line_account(type='out_invoice', product=product, fpos=None, company=company)
        if account:
           self.account_id = account.id

    is_invoice = fields.Boolean(
        string="Is Invoice",
        compute='_compute_invoice',
        store=True,
        
    )
    name = fields.Text(string='Description', required=True)
    product_id = fields.Many2one(
        'product.product',
        string="Product"
    )
    account_id = fields.Many2one(
        'account.account',
        string="Account",
        required=True,
    )
    account_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account'
    )
    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag',
        string='Analytic Tags'
    )
    quantity = fields.Float(
        string='Quantity',
        digits=dp.get_precision('Product Unit of Measure'),
        required=True,
        default=1
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        ondelete='set null',
        index=True,
    )
    price_unit = fields.Float(
        string='Unit Price',
        required=True,
        digits=dp.get_precision('Product Price')
    )
    discount = fields.Float(
        string='Discount (%)',
        digits=dp.get_precision('Discount'),
        default=0.0
    )
    invoice_line_tax_ids = fields.Many2many(
        'account.tax',
        'job_invoice_line_tax',
        'invoice_line_id',
        'tax_id',
        string='Taxes',
    )
    task_id = fields.Many2one(
        'project.task',
        string="Task"
    )
    tax_amount = fields.Float(
        string='Tax Amount',
        store=True,
        readonly=True,
        compute='_compute_price',
        help="Total tax amount"
    )
    price_subtotal = fields.Float(
        string='Amount',
        store=True,
        readonly=True,
        compute='_compute_price',
        help="Total amount without taxes"
    )
    invoice_id = fields.Many2one(
        'account.invoice',
        string='Invoice',
    )

