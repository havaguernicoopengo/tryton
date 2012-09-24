#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta

__all__ = ['Move']
__metaclass__ = PoolMeta


class Move:
    __name__ = 'stock.move'
    anglo_saxon_quantity = fields.Float('Anglo-Saxon Quantity', required=True,
        digits=(16, Eval('unit_digits', 2)), depends=['unit_digits'])

    @classmethod
    def __setup__(cls):
        super(Move, cls).__setup__()
        cls._sql_constraints += [
            ('check_anglo_saxon_quantity',
                'CHECK(quantity >= anglo_saxon_quantity)',
                'Anglo-Saxon quantity can not be greater than quantity!'),
            ]

    @staticmethod
    def default_anglo_saxon_quantity():
        return 0.0

    def _get_account_stock_move_lines(self, type_):
        pool = Pool()
        Uom = pool.get('product.uom')
        AccountMoveLine = pool.get('account.move.line')
        lines = super(Move, self)._get_account_stock_move_lines(type_)
        if (type_.endswith('supplier')
                and self.product.cost_price_method == 'fixed'):
            cost_price = Uom.compute_price(self.product.default_uom,
                self.cost_price, self.uom)
            amount = self.company.currency.round(
                Decimal(str(self.quantity)) * (self.unit_price - cost_price))
            if self.company.currency.is_zero(amount):
                return lines
            account = self.product.account_stock_supplier_used
            for move_line in lines:
                if move_line.account == account:
                    break
            else:
                return lines
            if type_.startswith('in_'):
                move_line.credit += amount
                debit = amount
                credit = Decimal(0)
            else:
                move_line.debit += amount
                debit = Decimal(0)
                credit = amount
            if amount < Decimal(0):
                debit, credit = -credit, -debit
            move_line = AccountMoveLine(
                name=self.rec_name,
                debit=debit,
                credit=credit,
                account=self.product.account_expense_used,
                )
            lines.append(move_line)
        return lines

    @classmethod
    def _get_anglo_saxon_move(cls, moves, quantity):
        '''
        Generator of (move, qty) where move is the move to be consumed and qty
        is the quantity (in the product default uom) to be consumed on this
        move.
        '''
        Uom = Pool().get('product.uom')

        consumed_qty = 0.0
        for move in moves:
            qty = Uom.compute_qty(move.uom,
                    move.quantity - move.anglo_saxon_quantity,
                    move.product.default_uom, round=False)
            if qty <= 0.0:
                continue
            if qty > quantity - consumed_qty:
                qty = quantity - consumed_qty
            if consumed_qty >= quantity:
                break
            yield (move, qty)

    @classmethod
    def update_anglo_saxon_quantity_product_cost(cls, product, moves,
            quantity, uom, type_):
        '''
        Return the cost for quantity based on lines.
        Update anglo_saxon_quantity on the concerned moves.
        '''
        Uom = Pool().get('product.uom')

        for move in moves:
            assert move.product == product, 'wrong product'
        assert type_.startswith('in_') or type_.startswith('out_'), \
            'wrong type'

        total_qty = Uom.compute_qty(uom, quantity, product.default_uom,
                round=False)

        cost = Decimal('0.0')
        consumed_qty = 0.0
        for move, move_qty in cls._get_anglo_saxon_move(moves, total_qty):
            consumed_qty += move_qty

            if type_.startswith('in_'):
                move_cost_price = Uom.compute_price(move.uom,
                        move.unit_price, move.product.default_uom)
            else:
                move_cost_price = move.cost_price
            cost += move_cost_price * Decimal(str(move_qty))

            cls.write([move], {
                'anglo_saxon_quantity': ((move.anglo_saxon_quantity or 0.0)
                    + move_qty),
                })

        if consumed_qty < total_qty:
            qty = total_qty - consumed_qty
            consumed_qty += qty
            cost += product.cost_price * Decimal(str(qty))
        return cost

    @classmethod
    def copy(cls, moves, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default.setdefault('anglo_saxon_quantity',
            cls.default_anglo_saxon_quantity())
        return super(Move, cls).copy(moves, default=default)
