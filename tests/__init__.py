# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

try:
    from trytond.modules.sale_product_customer.tests.test_sale_product_customer import \
        suite  # noqa: E501
except ImportError:
    from .test_sale_product_customer import suite

__all__ = ['suite']
