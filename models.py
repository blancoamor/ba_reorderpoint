from openerp import models, fields, api, _
from openerp.osv import osv
from openerp.exceptions import except_orm, ValidationError
from StringIO import StringIO
import urllib2, httplib, urlparse, gzip, requests, json
import openerp.addons.decimal_precision as dp
import logging
import datetime
from openerp.fields import Date as newdate
from datetime import datetime

#Get the logger
_logger = logging.getLogger(__name__)


class stock_presupuesto(models.Model):
	_name = 'stock.presupuesto'
	_description = 'Presupuesto periodico para reposicion de stock'
	
	warehouse_id = fields.Many2one('stock.warehouse',string='Sucursal')
	monto_presupuesto = fields.Float('Presupuesto')
	state = fields.Selection(selection=[('Borrador','En Proceso')],string='Status')
	presupuesto_lines = fields.One2many(comodel_name='stock.presupuesto.line',inverse_name='presupuesto_id')

class stock_presupuesto_line(models.Model):
	_name = 'stock.presupuesto.line'
	_description = 'Lineas de presupuesto para reposicion de stock'

	presupuesto_id = fields.Many2one('stock.presupuesto')
	
