"""Photo storage backends (D6)."""

import io

from app.storage.local import LocalPhotoStorage
from app.storage.s3_compatible import S3PhotoStorage


def test_local_round_trip(tmp_path):
    storage = LocalPhotoStorage(tmp_path)
    storage.save("reports/2026/11/a.jpg", b"jpeg")
    assert storage.read("reports/2026/11/a.jpg") == b"jpeg"
    storage.delete("reports/2026/11/a.jpg")
    assert storage.read("reports/2026/11/a.jpg") is None


class FakeS3:
    """Records calls like boto3's S3 client would receive them."""

    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        assert ContentType == "image/jpeg"
        self.objects[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise Exception("An error occurred (NoSuchKey) when calling the GetObject operation")
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)


def test_s3_round_trip():
    fake = FakeS3()
    storage = S3PhotoStorage("tracehealth-photos", client=fake)
    storage.save("reports/x.jpg", b"jpeg")
    assert fake.objects == {("tracehealth-photos", "reports/x.jpg"): b"jpeg"}
    assert storage.read("reports/x.jpg") == b"jpeg"
    storage.delete("reports/x.jpg")
    assert storage.read("reports/x.jpg") is None
