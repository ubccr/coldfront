import grpc

from coldfront.plugins.lfs.lfsprotobuffer.gen.pb_python import lfsprotobuffer_pb2, lfsprotobuffer_pb2_grpc

class GrpcClient:
    def __init__(self, host='localhost', port=50051):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.groups_stub = lfsprotobuffer_pb2_grpc.GroupsStub(self.channel)
        self.filesystems_stub = lfsprotobuffer_pb2_grpc.FilesystemsStub(self.channel)
        self.quotas_stub = lfsprotobuffer_pb2_grpc.QuotasStub(self.channel)

    def get_groups(self, group_id):
        request = lfsprotobuffer_pb2.GroupRequest(id=group_id)
        response = self.groups_stub.GetGroups(request)
        return response

    def list_groups(self):
        request = lfsprotobuffer_pb2.voidNoParam()
        responses = self.groups_stub.ListGroups(request)
        return [response for response in responses]

    def get_filesystems(self, filesystem_id):
        request = lfsprotobuffer_pb2.FilesystemRequest(id=filesystem_id)
        response = self.filesystems_stub.GetFilesystems(request)
        return response

    def list_filesystems(self):
        request = lfsprotobuffer_pb2.voidNoParam()
        responses = self.filesystems_stub.ListFilesystems(request)
        return [response for response in responses]

    def get_quotas(self, quota_id):
        request = lfsprotobuffer_pb2.QuotaRequest(id=quota_id)
        response = self.quotas_stub.GetQuotas(request)
        return response

    def list_quotas(self):
        request = lfsprotobuffer_pb2.voidNoParam()
        responses = self.quotas_stub.ListQuotas(request)
        return [response for response in responses]

