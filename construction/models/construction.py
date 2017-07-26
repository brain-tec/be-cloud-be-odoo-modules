# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 be-cloud.be
#                       Jerome Sonnet <jerome.sonnet@be-cloud.be>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging

from openerp import api, fields, models, _
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

class BuildingSite(models.Model):
    '''Building Site'''
    _name = 'construction.building_site'
    _description = 'Building Site'
    
    _inherits = {'project.project': "project_id"}
    
    construction_state = fields.Selection([
            ('development', 'In development'),
            ('onsale', 'On Sale'),
            ('construction', 'In Construction'),
            ('waranty', 'Waranty'),
            ('long_waranty', 'Long Wanranty'),
            ('archived', 'Archived'),
        ], string='State', required=True, help="")
    
    @api.onchange('construction_state')
    def update_project_state(self):
        if self.construction_state == 'construction':
            self.state = 'open'
        if self.construction_state == 'waranty':
            self.state = 'close'
    
    project_id = fields.Many2one('project.project', 'Project',
            help="Link this site to a project",
            ondelete="cascade", required=True, auto_join=True)
    
    @api.onchange('project_id')
    def update_project(self):
        self.building_site_id = self.id
        
    type = fields.Selection([
            ('single', 'Single'),
            ('double', 'Double'),
            ('residency', 'Residency'),
        ], string='Type of building', required=True, help="")
    
    address_id = fields.Many2one('res.partner', string='Site adress', domain="[('type', '=', 'delivery')]")
    notes = fields.Text(string='Notes')
    
    acquisition_lead = fields.Many2one('crm.lead', string='Acquisition Lead')
    asset_ids = fields.One2many('construction.building_asset', 'site_id', string="Building Assets")
    asset_count = fields.Integer(compute='_compute_asset_count')
    
    def _compute_asset_count(self):
        for site in self:
            site.asset_counts = len(site.asset_ids)
    
class Project(models.Model):
    _inherit = "project.project"
    
    building_site_id = fields.Many2one('construction.building_site', string='Building Site', ondelete='cascade')
    
class BuildingAsset(models.Model):
    '''Building Asset'''
    _name = 'construction.building_asset'
    _description = 'Building Asset'
    
    title = fields.Char(string="Title")
    
    name = fields.Char(string="Name", compute='_compute_name', store=True)
    
    @api.one
    @api.depends('title','partner_id.name')
    def _compute_name(self):
        if self.partner_id :
            self.name = "%s - %s" % (self.title, self.partner_id.name)
        else:
            self.name = self.title
    
    state = fields.Selection([
            ('development', 'In development'),
            ('onsale', 'On sale'),
            ('proposal', 'Proposal'),
            ('sold', 'Sold'),
        ], string='State', required=True, help="",default="development")
    
    type = fields.Selection([
            ('appartment', 'Appartment'),
            ('duplex', 'Duplex'),
            ('house', 'House'),
            ('contiguous', 'Contiguous House'),
            ('parking', 'Parking'),
        ], string='Type of asset', required=True, help="")
    
    site_id = fields.Many2one('construction.building_site', string='Building Site')
    
    partner_id = fields.Many2one('res.partner', string='Customer', ondelete='restrict', help="Customer for this asset.")
    
    confirmed_lead_id = fields.Many2one('crm.lead', string='Confirmed Lead')
    candidate_lead_ids = fields.One2many('crm.lead', 'building_asset_id', string='Candidate Leads', domain=['|',('active','=',True),('active','=',False)])
    
    @api.onchange('confirmed_lead_id')
    def update_confirmed_lead_id(self):
        self.partner_id = self.confirmed_lead_id.partner_id
        self.state = 'sold'
    
    sale_order_ids = fields.One2many('sale.order', 'building_asset_id', string="Sale Orders", readonly=True)
    invoice_ids = fields.One2many('account.invoice','building_asset_id', string="Invoices", readonly=True) 
    
class SaleOrder(models.Model):
    '''Sale Order'''
    _inherit = "sale.order"
    
    building_site_id = fields.Many2one('construction.building_site', string='Building Site', related="building_asset_id.site_id",store=True)
    building_asset_id = fields.Many2one('construction.building_asset', string='Building Asset', ondelete='restrict')
    
    @api.onchange('state')
    def update_asset_state(self):
        if self.state == 'sent':
            self.building_asset_id.state = 'proposal'
            # TODO add to the candidate lead_ids
        if self.state == 'sale':
            self.building_asset_id.state = 'sold'
            self.confirmed_lead_id.id = self.opportunity_id.id
            
    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['building_asset_id'] = self.building_asset_id.id or False
        return invoice_vals
            
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.order_id.building_site_id :
            res.update({'account_analytic_id': self.order_id.building_site_id.analytic_account_id.id})
        return res
            
class CrmLean(models.Model):
    '''CRM Lead'''
    _inherit = "crm.lead"
    
    building_site_id = fields.Many2one('construction.building_site', string='Building Site', related="building_asset_id.site_id",store=True)
    building_asset_id = fields.Many2one('construction.building_asset', string='Building Asset', ondelete='restrict')
    
    @api.multi
    def _convert_opportunity_data(self, customer, team_id=False):
        res = super(CrmLean, self)._convert_opportunity_data(self, customer, team_id)
        res['building_asset_id'] = self.building_asset_id.id or False
    
class Invoice(models.Model):
    '''Invoice'''
    _inherit = 'account.invoice'
    
    building_site_id = fields.Many2one('construction.building_site', string='Building Site', related="building_asset_id.site_id",store=True)
    building_asset_id = fields.Many2one('construction.building_asset', string='Building Asset', ondelete='restrict')
    
class Partner(models.Model):
    '''Partner'''
    _inherit = 'res.partner'
    
    matricule = fields.Char(string="Matricule")