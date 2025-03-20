import grpc

from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.lfs.lfsprotobuffer.pb_python import lfsprotobuffer_pb2, lfsprotobuffer_pb2_grpc

LFS_HOST = import_from_settings('LFS_HOST', 'localhost')
LFS_PORT = import_from_settings('LFS_PORT', 50051)

class GrpcClient:
    def __init__(self, host=LFS_HOST, port=LFS_PORT):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.groups_stub = lfsprotobuffer_pb2_grpc.GroupsStub(self.channel)
        self.filesystems_stub = lfsprotobuffer_pb2_grpc.FilesystemsStub(self.channel)
        self.quotas_stub = lfsprotobuffer_pb2_grpc.QuotasStub(self.channel)

    def update_filesystem_stats(self):
        stub = lfsprotobuffer_pb2_grpc.FilesystemStatsStub(self.channel)
        request = lfsprotobuffer_pb2.UpdateFilesystemStatsRequest()
        response = stub.UpdateFilesystemStats(request)
        return response

    def get_group_by_id(self, group_id):
        request = lfsprotobuffer_pb2.GroupRequestById(id=group_id)
        return self.groups_stub.GetGroupById(request)

    def get_group_by_name(self, group_name):
        request = lfsprotobuffer_pb2.GroupRequestByName(name=group_name)
        return self.groups_stub.GetGroupByName(request)

    def list_groups(self):
        request = lfsprotobuffer_pb2.voidNoParam()
        return self.groups_stub.ListGroups(request)

    def get_filesystem_by_id(self, filesystem_id):
        request = lfsprotobuffer_pb2.FilesystemRequestById(id=filesystem_id)
        return self.filesystems_stub.GetFilesystemById(request)

    def get_filesystem_by_name(self, filesystem_name):
        request = lfsprotobuffer_pb2.FilesystemRequestByName(name=filesystem_name)
        return self.filesystems_stub.GetFilesystemByName(request)

    def list_filesystems(self):
        request = lfsprotobuffer_pb2.voidNoParam()
        responses = self.filesystems_stub.ListFilesystems(request)
        return [response for response in responses]

    def get_quotas(self, group_id=None, filesystem_uid=None, group_name=None, filesystem_name=None):
        request = lfsprotobuffer_pb2.QuotaRequest(
            group_uid=group_id,
            filesystem_uid=filesystem_uid,
            group_name=group_name,
            filesystem_name=filesystem_name
        )
        return self.quotas_stub.GetQuotas(request)

    def get_quota_by_id(self, quota_id):
        request = lfsprotobuffer_pb2.QuotaRequestById(id=quota_id)
        return self.quotas_stub.GetQuotaById(request)

    def get_quotas_by_date(self, date, before):
        request = lfsprotobuffer_pb2.QuotaRequestByDate(date=date, before=before)
        return self.quotas_stub.GetQuotasByDate(request)

    def list_quotas(self):
        request = lfsprotobuffer_pb2.voidNoParam()
        return self.quotas_stub.ListQuotas(request)
