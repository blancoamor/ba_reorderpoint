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

	@api.multi
	def process_lines(self):
		if self.monto_lineas > self.monto_presupuesto:
			raise ValidationError('El monto de las lineas supera el monto presupuestado')
		self.state = 'process'
		for linea in self.presupuesto_lines:
			vals = {
				'name': 'PEDIDO ' + self.name,
				'origin': 'PEDIDO ' + self.name,
				'date_planned': self.date_planned,
				'product_id': linea.product_id.id,
				'product_qty': linea.cantidad,
				'product_uom': 1,
				'warehouse_id': self.warehouse_id.id,
				'location_id': self.warehouse_id.lot_stock_id.id,
				'company_id': self.warehouse_id.company_id.id,
				}
			procure_id = self.env['procurement.order'].create(vals)
            		procure_id.signal_workflow('button_confirm')
			linea.procurement_id = procure_id.id
	


	@api.one
	def _compute_monto_lineas(self):
		return_value = 0
		for linea in self.presupuesto_lines:
			return_value = return_value + linea.monto
		self.monto_lineas = return_value

	@api.one
	def _compute_ok_process(self):
		if self.monto_presupuesto >= self.monto_lineas:
			self.ok_process = True
		else:
			self.ok_process = False

	name = fields.Char('Nombre',required=True)	
	date_planned = fields.Date('Fecha Abastecimiento',required=True)
	warehouse_id = fields.Many2one('stock.warehouse',string='Sucursal',required=True)
	monto_presupuesto = fields.Float('Presupuesto')
	state = fields.Selection(selection=[('draft','Borrador'),('process','En Proceso')],string='Status',default='draft')
	presupuesto_lines = fields.One2many(comodel_name='stock.presupuesto.line',inverse_name='presupuesto_id')
	monto_lineas = fields.Float('Monto pedido',compute=_compute_monto_lineas)
	ok_process = fields.Boolean('OK Proceso',compute=_compute_ok_process)

class stock_presupuesto_line(models.Model):
	_name = 'stock.presupuesto.line'
	_description = 'Lineas de presupuesto para reposicion de stock'


	@api.one
	def _compute_monto(self):
		if self.product_id.standard_price:
			self.monto = self.cantidad * self.product_id.standard_price

	@api.one
	def _compute_procurement_state(self):
		return_value = 'N/A'
		if self.procurement_id:
			return_value = self.procurement_id.state
		self.procurement_state = return_value

	presupuesto_id = fields.Many2one('stock.presupuesto')
	product_id = fields.Many2one('product.product',string='Producto',required=True)
	cantidad = fields.Integer(string='Cantidad a pedir',required=True)
	monto = fields.Float(string='Costo Calculado',compute=_compute_monto)
	procurement_id = fields.Many2one('procurement.order')
	procurement_state = fields.Char(string='Estado Pedido',related='procurement_id.state')
