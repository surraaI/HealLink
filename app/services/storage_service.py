import io
import time
from datetime import datetime, timezone
from uuid import uuid4

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from fastapi import UploadFile, HTTPException, status

from app.core.config import get_settings

settings = get_settings()

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)


async def upload_license_document(file: UploadFile, provider_type: str) -> str:
    # Validate MIME
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must be a PDF")

    # Read first bytes to check magic
    head = await file.read(4)
    if head != b"%PDF":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid PDF")

    # Read entire content to check size
    await file.seek(0)
    content = await file.read()
    max_size = 10 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF too large (max 10MB)")

    folder = f"heallink/licenses/{provider_type}/{uuid4().hex}"

    # Upload as raw resource
    try:
        # cloudinary.uploader.upload accepts file-like objects or bytes
        result = cloudinary.uploader.upload(
            io.BytesIO(content),
            resource_type="raw",
            folder=folder,
            access_mode="authenticated",
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload document") from exc

    secure_url = result.get("secure_url")
    if not secure_url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Upload returned no URL")
    return secure_url


def _extract_public_id(cloudinary_url: str) -> str:
    # Attempt to strip typical Cloudinary URL patterns to public_id
    # Example: https://res.cloudinary.com/<cloud>/raw/upload/v1234567890/folder/abc-uuid/filename.pdf
    parts = cloudinary_url.split("/")
    # find the index of 'upload' and take everything after version segment
    try:
        idx = parts.index("upload")
        public_parts = parts[idx + 2 :]
        public_id_with_ext = "/".join(public_parts)
        # strip extension
        if "." in public_id_with_ext:
            public_id = public_id_with_ext.rsplit(".", 1)[0]
        else:
            public_id = public_id_with_ext
        return public_id
    except ValueError:
        # fallback to entire path after cloud name
        return cloudinary_url


def generate_signed_url(cloudinary_url: str, expires_in: int = 3600) -> str:
    pub_id = _extract_public_id(cloudinary_url)
    # cloudinary.utils.private_download_url expects an expires_at timestamp
    expires_at = int(time.time()) + int(expires_in)
    try:
        url = cloudinary.utils.private_download_url(pub_id, resource_type="raw", expires_at=expires_at)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate signed URL") from exc
    return url


async def delete_document(cloudinary_url: str) -> None:
    pub_id = _extract_public_id(cloudinary_url)
    try:
        cloudinary.uploader.destroy(pub_id, resource_type="raw")
    except Exception:
        # Best-effort delete; swallow to avoid failing caller
        return


async def upload_profile_picture(file: UploadFile, user_type: str, user_id: int) -> str:
    # Validate MIME type for images
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file must be an image (JPEG, PNG, or WebP)"
        )

    # Read content to check size
    await file.seek(0)
    content = await file.read()
    max_size = 5 * 1024 * 1024  # 5MB
    if len(content) > max_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image too large (max 5MB)")

    folder = f"heallink/profiles/{user_type}/{user_id}"

    # Upload as image
    try:
        result = cloudinary.uploader.upload(
            io.BytesIO(content),
            resource_type="image",
            folder=folder,
            transformation=[
                {"width": 400, "height": 400, "crop": "fill", "gravity": "face"},
                {"quality": "auto"}
            ]
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload profile picture") from exc

    secure_url = result.get("secure_url")
    if not secure_url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Upload returned no URL")
    return secure_url
