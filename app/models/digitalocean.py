# app/services/digitalocean.py
import base64
import imghdr
import uuid
from datetime import datetime
from typing import Tuple, Optional

import boto3

class DigitalOceanSpacesUploader:
    """
    Sobe arquivos para o DigitalOcean Spaces (compatível S3).
    """

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "nyc3",
        endpoint: str = "https://nyc3.digitaloceanspaces.com",
        cdn_base: Optional[str] = None,
        public_read: bool = True,
    ) -> None:
        self.bucket = bucket
        self.public_read = public_read
        self.cdn_base = cdn_base or f"https://{bucket}.{region}.digitaloceanspaces.com"

        self._s3 = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    # --- utils ---------------------------------------------------------------

    @staticmethod
    def _strip_data_url_prefix(data: str) -> str:
        if data.startswith("data:"):
            _, _, rest = data.partition("base64,")
            return rest if rest else data
        return data

    @staticmethod
    def _detect_ext(img_bytes: bytes) -> str:
        kind = imghdr.what(None, h=img_bytes)  # 'jpeg', 'png', etc
        if kind == "jpeg":
            return "jpg"
        return kind or "bin"

    @staticmethod
    def _guess_content_type(ext: str) -> str:
        mapping = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "bmp": "image/bmp",
            "tiff": "image/tiff",
        }
        return mapping.get(ext.lower(), "application/octet-stream")

    def _build_object_key(self, base_path: str, ext: str) -> str:
        today = datetime.utcnow()
        return f"{base_path.rstrip('/')}/{today:%Y/%m/%d}/{uuid.uuid4().hex}.{ext}"

    def _put(self, object_key: str, content_type: str, body: bytes) -> str:
        extra_args = {"ContentType": content_type}
        if self.public_read:
            extra_args["ACL"] = "public-read"

        self._s3.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=body,
            **extra_args,
        )

        return f"{self.cdn_base}/{object_key}"

    # --- public: base64 ------------------------------------------------------

    def upload_base64_to_path(
        self,
        base_path: str,
        image_base64: str,
        filename_hint: Optional[str] = None,
    ) -> Tuple[str, str]:
        if not image_base64:
            raise ValueError("Imagem em base64 não informada.")

        raw_b64 = self._strip_data_url_prefix(image_base64)

        try:
            img_bytes = base64.b64decode(raw_b64, validate=True)
        except Exception as exc:
            raise ValueError("Base64 inválido.") from exc

        ext = self._detect_ext(img_bytes)

        if filename_hint and "." in filename_hint:
            hint_ext = filename_hint.rsplit(".", 1)[-1].lower()
            if hint_ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff"}:
                ext = "jpg" if hint_ext == "jpeg" else hint_ext

        content_type = self._guess_content_type(ext)
        object_key = self._build_object_key(base_path, ext)
        public_url = self._put(object_key, content_type, img_bytes)
        return object_key, public_url

    # --- public: arquivo (form-data) ----------------------------------------

    def upload_file_to_path(
        self,
        base_path: str,
        file_bytes: bytes,
        filename_hint: Optional[str] = None,
    ) -> Tuple[str, str]:
        if not file_bytes:
            raise ValueError("Arquivo vazio.")

        ext = self._detect_ext(file_bytes)

        if filename_hint and "." in filename_hint:
            hint_ext = filename_hint.rsplit(".", 1)[-1].lower()
            if hint_ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff"}:
                ext = "jpg" if hint_ext == "jpeg" else hint_ext

        content_type = self._guess_content_type(ext)
        object_key = self._build_object_key(base_path, ext)
        public_url = self._put(object_key, content_type, file_bytes)
        return object_key, public_url
