# -*- coding: utf-8 -*-

from odoo import fields, models


class QualityChecklist(models.Model):
    _name = "quality.checklist"

    name = fields.Char(
        string = "Name",
        required=True,
        copy=False
    )
    description = fields.Text(
        string = "Description"
    )

