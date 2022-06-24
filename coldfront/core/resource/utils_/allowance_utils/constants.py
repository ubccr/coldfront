class Allowances(object):
    """Names of Resource objects corresponding to common computing
    allowances."""
    CO = 'Condo Allocation'
    RECHARGE = 'Recharge Allocation'


class BRCAllowances(Allowances):
    """Names of Resource objects corresponding to BRC-exclusive
    computing allowances."""
    FCA = 'Faculty Computing Allowance'
    ICA = 'Instructional Computing Allowance'
    PCA = 'Partner Computing Allowance'


class LRCAllowances(Allowances):
    """Names of Resource objects corresponding to LRC-exclusive
    computing allowances."""
    PCA = 'PI Computing Allowance'
