"""Nextcloud REST API 客户端（nc_api_client）。

封装所有与 NC OCS Provisioning API / Group Folders API 的 HTTP 通信。
调用方无需关心 URL 拼接、认证头、SSL 配置，只需调用语义方法。

NC OCS API 基础路径：
    /ocs/v1.php/cloud/users/...
    /ocs/v2.php/apps/groupfolders/folders/...

所有请求均带 OCS-APIRequest: true 头，使 NC 以 JSON 返回响应。
"""
import logging

import requests

from django.conf import settings

logger = logging.getLogger(__name__)

# OCS API 成功状态码
# v1 路径（/ocs/v1.php/）：100=OK，102=已存在
# v2 路径（/ocs/v2.php/）：200=OK（Group Folders 等应用使用 v2）
_OCS_OK_CODES = {100, 102, 200}


class NcApiClient:
    """Nextcloud REST API 客户端。

    Args:
        server_url (str): NC 服务器根地址，如 https://192.168.0.27:40069
        admin_user (str): 具有管理员权限的 NC 用户名
        admin_password (str): 对应明文密码

    Raises:
        RuntimeError: 当 NC 返回非预期状态时抛出，携带完整错误信息。

    Examples:
        >>> client = NcApiClient.from_settings()
        >>> client.create_user("zhangsan", "Abc@12345", "张三", "test@example.com")
    """

    def __init__(self, server_url: str, admin_user: str, admin_password: str) -> None:
        """初始化客户端，构建 Session 并设置通用头。"""
        self._base = server_url.rstrip("/")
        self._session = requests.Session()
        self._session.auth = (admin_user, admin_password)
        self._session.headers.update({
            "OCS-APIRequest": "true",
            "Accept": "application/json",
        })
        self._verify: bool = getattr(settings, "NC_VERIFY_SSL", True)

    @classmethod
    def from_settings(cls) -> "NcApiClient":
        """从 Django settings / .env 读取配置创建实例。

        Returns:
            NcApiClient: 已完成初始化的客户端实例。
        """
        from api_v1.models.system.config import Config
        server_url = cls._read_config("NC_BASE_URL")
        admin_user = cls._read_config("NC_ADMIN_USER")
        admin_password = cls._read_config_plaintext("NC_ADMIN_APP_PWD")
        return cls(server_url, admin_user, admin_password)

    @staticmethod
    def _read_config(key: str) -> str:
        """从 Config 表读取文本型配置值。

        Args:
            key (str): Config 表中的 config_key。

        Returns:
            str: 配置值（去除首尾空白）。

        Raises:
            RuntimeError: 配置项不存在或值为空时抛出。
        """
        from api_v1.models.system.config import Config
        obj = Config.objects.filter(key=key).first()
        if not obj or not obj.value:
            raise RuntimeError(f"[NcApiClient] Config 表中缺少必要配置项: {key}")
        return obj.value.strip()

    @staticmethod
    def _read_config_plaintext(key: str) -> str:
        """从 Config 表读取 PASSWORD 型配置（自动解密）。

        Args:
            key (str): Config 表中的 config_key。

        Returns:
            str: 解密后的明文字符串。

        Raises:
            RuntimeError: 配置项不存在或解密失败时抛出。
        """
        from api_v1.models.system.config import Config
        obj = Config.objects.filter(key=key).first()
        if not obj:
            raise RuntimeError(f"[NcApiClient] Config 表中缺少必要配置项: {key}")
        value = obj.get_plaintext_value()
        if not value:
            raise RuntimeError(f"[NcApiClient] Config 项 {key} 解密后为空，请检查 Fernet 密钥或配置值。")
        return value

    def _post(self, path: str, data: dict) -> dict:
        """发送 POST 请求并校验 OCS 响应状态码。

        Args:
            path (str): API 路径（相对于 server_url）。
            data (dict): 表单/JSON 请求体。

        Returns:
            dict: NC 返回的 ocs.data 字段内容（可能为空字典）。

        Raises:
            RuntimeError: HTTP 错误或 OCS statuscode 不在成功集合时抛出。
        """
        url = f"{self._base}{path}"
        try:
            resp = self._session.post(url, data=data, verify=self._verify, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"[NcApiClient] POST {path} 网络错误: {exc}") from exc
        return self._parse_ocs(resp, path)

    def _put(self, path: str, data: dict | None = None) -> dict:
        """发送 PUT 请求。"""
        url = f"{self._base}{path}"
        try:
            resp = self._session.put(url, data=data or {}, verify=self._verify, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"[NcApiClient] PUT {path} 网络错误: {exc}") from exc
        return self._parse_ocs(resp, path)

    def _delete(self, path: str) -> dict:
        """发送 DELETE 请求。"""
        url = f"{self._base}{path}"
        try:
            resp = self._session.delete(url, verify=self._verify, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"[NcApiClient] DELETE {path} 网络错误: {exc}") from exc
        return self._parse_ocs(resp, path)

    def _get(self, path: str) -> dict:
        """发送 GET 请求。"""
        url = f"{self._base}{path}"
        try:
            resp = self._session.get(url, verify=self._verify, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"[NcApiClient] GET {path} 网络错误: {exc}") from exc
        return self._parse_ocs(resp, path)

    @staticmethod
    def _parse_ocs(resp: requests.Response, path: str) -> dict:
        """解析 OCS 响应，校验 statuscode，返回 data 字典。

        Args:
            resp (requests.Response): 原始 HTTP 响应。
            path (str): 请求路径，用于日志。

        Returns:
            dict: ocs.data 内容。

        Raises:
            RuntimeError: OCS statuscode 不在 100/102 时抛出。
        """
        try:
            body = resp.json()
        except Exception as exc:
            raise RuntimeError(f"[NcApiClient] {path} 响应无法解析为 JSON: {resp.text[:200]}") from exc
        ocs = body.get("ocs", {})
        meta = ocs.get("meta", {})
        status_code = int(meta.get("statuscode", 0))
        if status_code not in _OCS_OK_CODES:
            msg = meta.get("message", "")
            raise RuntimeError(
                f"[NcApiClient] {path} OCS 返回错误 {status_code}: {msg}"
            )
        return ocs.get("data", {})

    # ------------------------------------------------------------------ #
    #  用户操作                                                            #
    # ------------------------------------------------------------------ #

    def create_user(
        self,
        username: str,
        password: str,
        display_name: str = "",
        email: str = "",
    ) -> None:
        """在 NC 中创建新用户。

        Args:
            username (str): 用户名（与 Django username 对齐）。
            password (str): 初始密码明文。
            display_name (str): 显示名称，可选。
            email (str): 邮箱，可选。
        """
        logger.info("[NcApiClient][create_user] username=%s", username)
        self._post("/ocs/v1.php/cloud/users", {
            "userid": username,
            "password": password,
            "displayName": display_name,
            "email": email,
        })

    def update_user_email(self, username: str, email: str) -> None:
        """更新 NC 用户邮箱。

        Args:
            username (str): 目标用户名。
            email (str): 新邮箱地址。
        """
        logger.info("[NcApiClient][update_user_email] username=%s", username)
        self._put(f"/ocs/v1.php/cloud/users/{username}", {"key": "email", "value": email})

    def update_user_display_name(self, username: str, display_name: str) -> None:
        """更新 NC 用户显示名称。

        Args:
            username (str): 目标用户名。
            display_name (str): 新显示名称。
        """
        logger.info("[NcApiClient][update_user_display_name] username=%s", username)
        self._put(f"/ocs/v1.php/cloud/users/{username}", {"key": "displayname", "value": display_name})

    def disable_user(self, username: str) -> None:
        """禁用 NC 用户（账号保留，仅禁止登录）。

        Args:
            username (str): 目标用户名。
        """
        logger.info("[NcApiClient][disable_user] username=%s", username)
        self._put(f"/ocs/v1.php/cloud/users/{username}/disable")

    def enable_user(self, username: str) -> None:
        """重新启用 NC 用户。

        Args:
            username (str): 目标用户名。
        """
        logger.info("[NcApiClient][enable_user] username=%s", username)
        self._put(f"/ocs/v1.php/cloud/users/{username}/enable")

    def set_admin(self, username: str) -> None:
        """将 NC 用户加入 admin 群组（使其成为 NC 管理员）。

        Args:
            username (str): 目标用户名。
        """
        logger.info("[NcApiClient][set_admin] username=%s", username)
        self._post(f"/ocs/v1.php/cloud/users/{username}/groups", {"groupid": "admin"})

    def revoke_admin(self, username: str) -> None:
        """将 NC 用户移出 admin 群组。

        Args:
            username (str): 目标用户名。
        """
        logger.info("[NcApiClient][revoke_admin] username=%s", username)
        self._delete(f"/ocs/v1.php/cloud/users/{username}/groups?groupid=admin")

    def get_user(self, username: str) -> dict:
        """获取 NC 用户信息。

        Args:
            username (str): 目标用户名。

        Returns:
            dict: NC 返回的用户信息字典（OCS data 部分）。
        """
        return self._get(f"/ocs/v1.php/cloud/users/{username}")

    def user_exists(self, username: str) -> bool:
        """判断 NC 用户是否存在。

        Args:
            username (str): 目标用户名。

        Returns:
            bool: 存在返回 True，否则 False。
        """
        try:
            self._get(f"/ocs/v1.php/cloud/users/{username}")
            return True
        except RuntimeError:
            return False

    def group_exists(self, group_id: str) -> bool:
        """判断 NC 群组是否存在。

        Args:
            group_id (str): 群组 ID（NcGroup.code）。

        Returns:
            bool: 存在返回 True，否则 False。
        """
        try:
            self._get(f"/ocs/v1.php/cloud/groups/{group_id}")
            return True
        except RuntimeError:
            return False

    # ------------------------------------------------------------------ #
    #  群组操作                                                            #
    # ------------------------------------------------------------------ #

    def create_group(self, group_id: str, display_name: str = "") -> None:
        """在 NC 中创建群组。

        Args:
            group_id (str): 群组 ID（NcGroup.code）。
            display_name (str): 群组显示名称，可选。
        """
        logger.info("[NcApiClient][create_group] group_id=%s", group_id)
        self._post("/ocs/v1.php/cloud/groups", {
            "groupid": group_id,
            "displayname": display_name or group_id,
        })

    def delete_group(self, group_id: str) -> None:
        """在 NC 中删除群组（不删除组内用户）。

        Args:
            group_id (str): 群组 ID（NcGroup.code）。
        """
        logger.info("[NcApiClient][delete_group] group_id=%s", group_id)
        self._delete(f"/ocs/v1.php/cloud/groups/{group_id}")

    def add_user_to_group(self, username: str, group_id: str) -> None:
        """将用户加入 NC 群组。

        Args:
            username (str): 用户名。
            group_id (str): 群组 ID。
        """
        logger.info("[NcApiClient][add_user_to_group] username=%s group=%s", username, group_id)
        self._post(f"/ocs/v1.php/cloud/users/{username}/groups", {"groupid": group_id})

    def remove_user_from_group(self, username: str, group_id: str) -> None:
        """将用户移出 NC 群组。

        Args:
            username (str): 用户名。
            group_id (str): 群组 ID。
        """
        logger.info("[NcApiClient][remove_user_from_group] username=%s group=%s", username, group_id)
        self._delete(f"/ocs/v1.php/cloud/users/{username}/groups?groupid={group_id}")

    # ------------------------------------------------------------------ #
    #  Group Folders 操作                                                  #
    # ------------------------------------------------------------------ #

    def create_group_folder(self, mount_point: str) -> int:
        """创建 Group Folder。

        Args:
            mount_point (str): 挂载点路径，如 "/部门文档/技术部"。

        Returns:
            int: NC 分配的 Group Folder ID（后续权限授权需要此 ID）。
        """
        logger.info("[NcApiClient][create_group_folder] mount_point=%s", mount_point)
        data = self._post("/ocs/v2.php/apps/groupfolders/folders", {"mountpoint": mount_point})
        folder_id = data.get("id")
        if folder_id is None:
            raise RuntimeError(f"[NcApiClient] create_group_folder 返回数据中缺少 id: {data}")
        return int(folder_id)

    def grant_group_folder(self, folder_id: int, group_id: str, permissions: int) -> None:
        """为 Group Folder 授权指定群组。

        Args:
            folder_id (int): Group Folder ID。
            group_id (str): NC 群组 ID。
            permissions (int): 权限位（READ=1 WRITE=2 CREATE=4 DELETE=8 SHARE=16）。
        """
        logger.info(
            "[NcApiClient][grant_group_folder] folder_id=%s group=%s perms=%s",
            folder_id, group_id, permissions,
        )
        # 先确保群组已加入该 Folder
        self._post(f"/ocs/v2.php/apps/groupfolders/folders/{folder_id}/groups", {"group": group_id})
        # 再设置权限
        self._post(
            f"/ocs/v2.php/apps/groupfolders/folders/{folder_id}/groups/{group_id}",
            {"permissions": permissions},
        )
