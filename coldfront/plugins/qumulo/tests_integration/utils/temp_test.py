from coldfront_plugin_qumulo.utils.qumulo_api import QumuloAPI
import json

# jprew - TODO - what is this file?

qumulo_instance = QumuloAPI()

file_attr = qumulo_instance.rc.nfs.nfs_get_export("test-proejct")

print("exports: ", json.dumps(file_attr, indent=2))
