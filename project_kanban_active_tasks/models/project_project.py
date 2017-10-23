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

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'
    
    display_in_kanban = fields.Boolean("Display in Kanaban View", default=False)

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    is_active_project = fields.Boolean('Active Project',compute = lambda self : len(self.active_task_ids)>0,
        search = lambda self, operator, value : [('task_ids.stage_id.display_in_kanban', '=', value)] )
    
    active_task_ids = fields.One2many('project.task', 'project_id', string='Active Tasks',
        domain=[('stage_id.display_in_kanban', '=', True)])
        