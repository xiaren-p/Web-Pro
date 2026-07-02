"""图片文件安全校验与处理工具（image_validator）。

提供三重校验：Magic Number（PIL 实际解码）+ 白名单格式 + 大小限制，
并附带服务端居中裁剪 + 缩放工具函数，供头像/图片上传端点统一复用。
"""
import io
from typing import IO

from PIL import Image


# 白名单格式：PIL format_name → (推荐扩展名, MIME 类型)
_ALLOWED_FORMATS: dict[str, tuple[str, str]] = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}

# 默认最大体积（MB）
_DEFAULT_MAX_MB = 5


def validate_image_file(
    file: IO,
    *,
    max_mb: int = _DEFAULT_MAX_MB,
) -> tuple[str, str]:
    """用 PIL 做 Magic Number 校验，确认文件是合法图片且格式在白名单内。

    Args:
        file (IO): 文件对象，本函数调用后会 seek(0) 归位，供后续处理复用。
        max_mb (int): 允许的最大文件体积（MB），默认 5。

    Returns:
        tuple[str, str]: (推荐扩展名, MIME 类型)，例如 ('.jpg', 'image/jpeg')。

    Raises:
        ValueError: 超过大小限制、Magic Number 不合法或格式不在白名单时抛出，
                    携带适合直接返回给前端的中文描述。
    """
    # ① 大小校验：seek 到末尾取字节数
    file.seek(0, 2)
    size_bytes = file.tell()
    file.seek(0)
    if size_bytes > max_mb * 1024 * 1024:
        raise ValueError(f"图片过大，不能超过 {max_mb}MB")

    # ② Magic Number 校验：PIL.Image.open 读取文件头魔数
    try:
        img = Image.open(file)
        # verify() 仅读元信息不完整解码，用于快速鉴别格式；
        # 调用后 img 对象不可再用，需 seek(0) 重新 open
        img.verify()
    except Exception:
        raise ValueError("文件不是合法图片（格式验证失败）")
    finally:
        file.seek(0)

    # ③ 白名单格式校验
    fmt = (img.format or "").upper()
    if fmt not in _ALLOWED_FORMATS:
        allowed = "、".join(_ALLOWED_FORMATS.keys())
        raise ValueError(f"图片格式不在白名单，仅支持 {allowed}")

    ext, mime = _ALLOWED_FORMATS[fmt]
    return ext, mime


def resize_image_to_square(
    file: IO,
    *,
    size: int = 512,
) -> io.BytesIO:
    """将图片居中裁剪为正方形后缩放至指定边长，输出 JPEG 格式字节流。

    处理流程：
      1. 统一转换为 RGB（处理 RGBA / P 等模式）
      2. 以短边为基准居中裁剪为正方形
      3. 缩放至 size × size（LANCZOS 高质量重采样）
      4. JPEG 压缩输出（quality=85，optimize=True）

    Args:
        file (IO): 原始图片文件对象（函数内部会 seek(0)）。
        size (int): 输出正方形边长（像素），默认 512。

    Returns:
        io.BytesIO: 处理后的图片字节流，位置归 0 可直接读取或保存。
    """
    file.seek(0)
    img = Image.open(file)

    # 统一转为 RGB，避免 RGBA / P 模式在 JPEG 编码时报错
    img = img.convert("RGB")

    # 居中裁剪为正方形（以短边为准）
    width, height = img.size
    short = min(width, height)
    left = (width - short) // 2
    top = (height - short) // 2
    img = img.crop((left, top, left + short, top + short))

    # 缩放至目标尺寸
    img = img.resize((size, size), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    buf.seek(0)
    return buf
