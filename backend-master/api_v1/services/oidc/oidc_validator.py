"""自定义 OIDC 验证器（oidc_validator）。

重写 get_additional_claims 以向 NC user_oidc 插件提供以下自定义声明：
    name          → 显示名称（nickname）
    email         → 邮箱
    phone_number  → 手机号
    groups        → 用户所属 NC 群组 code 列表（部门群组 + 额外群组）
    is_admin      → 是否为公司管理员（NC admin flag）

声明范围映射（oidc_claim_scope）：
    name / phone_number / groups / is_admin  → profile 范围
    email                                    → email 范围（父类已定义）
"""
import logging

from oauth2_provider.oauth2_validators import OAuth2Validator

from api_v1.models.nc.nc_group import NcGroup, NcGroupType
from api_v1.models.system.user_profile import AdminLevel

logger = logging.getLogger(__name__)


class CustomOAuth2Validator(OAuth2Validator):
    """自定义 OAuth2 / OIDC 验证器。

    在父类基础上扩展 oidc_claim_scope（声明→范围映射）并重写
    get_additional_claims 注入业务级声明，供 NC user_oidc 插件消费。
    """

    # 扩展父类的 claim→scope 映射，追加自定义声明
    oidc_claim_scope = {
        **OAuth2Validator.oidc_claim_scope,
        "preferred_username": "profile",
        "groups": "profile",
        "is_admin": "profile",
        "mobile": "phone",
    }

    def get_additional_claims(self, request) -> dict:
        """构建并返回自定义 OIDC 额外声明字典。

        Args:
            request: OAuthLib 请求对象，request.user 为已认证的 Django User 实例。

        Returns:
            dict: 包含 preferred_username/name/email/phone_number/groups/is_admin 的声明字典。
                  任何字段查询失败时静默忽略，保证不影响 OIDC 正常流程。

        说明：
            - sub 字段由父类自动生成（user.id 字符串化），符合 OIDC "稳定唯一标识不可变" 规范。
            - preferred_username 输出 Django username，与 NcSyncService 创建 NC 用户时使用的 UID 一致。
              NC user_oidc 端 User ID mapping 必须配置为 preferred_username，才能正确匹配现有 NC 用户。
        """
        user = request.user
        claims: dict = {}

        # preferred_username：Django username，与 NC 用户 UID 一致，供 NC 做用户映射
        claims["preferred_username"] = user.username

        try:
            profile = getattr(user, "profile", None)
            if not profile:
                return claims

            # name：优先 nickname，回退到 username
            claims["name"] = profile.nickname or user.username

            # email
            if user.email:
                claims["email"] = user.email

            # phone_number（字段名 mobile，映射为 OIDC 标准 phone_number）
            if profile.mobile:
                claims["phone_number"] = profile.mobile

            # groups：部门绑定的 NC 群组 + 额外分配的 NC 群组
            groups: list[str] = []
            if profile.dept_id:
                dept_nc = NcGroup.objects.filter(
                    dept_id=profile.dept_id,
                    group_type=NcGroupType.DEPT,
                ).values_list("code", flat=True).first()
                if dept_nc:
                    groups.append(dept_nc)
            for code in profile.extra_nc_groups.values_list("code", flat=True):
                if code not in groups:
                    groups.append(code)
            claims["groups"] = groups

            # is_admin：COMPANY_ADMIN 对应 NC admin flag
            claims["is_admin"] = profile.admin_level == AdminLevel.COMPANY_ADMIN

        except Exception as exc:
            logger.warning("[CustomOAuth2Validator][get_additional_claims] 声明构建异常: %s", exc, exc_info=True)

        return claims
