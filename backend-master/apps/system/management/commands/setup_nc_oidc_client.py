"""setup_nc_oidc_client：为 Nextcloud user_oidc 注册 OAuth Client。

一次性创建 / 覆写一条 OAuth2 Application 记录，用于 NC user_oidc 应用接入。
执行后打印出 NC 后台需要填入的所有字段，部署时复制即可。

用法：
    python manage.py setup_nc_oidc_client --nc-host https://nc.example.com
    python manage.py setup_nc_oidc_client --nc-host https://nc.example.com --reset-secret
"""
import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)
User = get_user_model()

# 固定 Application 名称，便于幂等查找
APP_NAME = "Nextcloud SSO"


class Command(BaseCommand):
    """注册 / 更新 NC SSO 用 OAuth Client。

    幂等：以 name='Nextcloud SSO' 作为唯一键，已存在则更新 redirect_uris；
    --reset-secret 会重新生成 client_secret（NC 端需要同步更新）。
    """

    help = "为 Nextcloud user_oidc 注册或更新 OAuth Client（幂等）。"

    def add_arguments(self, parser) -> None:
        """注册命令行参数。

        Args:
            parser: argparse.ArgumentParser 实例。
        """
        parser.add_argument(
            "--nc-host",
            required=True,
            help="Nextcloud 站点根 URL，例如 https://nc.example.com（末尾不带斜杠）。",
        )
        parser.add_argument(
            "--reset-secret",
            action="store_true",
            default=False,
            help="重新生成 client_secret（NC 端需同步替换）。",
        )

    def handle(self, *args, **options) -> None:
        """命令入口：注册 / 更新 OAuth Client 并打印 NC 端配置。

        Args:
            *args: 不使用。
            **options (dict): 命令行选项字典，包含 nc_host / reset_secret。

        Raises:
            CommandError: oauth2_provider 未安装、无超级用户或私钥未生成时抛出。
        """
        try:
            from oauth2_provider.models import Application
        except ImportError as exc:
            raise CommandError(
                f"未安装 django-oauth-toolkit，请先 pip install django-oauth-toolkit: {exc}"
            ) from exc

        nc_host: str = options["nc_host"].rstrip("/")
        reset_secret: bool = options["reset_secret"]
        # NC 根据是否启用「漂亮 URL」，callback 有两种格式：
        # 1. 启用漂亮 URL：/apps/user_oidc/code
        # 2. 未启用（默认）：/index.php/apps/user_oidc/code
        # Application.redirect_uris 支持换行分隔，同时注册两种避免不匹配。
        redirect_uri: str = (
            f"{nc_host}/apps/user_oidc/code"
            f"\n{nc_host}/index.php/apps/user_oidc/code"
        )

        # 必须有超级用户作为 Application.user 归属
        owner = User.objects.filter(is_superuser=True).order_by("id").first()
        if not owner:
            raise CommandError("未找到超级用户，请先创建一个 superuser 再执行此命令。")

        # django-oauth-toolkit 3.x 默认 CLIENT_SECRET_HASHED=True，save() 后
        # app.client_secret 会变成不可逆的哈希串，因此必须在 save 之前生成明文并缓存。
        from oauth2_provider.generators import generate_client_secret

        app = Application.objects.filter(name=APP_NAME).first()
        created = False
        plain_secret: str | None = None
        if app is None:
            # 首次创建：手工生成明文 secret 后写入，save 后哈希；本地保留明文用于打印
            plain_secret = generate_client_secret()
            app = Application(
                name=APP_NAME,
                user=owner,
                client_type=Application.CLIENT_CONFIDENTIAL,
                authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                redirect_uris=redirect_uri,
                algorithm=Application.RS256_ALGORITHM,
                skip_authorization=True,
            )
            app.client_secret = plain_secret
            app.save()
            created = True
            logger.info(
                "[setup_nc_oidc_client] 创建 OAuth Application client_id=%s", app.client_id,
            )
        else:
            # 已存在：仅更新 redirect_uri（必要时刷新 secret）
            app.redirect_uris = redirect_uri
            app.algorithm = Application.RS256_ALGORITHM
            app.skip_authorization = True
            if reset_secret:
                plain_secret = generate_client_secret()
                app.client_secret = plain_secret
                logger.warning(
                    "[setup_nc_oidc_client] 已重置 client_secret，NC 端必须同步更新。",
                )
            app.save()

        # 打印 NC 端需要填的配置（client_secret 仅在创建 / reset 时有明文可显示）
        self.stdout.write(self.style.SUCCESS(
            f"\n=== Nextcloud user_oidc 配置（{'新建' if created else '已更新'}）===\n"
        ))
        self.stdout.write(f"Identifier        : Django")
        self.stdout.write(f"Client ID         : {app.client_id}")
        if plain_secret is not None:
            self.stdout.write(f"Client secret     : {plain_secret}")
        else:
            self.stdout.write(self.style.WARNING(
                "Client secret     : (已哈希存储，无法回显，请加 --reset-secret 重新生成)"
            ))
        self.stdout.write(
            "Discovery endpoint: <DJANGO_HOST>/o/.well-known/openid-configuration"
        )
        self.stdout.write(f"Scope             : openid profile email")
        self.stdout.write(f"Redirect URI      : {redirect_uri}")
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("--- Attribute Mapping ---"))
        self.stdout.write("User ID mapping   : preferred_username")
        self.stdout.write("Display name      : name")
        self.stdout.write("Email             : email")
        self.stdout.write("Quota             : (留空)")
        self.stdout.write("Groups            : groups")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING(
            "重要：User ID mapping 必须填 preferred_username（不能用 sub），"
            "才能与 NcSyncService 创建的 NC 用户 username 对齐。"
        ))
        if not reset_secret and not created:
            self.stdout.write(self.style.NOTICE(
                "\n提示：若 NC 端 client_secret 已遗失，使用 --reset-secret 重新生成。"
            ))
