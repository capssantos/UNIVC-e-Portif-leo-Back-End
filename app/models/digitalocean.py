# app/services/spaces_uploader.py
import base64
import imghdr
import uuid
from datetime import datetime
from typing import Tuple, Optional

import boto3

class DigitalOceanSpacesUploader:
    """
    Sobe arquivos para o DigitalOcean Spaces (compatível S3).
    Uso básico:
        uploader = DigitalOceanSpacesUploader(
            access_key=...,
            secret_key=...,
            bucket="onicode",
            region="nyc3",
            endpoint="https://nyc3.digitaloceanspaces.com",
            cdn_base="https://onicode.nyc3.digitaloceanspaces.com"  # para montar URL pública
        )
        key, url = uploader.upload_base64_to_path("Vision/img-original", img_b64, filename_hint="foto.png")
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
        """
        Remove cabeçalho de data URL: 'data:image/png;base64,....'
        """
        if data.startswith("data:"):
            # Ex.: data:image/png;base64,AAAA...
            head, _, rest = data.partition("base64,")
            return rest if rest else data
        return data

    @staticmethod
    def _detect_ext(img_bytes: bytes) -> str:
        """
        Detecta extensão da imagem usando imghdr.
        Retorna 'jpg' para 'jpeg' por convenção.
        """
        kind = imghdr.what(None, h=img_bytes)  # 'jpeg', 'png', 'gif', etc.
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

    # --- public --------------------------------------------------------------

    def upload_base64_to_path(
        self,
        base_path: str,
        image_base64: str,
        filename_hint: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Faz upload de uma imagem base64 para o path informado (ex.: 'Vision/img-original')
        Retorna (object_key, public_url)
        """
        if not image_base64:
            raise ValueError("Imagem em base64 não informada.")

        raw_b64 = self._strip_data_url_prefix(image_base64)

        try:
            img_bytes = base64.b64decode(raw_b64, validate=True)
        except Exception as exc:
            raise ValueError("Base64 inválido.") from exc

        # extensão (tentamos por imghdr; se houver dica no nome, usamos ela)
        ext = self._detect_ext(img_bytes)
        if filename_hint and "." in filename_hint:
            hint_ext = filename_hint.rsplit(".", 1)[-1].lower()
            if hint_ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff"}:
                ext = "jpg" if hint_ext == "jpeg" else hint_ext

        content_type = self._guess_content_type(ext)

        # key: Vision/img-original/2025/09/30/<uuid>.ext
        today = datetime.utcnow()
        object_key = f"{base_path.rstrip('/')}/{today:%Y/%m/%d}/{uuid.uuid4().hex}.{ext}"

        extra_args = {"ContentType": content_type}
        if self.public_read:
            extra_args["ACL"] = "public-read"

        self._s3.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=img_bytes,
            **extra_args,
        )

        public_url = f"{self.cdn_base}/{object_key}"
        return object_key, public_url
