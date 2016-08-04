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

	@api.one
	def _compute_monto_lineas(self):
		return_value = 0
		for linea in self.presupuesto_lines:
			return_value = return_value + linea.monto
		self.monto_lineas = return_value

	name = fields.Char('Nombre')	
	warehouse_id = fields.Many2one('stock.warehouse',string='Sucursal')
	monto_presupuesto = fields.Float('Presupuesto')
	state = fields.Selection(selection=[('draft','Borrador'),('process','En Proceso')],string='Status',default='draft')
	presupuesto_lines = fields.One2many(comodel_name='stock.presupuesto.line',inverse_name='presupuesto_id')
	monto_lineas = fields.Float('Monto pedido',compute=_compute_monto_lineas)

class stock_presupuesto_line(models.Model):
	_name = 'stock.presupuesto.line'
	_description = 'Lineas de presupuesto para reposicion de stock'

	@api.onchange('cantidad')
	def _compute_monto(self):
		if self.product_id.standard_price:
			self.monto = self.cantidad * self.product_id.standard_price

	presupuesto_id = fields.Many2one('stock.presupuesto')
	product_id = fields.Many2one('product.product',string='Producto')
	cantidad = fields.Integer(string='Cantidad a pedir')
	monto = fields.Float(string='Costo Calculado')
