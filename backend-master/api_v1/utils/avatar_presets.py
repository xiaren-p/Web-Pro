"""预设头像配置（avatar_presets）。

维护系统内置的 12 个预设头像种子 ID，供用户创建时随机分配以及前端选择器渲染使用。
前端通过 @dicebear/thumbs + 对应 seed 在本地生成 SVG，无需存储图片文件。
DB 中以 'preset:01' ~ 'preset:12' 格式标识，区别于上传头像的 HTTP URL。
"""
import random

# 系统内置预设头像数量
PRESET_COUNT = 12

# DB 存储前缀（与前端约定保持一致）
PRESET_PREFIX = "preset:"


def get_random_preset() -> str:
    """随机返回一个预设头像标识符，格式 'preset:01' ~ 'preset:12'。

    用于用户创建时自动分配默认头像，确保每位新用户都有独特的初始外观。

    Returns:
        str: 预设头像标识，如 'preset:07'。
    """
    idx = random.randint(1, PRESET_COUNT)
    return f"{PRESET_PREFIX}{idx:02d}"


def is_preset(avatar: str) -> bool:
    """判断 avatar 字段值是否为系统预设头像标识（而非用户上传的 URL）。

    Args:
        avatar (str): UserProfile.avatar 字段值。

    Returns:
        bool: True 表示预设头像，False 表示用户自行上传的图片 URL。
    """
    return bool(avatar) and avatar.startswith(PRESET_PREFIX)


def is_local_upload(avatar: str) -> bool:
    """判断 avatar 字段值是否为系统本地上传路径（非预设、非外部 URL）。

    用于判断是否需要在覆盖时清理旧文件。

    Args:
        avatar (str): UserProfile.avatar 字段值。

    Returns:
        bool: True 表示本地上传文件，需在覆盖时清理磁盘文件。
    """
    if not avatar:
        return False
    if is_preset(avatar):
        return False
    # 外部 URL（gitee、gravatar 等旧默认头像）不属于本地文件
    if avatar.startswith(("http://", "https://")):
        # 本系统域内上传文件的 URL 特征：含 /media/uploads/avatars/
        return "/media/uploads/avatars/" in avatar
    # 相对路径格式（如 uploads/avatars/...）
    return avatar.startswith("uploads/avatars/")


# 与前端 avatarPresets.ts backgroundColor 数组一一对应（12 色）
PRESET_COLORS: dict[str, str] = {
    "preset:01": "5c6bc0",
    "preset:02": "42a5f5",
    "preset:03": "26c6da",
    "preset:04": "66bb6a",
    "preset:05": "ffa726",
    "preset:06": "ef5350",
    "preset:07": "ab47bc",
    "preset:08": "26a69a",
    "preset:09": "8d6e63",
    "preset:10": "78909c",
    "preset:11": "ec407a",
    "preset:12": "7e57c2",
}


def make_preset_png(username: str, preset_id: str) -> bytes:
    """用 Pillow 生成与前端预设色匹配的头像，返回 PNG bytes。

    正方形背景使用与前端 @dicebear/thumbs 相同的 12 色调色板，
    圆心绘制用户名首字母（大写白色）。生成 256×256 PNG。

    Args:
        username (str): Django 用户名，取首字母作为头像文字。
        preset_id (str): 预设标识符，如 'preset:06'，用于查调色板。

    Returns:
        bytes: PNG 二进制，可直接传给 NcApiClient.upload_own_avatar()。
    """
    import io
    from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]

    size = 256
    hex_color = PRESET_COLORS.get(preset_id, "5c6bc0")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    # 正方形画布（NC 会自动裁圆）
    img = Image.new("RGB", (size, size), (r, g, b))
    draw = ImageDraw.Draw(img)

    # 首字母居中
    letter = (username[0] if username else "U").upper()
    font_size = 110
    try:
        # Pillow >= 10.0 支持 load_default(size=)
        font = ImageFont.load_default(size=font_size)  # type: ignore[call-arg]
    except TypeError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), letter, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2 - bbox[0]
    y = (size - text_h) // 2 - bbox[1]
    draw.text((x, y), letter, fill=(255, 255, 255), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
