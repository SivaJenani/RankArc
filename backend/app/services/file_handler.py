import os
import uuid

import aiofiles
from fastapi import UploadFile


async def save_upload_file(
    file: UploadFile,
    user_id: int,
    upload_dir: str,
) -> tuple[str, str]:
    """Save an uploaded file to disk.

    Returns:
        (filename, file_path) where filename is a UUID-based name and
        file_path is the full path on disk.
    """
    user_dir = os.path.join(upload_dir, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    original_ext = ""
    if file.filename:
        _, original_ext = os.path.splitext(file.filename)

    unique_name = f"{uuid.uuid4().hex}{original_ext}"
    file_path = os.path.join(user_dir, unique_name)

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    return unique_name, file_path
