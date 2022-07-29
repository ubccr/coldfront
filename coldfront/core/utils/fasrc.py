"""A module for fasrc-specific utility functions
"""

from ifxbilling.models import Product


def determine_size_fmt(byte_num):
    unit = "B"
    for u in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if abs(byte_num) < 1024.0:
            return round(byte_num, 3), unit
        byte_num /= 1024.0
        unit = u

def convert_size_fmt(num, target_unit, source_unit="B"):
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]
    diff = units.index(target_unit) - units.index(source_unit)
    if diff == 0:
        pass
    elif diff > 0:
        for i in range(diff):
            num/=1024.0
    elif diff < 0:
        for i in range(abs(diff)):
            num*=1024.0
    return round(num, 3)

def get_resource_rate(resource):
    """find Product with the name provided and return the associated rate"""
    prod_obj = Product.objects.get(product_name=resource)
    rate_obj = prod_obj.rate_set.get(is_active=True)
    # return charge per TB, adjusted to dollar value
    if rate_obj.units == "TB":
        return rate_obj.price/100
    price = convert_size_fmt(rate_obj.price, "TB", source_unit=rate_obj.units)
    return round(price/100, 2)
