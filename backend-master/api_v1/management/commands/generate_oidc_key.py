"""generate_oidc_key：生成 OIDC RSA 私钥管理命令。

生成一枚 2048 位 RSA 私钥，写入 backend_master/oidc_private.pem。
该文件已被 .gitignore 排除，不会提交到版本库。

用法：
    python manage.py generate_oidc_key
    python manage.py generate_oidc_key --bits 4096   # 使用更长的密钥
    python manage.py generate_oidc_key --force        # 覆盖已有密钥
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """生成 OIDC RSA 私钥并保存到 backend_master/oidc_private.pem。

    若密钥文件已存在则拒绝覆盖（使用 --force 强制覆盖）。
    """

    help = "生成 OIDC RSA 私钥文件（backend_master/oidc_private.pem）。"

    def add_arguments(self, parser) -> None:
        """注册命令行参数。

        Args:
            parser: argparse.ArgumentParser 实例。
        """
        parser.add_argument(
            "--bits",
            type=int,
            default=2048,
            help="RSA 密钥位数，默认 2048，推荐生产使用 4096。",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="若密钥文件已存在则强制覆盖。",
        )

    def handle(self, *args, **options) -> None:
        """生成 RSA 私钥并写入文件。

        Args:
            *args: 不使用。
            **options (dict): 命令行选项，包含 bits / force。

        Raises:
            CommandError: 密钥文件已存在且未指定 --force 时抛出。
        """
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
        except ImportError as exc:
            raise CommandError("缺少 cryptography 库，请先安装: pip install cryptography") from exc

        from django.conf import settings

        bits: int = options["bits"]
        force: bool = options["force"]

        key_path = Path(settings.BASE_DIR) / "backend_master" / "oidc_private.pem"

        if key_path.exists() and not force:
            raise CommandError(
                f"密钥文件已存在: {key_path}\n"
                "若需要重新生成，请使用 --force 参数（注意：原有 OIDC 应用的 token 将全部失效）。"
            )

        self.stdout.write(f"正在生成 {bits} 位 RSA 私钥...")

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=bits,
        )
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(pem)

        # 设置文件权限为仅 owner 可读写（Unix 环境）
        try:
            import stat
            key_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS(
            f"RSA 私钥已生成: {key_path}\n"
            "请重启 Django 使 OIDC_ENABLED=True 生效，并在 NC user_oidc 插件中配置：\n"
            f"  OIDC Discovery URL: <backend_url>/o/.well-known/openid-configuration"
        ))

        # 提示将文件加入 .gitignore
        gitignore_path = Path(settings.BASE_DIR) / ".gitignore"
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding="utf-8")
            if "oidc_private.pem" not in content:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠ 请将 backend_master/oidc_private.pem 加入 .gitignore 以防止私钥泄露。"
                    )
                )
