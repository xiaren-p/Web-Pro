"""验证码工具模块。

模块说明：生成图形验证码（PNG base64）并在缓存中存储答案，提供校验函数 `validate_captcha`。
在无 PIL 环境下回退为透明 1x1 PNG。
"""
import uuid, base64, io, random, string
from django.core.cache import cache

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


def generate_captcha(width: int = 120, height: int = 40, length: int = 4, expire: int = 300):
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    key = uuid.uuid4().hex
    cache.set(f"captcha:{key}", text, timeout=expire)
    if not PIL_AVAILABLE:
        transparent_png = base64.b64encode(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT\x08\x99c``\x00\x00\x00\x04\x00\x01\x0b\xe7\x02\x9d\x00\x00\x00\x00IEND\xaeB`\x82").decode()
        return key, f"data:image/png;base64,{transparent_png}", text
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    for _ in range(6):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line(((x1, y1), (x2, y2)), fill=(200, 200, 200), width=1)
    # try several common TTF font locations first; fall back to default
    font = None
    font_size = max(12, int(height * 0.7))
    # common font paths on Linux and project-local fallback
    try_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "arial.ttf",
    ]
    # also check a project-local fonts directory (if you bundle a font)
    try:
        from pathlib import Path
        base = Path(__file__).resolve().parent.parent
        try_paths.append(str(base / 'static' / 'fonts' / 'DejaVuSans.ttf'))
        try_paths.append(str(base / 'static' / 'fonts' / 'arial.ttf'))
    except Exception:
        pass

    for p in try_paths:
        try:
            font = ImageFont.truetype(p, font_size)
            break
        except Exception:
            font = None
    if font is None:
        # fallback to PIL default (may be small); keep font_size attempt
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
    # compute text bbox; if font is None use default measurement
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2:]
    except Exception:
        w, h = draw.textsize(text)
    draw.text(((width - w) / 2, (height - h) / 2), text, font=font, fill=(50, 50, 50))
    image = image.filter(ImageFilter.SMOOTH)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return key, f"data:image/png;base64,{b64}", text


def validate_captcha(key: str, code: str) -> bool:
    """Validate captcha code stored in cache.

    Normalize both stored value and provided code to handle:
    - surrounding whitespace
    - full-width characters (NFKC normalization)
    - case-insensitive comparison
    """
    try:
        import unicodedata
    except Exception:
        unicodedata = None

    def _norm(s: str) -> str:
        if s is None:
            return ''
        s2 = str(s)
        # normalize full-width -> ascii where possible
        if unicodedata:
            try:
                s2 = unicodedata.normalize('NFKC', s2)
            except Exception:
                pass
        # strip surrounding whitespace and compare case-insensitively
        return s2.strip().lower()

    real = _norm(cache.get(f"captcha:{key}") or '')
    if not real or real != _norm(code or ''):
        return False
    try:
        cache.delete(f"captcha:{key}")
    except Exception:
        pass
    return True
