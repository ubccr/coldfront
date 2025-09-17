from vastpy import VASTClient
from coldfront.config.plugins.vast import VASTUSER, VASTPASS, VASTADDRESS

client = VASTClient(
    address=VASTADDRESS,
    user=VASTUSER,
    password=VASTPASS,
)
