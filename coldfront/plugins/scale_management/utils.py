# from bs4 import BeautifulSoup

from coldfront.core.utils.common import import_from_settings


def get_scale_management_context():
    context = {}
    system_monitor = ScaleManagement()

    return context


class ScaleManagement:
    """If anything fails, the home page will still work"""
    primary_color = '#002f56'
    info_color = '#2f9fd0'
    secondary_color = '#666666'

    def __init__(self):
        self.response = None
        self.data = {}
