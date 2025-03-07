from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI

PETABYTE_IN_BYTES = 1e15


class FileSystemService:

    @staticmethod
    def get_file_system_stats() -> dict:
        file_system_stats = QumuloAPI().get_file_system_stats()
        total_size = FileSystemService._get_size_in_pt(
            file_system_stats.get("total_size_bytes")
        )
        free_size = FileSystemService._get_size_in_pt(
            file_system_stats.get("free_size_bytes")
        )
        snapshot_size = FileSystemService._get_size_in_pt(
            file_system_stats.get("snapshot_size_bytes")
        )
        return {
            "total_size": total_size,
            "free_size": free_size,
            "snapshot_size": snapshot_size,
        }

    @staticmethod
    def _get_size_in_pt(size_in_bytes: int) -> float:
        if size_in_bytes is None:
            return None

        return round(FileSystemService._bytes_to_petabytes(int(size_in_bytes)), 4)

    @staticmethod
    def _bytes_to_petabytes(value_in_bytes: int) -> float:
        return value_in_bytes / PETABYTE_IN_BYTES
