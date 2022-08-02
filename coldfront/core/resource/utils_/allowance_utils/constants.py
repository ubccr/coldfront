class Allowances(object):
    """Names of Resource objects corresponding to common computing
    allowances."""
    RECHARGE = 'Recharge Allocation'


class BRCAllowances(Allowances):
    """Names of Resource objects corresponding to BRC-exclusive
    computing allowances."""
    CO = 'Condo Allocation'
    FCA = 'Faculty Computing Allowance'
    ICA = 'Instructional Computing Allowance'
    PCA = 'Partner Computing Allowance'


class LRCAllowances(Allowances):
    """Names of Resource objects corresponding to LRC-exclusive
    computing allowances."""
    LR = 'Condo Allocation'
    PCA = 'PI Computing Allowance'
