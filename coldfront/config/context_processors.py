import os

def export_vars(request):
    data = {}
    data['PLUGIN_FASRC_MONITORING'] = os.environ.get('PLUGIN_FASRC_MONITORING', False)
    return data
