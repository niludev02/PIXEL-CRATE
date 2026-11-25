import mimetypes
import posixpath
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.core.exceptions import SuspiciousFileOperation
from django.utils.deconstruct import deconstructible

from .supabase_client import supabase


@deconstructible
class SupabasePublicMediaStorage(Storage):
    def __init__(self, bucket_name=None):
        self.bucket_name = bucket_name or settings.SUPABASE_STORAGE_BUCKET

    @property
    def bucket(self):
        return supabase.storage.from_(self.bucket_name)

    def _open(self, name, mode="rb"):
        if mode != "rb":
            raise ValueError("Supabase media files can only be opened in binary read mode.")
        return ContentFile(self.bucket.download(name), name=name)

    def _save(self, name, content):
        if hasattr(content, "seek"):
            content.seek(0)

        content_type = (
            getattr(content, "content_type", None)
            or mimetypes.guess_type(name)[0]
            or "application/octet-stream"
        )
        self.bucket.upload(
            name,
            content.read(),
            file_options={
                "content-type": content_type,
                "upsert": "false",
            },
        )
        return name

    def delete(self, name):
        self.bucket.remove([name])

    def exists(self, name):
        directory, filename = posixpath.split(name)
        files = self.bucket.list(directory or "")
        return any(file.get("name") == filename for file in files)

    def get_available_name(self, name, max_length=None):
        directory, filename = posixpath.split(name)
        extension = posixpath.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{extension}"
        available_name = posixpath.join(directory, unique_filename) if directory else unique_filename

        if max_length is not None and len(available_name) > max_length:
            raise SuspiciousFileOperation("The generated storage name exceeds the field's maximum length.")

        return available_name

    def url(self, name):
        return self.bucket.get_public_url(name)
