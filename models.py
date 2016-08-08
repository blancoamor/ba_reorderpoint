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
		if not self.presupuesto_lines:
			raise ValidationError('No hay lineas para procesar')
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

	@api.constrains('business_unit','warehouse_id')
	def _check_business_unit(self):
		presupuestos = self.env['stock.presupuesto'].search([('warehouse_id','=',self.warehouse_id.id),\
				('business_unit','=',self.business_unit.id),('state','=','draft')])
		if len(presupuestos) > 1:
			raise ValidationError('Ya existe un pedido creado para la business unit ' + self.business_unit.name + \
				' sucursal ' + self.warehouse_id.name)

	@api.one
	def _compute_presupuesto_previo(self):
		return_value = None
		if self.state == 'process':
			limite = 2
		else:
			limite = 1
		presupuesto_id = self.env['stock.presupuesto'].search([('business_unit','=',self.business_unit.id),\
					('warehouse_id','=',self.warehouse_id.id),\
					('state','=','process')],order='date_planned desc',limit=limite)
		if presupuesto_id:
			if limite == 1:
				self.presupuesto_previo = presupuesto_id.id
			else:
				for presupuesto in presupuesto_id:
					if presuesto.id != self.id:
						self.presupuesto_previo = presupuesto.id
		else:
			self.presupuesto_previo = None

	name = fields.Char('Nombre',required=True)	
	date_planned = fields.Date('Fecha Abastecimiento',required=True)
	warehouse_id = fields.Many2one('stock.warehouse',string='Sucursal',required=True)
	monto_presupuesto = fields.Float('Presupuesto')
	state = fields.Selection(selection=[('draft','Borrador'),('process','En Proceso')],string='Status',default='draft')
	presupuesto_lines = fields.One2many(comodel_name='stock.presupuesto.line',inverse_name='presupuesto_id')
	monto_lineas = fields.Float('Monto pedido',compute=_compute_monto_lineas)
	ok_process = fields.Boolean('OK Proceso',compute=_compute_ok_process)
	presupuesto_previo = fields.Many2one('stock.presupuesto',string='Presupuesto anterior',compute=_compute_presupuesto_previo)
	business_unit = fields.Many2one('business.unit',required=True)

class stock_presupuesto_line(models.Model):
	_name = 'stock.presupuesto.line'
	_description = 'Lineas de presupuesto para reposicion de stock'


	@api.constrains('product_id')
	def _check_product_id_unique(self):
		if self.product_id:
			products = self.search([('product_id','=',self.product_id.id),('presupuesto_id','=',self.presupuesto_id.id)])
			if len(products) > 1:
				raise ValidationError('Producto ' + self.product_id.name + '\nya ingresado para el presente presupuesto')

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

	#@api.one
	@api.onchange('product_id')
	def _onchange_product_id(self):
		return_value = 0
		if self.product_id:
			if self.product_id.product_tmpl_id.business_unit_id.id != self.presupuesto_id.business_unit.id:
				raise ValidationError('Producto no pertenece a la business unit del pedido')
			order_ids = self.env['sale.order'].search([('warehouse_id','=',self.presupuesto_id.warehouse_id.id),\
					('state','in',['progress','manual','shipping_except','invoice_except','done'])])
			for order in order_ids:
				line_ids = self.env['sale.order.line'].search([('order_id','=',order.id),\
						('product_id','=',self.product_id.id)])
				if line_ids:
					for line in line_ids:
						return_value = return_value + line.product_uom_qty
		self.cantidad_sugerida = return_value

	@api.onchange('cantidad')
	def _onchange_cantidad(self):
		if self.cantidad and self.product_id:
			self.monto = self.cantidad * self.product_id.standard_price

	presupuesto_id = fields.Many2one('stock.presupuesto')
	product_id = fields.Many2one('product.product',string='Producto',required=True)
	cantidad = fields.Integer(string='Cantidad a pedir',required=True)
	cantidad_sugerida = fields.Integer(string='Cantidad sugerida',readonly=True)
	monto = fields.Float(string='Costo Calculado',compute=_compute_monto)
	# monto = fields.Float(string='Costo Calculado')
	procurement_id = fields.Many2one('procurement.order')
	procurement_state = fields.Char(string='Estado Pedido',compute=_compute_procurement_state)
