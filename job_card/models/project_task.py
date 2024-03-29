# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning


class Task(models.Model):
    _inherit = "project.task"
    _rec_name = 'number'

    @api.one
    @api.depends('job_invoice_line_ids.price_subtotal', 'custom_currency_id', 'company_id')
    def _compute_amount(self):
        round_curr = self.custom_currency_id.round
        self.invoice_amount_untaxed = sum(line.price_subtotal for line in self.job_invoice_line_ids)
        self.invoice_amount_tax = sum(round_curr(line.tax_amount) for line in self.job_invoice_line_ids)
        self.invoice_amount_total = self.invoice_amount_untaxed + self.invoice_amount_tax

    @api.one
    @api.depends('job_cost_sheet_ids.price_subtotal', 'custom_currency_id', 'company_id')
    def _compute_cost_sheet_amount(self):
        round_curr = self.custom_currency_id.round
        self.cost_sheet_amount_untaxed = sum(line.price_subtotal for line in self.job_cost_sheet_ids)
        self.cost_sheet_amount_tax = sum(round_curr(line.tax_amount) for line in self.job_cost_sheet_ids)
        self.cost_sheet_amount_total = self.cost_sheet_amount_untaxed + self.cost_sheet_amount_tax
        
    
    @api.multi
    def print_job_card(self):
        return self.env.ref('job_card.action_report_jobcard').report_action(self)
    
    number = fields.Char(
        string = "Number",
        readonly=True,
        copy=False
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string="Analytic Account"
    )
    datas = fields.Binary(
        string='Technical Spec',
        copy=False
    )
    quality_checklist_id = fields.Many2many(
        'quality.checklist',
        string = "Quality Checklist",
    )
    instruction_job_order_ids = fields.One2many(
        'instruction.job.order',
        'task_id',
        string="Instruction/Job Order"
    )
    job_invoice_line_ids = fields.One2many(
        'job.invoice.line',
        'task_id',
        string="Job Invoice Line"
    )
    job_cost_sheet_ids = fields.One2many(
        'job.cost.sheet',
        'task_id',
        string="Job Cost Sheet"
    )
    job_card_daily_report_ids = fields.One2many(
        'account.analytic.line',
        'task_id',
        string="Daily Report",
    )
#     select_date = fields.Date(
#         string="Select Date",
#         #required=True,
#     )
    custom_currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.user.company_id.currency_id
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Account Journal',
    )
    invoice_amount_untaxed = fields.Float(
        string='Untaxed Amount',
        store=True,
        readonly=True,
        compute='_compute_amount',
    )
    invoice_amount_tax = fields.Float(
        string='Taxed Amount',
        store=True,
        readonly=True,
        compute='_compute_amount',
    )
    invoice_amount_total = fields.Float(
        string='Total',
        store=True,
        readonly=True,
        compute='_compute_amount',
    )
    cost_sheet_amount_untaxed = fields.Float(
        string='Untaxed Amount',
        store=True,
        readonly=True,
        compute='_compute_cost_sheet_amount',
    )
    cost_sheet_amount_tax = fields.Float(
        string='Taxed Amount',
        store=True,
        readonly=True,
        compute='_compute_cost_sheet_amount',
    )
    cost_sheet_amount_total = fields.Float(
        string='Total',
        store=True,
        readonly=True,
        compute='_compute_cost_sheet_amount',
    )
    material_requisition_ids = fields.One2many(
        'material.purchase.requisition',
        'task_id',
        string='Material Purchase Requisition',
        readonly=True,
    )
    material_requisition_line_ids = fields.One2many(
        'material.purchase.requisition.line',
        'task_id',
        string='Material Purchase Requisition Line',
        readonly=True,
    )
    workshop_staff_id = fields.Many2one(
        'workshop.position',
        string='Workshop Staff',
        copy=True,
    )
    is_close = fields.Boolean(
        string="Is Close",
        copy=False,
        readonly= True
    )
    is_jobcard = fields.Boolean(
        string='Is Job Card',
        default=False,
        readonly= True,
        copy=True,
    )

    @api.multi
    def action_mrak_done(self):
        for rec in self:
            rec.is_close = True

    @api.multi
    def action_re_open(self):
        for rec in self:
            rec.is_close = False

    @api.model
    def create(self, vals):
        result = super(Task, self).create(vals)
        for record in result:
            record.number = self.env['ir.sequence'].next_by_code('project.task')+': '+vals.get('name', False)#+' - '+partner_name
        return result
    
    @api.multi
    def unlink(self):
        for rec in self:
            if rec:
                raise Warning('You can not delete Job  Card.')

    @api.multi
    def create_invoice1(self):
        print("------------------------call-------------------")
        for rec in self:
            if any(not i.is_invoice for i in rec.job_invoice_line_ids):
                account_invoice_obj = self.env['account.invoice']
                p = rec.partner_id
                rec_account = p.property_account_receivable_id
                invoice_line_obj = self.env['account.invoice.line']
                invoice_vale = {
                    'partner_id': rec.partner_id.id,
                    'currency_id': self.env.user.company_id.currency_id.id,
                    'journal_id': rec.journal_id.id,
                    'account_id': rec_account.id,
                    'task_id': rec.id,
                    'type': 'out_invoice',
                }
                invoice_id = account_invoice_obj.create(invoice_vale)
                print("---------------invoice---------------",invoice_id)
                if invoice_id and rec.job_invoice_line_ids:
                    for line in rec.job_invoice_line_ids:
                        if not line.is_invoice:
                            invoice_line_vale = {
                                'product_id': line.product_id.id,
                                'name': line.name,
                                'account_id': line.account_id.id,
                                'account_analytic_id': line.account_analytic_id.id,
                                'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                                'quantity': line.quantity,
                                'uom_id': line.uom_id.id,
                                'invoice_line_tax_ids': [(6, 0, line.invoice_line_tax_ids.ids)],
                                'price_unit': line.price_unit,
                                'invoice_id': invoice_id.id,
                            }
                            invoice_line_id = invoice_line_obj.create(invoice_line_vale)
                            #if invoice_line_id:
                                #line.is_invoice = True
                            line.invoice_id = invoice_id.id
                res = self.env.ref('account.action_invoice_tree1')
                res = res.read()[0]
                res['domain'] = str([('id','=', invoice_id.id)])
                return res

    @api.onchange('project_id')
    def _onchange_project(self):
        for rec in self:
            rec.analytic_account_id = rec.project_id.analytic_account_id.id
            
    @api.multi
    def show_invoice(self):
        self.ensure_one()
        res = self.env.ref('account.action_invoice_tree1')
        res = res.read()[0]
        res['domain'] = str([('task_id', '=', self.id)])
        return res

    @api.multi
    def show_requisition(self):
        self.ensure_one()
        res = self.env.ref('material_purchase_requisitions.action_material_purchase_requisition')
        res = res.read()[0]
        res['domain'] = str([('id', 'in', self.material_requisition_ids.ids)])
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
