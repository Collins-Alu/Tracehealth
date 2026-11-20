"""
Photos in S3-compatible object storage (AWS S3, Cloudflare R2, MinIO).

Used when STORAGE_BACKEND=s3, so the API can run on more than one server, or
on a host with no permanent disk. The bucket must be PRIVATE: photos are only
ever served through the API's permission-checked /reports/{id}/photo.
"""


class S3PhotoStorage:
    name = "s3"

    def __init__(self, bucket: str, client=None, **client_options):
        if client is None:
            import boto3  # imported only when S3 storage is actually used

            client = boto3.client("s3", **{k: v for k, v in client_options.items() if v})
        self._client = client
        self._bucket = bucket

    def save(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType="image/jpeg")

    def read(self, key: str) -> bytes | None:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except Exception as exc:  # botocore ClientError: NoSuchKey
            if "NoSuchKey" in str(exc) or "Not Found" in str(exc) or "404" in str(exc):
                return None
            raise
        return response["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
