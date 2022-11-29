# -*- coding: utf-8 -*-

'''
Filters for coldfront templates

Created on  2021-06-23

@author: Meghan Correa <mportermahoney@g.harvard.edu>
@copyright: 2021 The Presidents and Fellows of Harvard College.
All rights reserved.
@license: GPL v2.0
'''
import decimal
import re
from django import template

register = template.Library()

def val_sign(val):
    '''
    Return string tuple of the absolute value of val and a sign string.  (val, '') if positive and (val, '-') if negative
    '''
    return (f'{val:,}', '') if val > 0 else (f'{abs(val):,}', '-')

@register.filter(name='dollars')
def dollars(pennies):
    '''
    convert pennies to dollars if digit
    '''
    try:
        int(pennies)
    except ValueError:
        return pennies
    cent = decimal.Decimal('0.01')
    valstr, signstr = val_sign(decimal.Decimal(int(pennies)/100).quantize(cent, decimal.ROUND_HALF_UP))
    return f'{signstr}${valstr}'

@register.filter(name='just_dollars')
def just_dollars(val):
    '''
    Only display as dollars without penny conversion
    '''
    try:
        int(val)
    except ValueError:
        return val
    cent = decimal.Decimal('0.01')
    valstr, signstr = val_sign(decimal.Decimal(val).quantize(cent, decimal.ROUND_HALF_UP))
    return f'{signstr}${valstr}'

@register.filter(name='bytestotbs')
def bytestotbs(bytes):
    '''
    Convert bytes to TB
    '''
    if not str(bytes).isdigit():
        return bytes
    val = decimal.Decimal(bytes / 1024**4).quantize(decimal.Decimal('1.00'))
    return str(val)

@register.filter(name='brtonl')
def brtonl(text):
    '''
    Convert <br/>s to \n
    '''
    if text:
        return text.replace(r'<br>', '\n')
    return text

@register.filter(name='liters')
def liters(ml):
    '''
    Convert ml to L
    '''
    if ml:
        return decimal.Decimal(ml / 1000).quantize(decimal.Decimal('1.0'))
    return ml

@register.filter(name='mintohour')
def mintohour(min):
    '''
    Convert minutes to hours
    '''
    if min:
        return decimal.Decimal(min / 60).quantize(decimal.Decimal('1.0'))
    return min

@register.filter(name='rcproduct')
def rcproduct(text):
    '''
    Converts holylfs04/tier0 to holylfs04 / tier0 so that it will wrap
    '''
    if text:
        return re.sub(r'(\S)/(\S)', r'\1 / \2', text)
    return text
