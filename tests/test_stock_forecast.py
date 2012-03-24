#!/usr/bin/env python
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

import sys, os
DIR = os.path.abspath(os.path.normpath(os.path.join(__file__,
            '..', '..', '..', '..', '..', 'trytond')))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))

import unittest
from decimal import Decimal
import datetime
from dateutil.relativedelta import relativedelta
import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT, test_view,\
    test_depends
from trytond.transaction import Transaction


class StockForecastTestCase(unittest.TestCase):
    '''
    Test StockForecast module.
    '''

    def setUp(self):
        trytond.tests.test_tryton.install_module('stock_forecast')
        self.category = POOL.get('product.category')
        self.uom = POOL.get('product.uom')
        self.product = POOL.get('product.product')
        self.location = POOL.get('stock.location')
        self.company = POOL.get('company.company')
        self.user = POOL.get('res.user')
        self.forecast = POOL.get('stock.forecast')
        self.line = POOL.get('stock.forecast.line')
        self.move = POOL.get('stock.move')

    def test0005views(self):
        '''
        Test views.
        '''
        test_view('stock_forecast')

    def test0006depends(self):
        '''
        Test depends.
        '''
        test_depends()

    def test0020distribute(self):
        '''
        Test distribute.
        '''
        for values, result in (
                ((1, 5), {0: 5}),
                ((4, 8), {0: 2, 1: 2, 2: 2, 3: 2}),
                ((2, 5), {0: 2, 1: 3}),
                ((10, 4), {0: 0, 1: 1, 2: 0, 3: 1, 4: 0,
                        5: 0, 6: 1, 7: 0, 8: 1, 9: 0}),
                ):
            self.assertEqual(self.line.distribute(*values), result)

    def test0030create_moves(self):
        '''
        Test create_moves.
        '''
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            category_id = self.category.create({
                    'name': 'Test create_moves',
                    })
            unit_id, = self.uom.search([('name', '=', 'Unit')])
            product_id = self.product.create({
                    'name': 'Test create_moves',
                    'type': 'goods',
                    'category': category_id,
                    'cost_price_method': 'fixed',
                    'default_uom': unit_id,
                    'list_price': Decimal('1'),
                    'cost_price': Decimal(0),
                    })
            customer_id, = self.location.search([('code', '=', 'CUS')])
            warehouse_id, = self.location.search([('code', '=', 'WH')])
            storage_id, = self.location.search([('code', '=', 'STO')])
            company_id, = self.company.search([('name', '=', 'B2CK')])
            self.user.write(USER, {
                    'main_company': company_id,
                    'company': company_id,
                    })

            today = datetime.date.today()

            forecast_id = self.forecast.create({
                    'warehouse': warehouse_id,
                    'destination': customer_id,
                    'from_date': today + relativedelta(months=1, day=1),
                    'to_date': today + relativedelta(months=1, day=20),
                    'company': company_id,
                    'lines': [
                        ('create', {
                                'product': product_id,
                                'quantity': 10,
                                'uom': unit_id,
                                'minimal_quantity': 2,
                                },
                            ),
                        ],
                    })
            self.forecast.confirm([forecast_id])

            self.forecast.create_moves([forecast_id])
            forecast = self.forecast.browse(forecast_id)
            line, = forecast.lines
            self.assertEqual(line.quantity_executed, 0)
            self.assertEqual(len(line.moves), 5)
            self.assertEqual(sum(move.quantity for move in line.moves), 10)

            self.forecast.delete_moves([forecast_id])
            forecast = self.forecast.browse(forecast_id)
            line, = forecast.lines
            self.assertEqual(len(line.moves), 0)

            company = self.company.browse(company_id)
            self.move.create({
                    'from_location': storage_id,
                    'to_location': customer_id,
                    'product': product_id,
                    'uom': unit_id,
                    'quantity': 2,
                    'planned_date': today + relativedelta(months=1, day=5),
                    'company': company_id,
                    'currency': company.currency.id,
                    'unit_price': Decimal('1'),
                    })
            forecast = self.forecast.browse(forecast_id)
            line, = forecast.lines
            self.assertEqual(line.quantity_executed, 2)

            self.forecast.create_moves([forecast_id])
            forecast = self.forecast.browse(forecast_id)
            line, = forecast.lines
            self.assertEqual(line.quantity_executed, 2)
            self.assertEqual(len(line.moves), 4)
            self.assertEqual(sum(move.quantity for move in line.moves), 8)

def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.company.tests import test_company
    for test in test_company.suite():
        if test not in suite:
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            StockForecastTestCase))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
