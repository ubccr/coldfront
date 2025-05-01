import os
from typing import Any, Optional
import requests

from coldfront.plugins.qumulo.services.itsm.fields.itsm_to_coldfront_fields_factory import (
    itsm_attributes,
)


class ItsmClient:
    def __init__(self):
        self.user = os.environ.get("ITSM_SERVICE_USER")
        self.password = os.environ.get("ITSM_SERVICE_PASSWORD")
        self.host = os.environ.get("ITSM_HOST")
        protocol = os.environ.get("ITSM_PROTOCOL")
        port = os.environ.get("ITSM_REST_API_PORT")
        endpoint_path = os.environ.get("ITSM_SERVICE_PROVISION_ENDPOINT")

        itsm_fields = ",".join(itsm_attributes)
        self.url = (
            f"{protocol}://{self.host}:{port}{endpoint_path}?attribute={itsm_fields}"
        )

    def get_fs1_allocation_by_fileset_name(self, fileset_name) -> str:
        return self._get_fs1_allocation_by("fileset_name", fileset_name)

    def get_fs1_allocation_by_fileset_alias(self, fileset_alias) -> str:
        return self._get_fs1_allocation_by("fileset_alias", fileset_alias)

    def get_fs1_allocation_by_storage_provision_name(
        self, storage_provision_name
    ) -> str:
        return self._get_fs1_allocation_by("name", storage_provision_name)

    # TODO is there a way to get the name of the environment such as prod, qa, or localhost?
    def _is_itsm_localhost(self):
        return self.host == "localhost"

    def _get_fs1_allocation_by(self, fileset_key, fileset_value) -> str:
        filtered_url = self._get_filtered_url(fileset_key, fileset_value)
        session = self._get_session()
        response = session.get(filtered_url, verify=self._get_verify_certificate())
        response.raise_for_status()

        data = response.json().get("data")
        session.close()
        return data

    def _get_filtered_url(self, fileset_key, fileset_value) -> str:
        itsm_active_allocation_service_id = 1
        filters = f'filter={{"{fileset_key}":"{fileset_value}","status":"active","service_id":{itsm_active_allocation_service_id}}}'
        return f"{self.url}&{filters}"

    def _get_session(self) -> requests.Session:
        session = requests.Session()
        session.auth = self._get_session_authentication()
        session.headers = self._get_session_headers()
        return session

    def _get_session_headers(self) -> dict:
        headers = {"content-type": "application/json"}
        if self._is_itsm_localhost():
            headers["x-remote-user"] = self.user

        return headers

    def _get_session_authentication(self) -> Optional[tuple]:
        if self._is_itsm_localhost():
            return None

        return (self.user, self.password)

    def _get_verify_certificate(self) -> Any:
        # Unfortunately, the verify attribute could be a path where the certificate is located or bool
        return os.environ.get("RIS_CHAIN_CERTIFICATE") or True
