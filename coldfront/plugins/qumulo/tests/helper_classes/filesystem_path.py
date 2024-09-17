from qumulo.lib import request
from unittest.mock import MagicMock


# "Path exists" is a condition where the mocked call to Qumulo's
# get_file_attr() function returns (None) without raising
# request.RequestError
class PathExistsMock(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.side_effect = self._pathExistsMock

    def _pathExistsMock(self, *args, **kwargs):
        return None


# A valid form's filesystem path for a parent allocation is mocked
# by returning None on the top 2 levels of a path (e.g. /storage2/fs1)
# and raising request.RequestError at the 3rd level.
class ValidFormPathMock(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.side_effect = self._prefixExistsSubDoesNot

    def _prefixExistsSubDoesNot(self, *args, **kwargs):
        if len(args[0].strip("/").split("/")) <= 2:
            return None
        raise request.RequestError(
            404,
            "File not found",
            {
                "error_class": "fs_no_such_entry_error",
                "description": "Path does not exist",
            },
        )
