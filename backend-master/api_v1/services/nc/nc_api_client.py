"""Nextcloud REST API 客户端（nc_api_client）。

封装所有与 NC OCS Provisioning API / Group Folders API 的 HTTP 通信。
调用方无需关心 URL 拼接、认证头、SSL 配置，只需调用语义方法。

NC 路由体系说明：
  OCS 路由  ：URL 以 /ocs/v1.php/ 或 /ocs/v2.php/ 开头，由 OCS Router 处理。
              使用 _post() 方法，响应为 OCS 格式 {ocs: {meta, data}}。
  App 路由  ：URL 以 /apps/{appid}/ 开头，由 App Router 处理（如 Group Folders）。
              使用 _post_app() 方法，响应为 Controller DataResponse 的原始 JSON。

所有请求均带 OCS-APIRequest: true 头：
  - 对 OCS 路由：声明客户端期望 OCS JSON 格式响应。
  - 对 App 路由：绕过 NC SecurityMiddleware 的 CSRF requesttoken 校验。
  两者的路由选择均由 URL 前缀决定，与此头无关。
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
        self._admin_user = admin_user
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

    def _post_app(self, path: str, data: dict) -> dict:
        """发送 POST 到普通 App 路由（/apps/...），携带 OCS-APIRequest: true 绕过 CSRF。

        NC 的路由决策完全基于 URL 前缀：
        - /ocs/v1.php/、/ocs/v2.php/ → OCS Router
        - /apps/{appid}/...          → 普通 App Router（本方法使用）

        OCS-APIRequest: true 头使 NC 以 OCS 格式返回响应（包含 ocs.meta / ocs.data），
        同时绕过 SecurityMiddleware 的 CSRF requesttoken 校验，与路由选择无关。

        Args:
            path (str): API 路径（相对于 server_url），如 /apps/groupfolders/folders。
            data (dict): 表单请求体。

        Returns:
            dict: ocs.data 字段内容（与 _post() 返回格式一致）。

        Raises:
            RuntimeError: HTTP 错误、OCS statuscode 不合法或响应非 JSON 时抛出。
        """
        url = f"{self._base}{path}"
        try:
            resp = self._session.post(
                url,
                data=data,
                verify=self._verify,
                timeout=15,
            )
            logger.debug(
                "[NcApiClient][_post_app] %s -> HTTP %s | body=%s",
                path,
                resp.status_code,
                resp.text[:300],
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"[NcApiClient] POST {path} 网络错误: {exc}") from exc
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

    def list_group_folders(self) -> dict[int, dict]:
        """列出 NC 中所有已存在的 Group Folders。

        Returns:
            dict[int, dict]: 以 folder_id（int）为键、folder 信息字典为值的映射。
                             folder 信息包含 mount_point、quota、groups 等字段。

        Raises:
            RuntimeError: HTTP 错误或 OCS 响应异常时抛出。
        """
        logger.info("[NcApiClient][list_group_folders] 查询所有 Group Folders")
        raw = self._get("/apps/groupfolders/folders")
        # NC 返回 ocs.data 为 {"1": {folder_info}, "2": {...}} 格式
        return {int(k): v for k, v in raw.items()}

    def create_group_folder(self, mount_point: str) -> int:
        """创建 Group Folder，若同名挂载点已存在则直接返回已有 ID（幂等）。

        Args:
            mount_point (str): 挂载点路径，如 "/部门文档/技术部"。

        Returns:
            int: NC 分配的 Group Folder ID（后续权限授权需要此 ID）。

        Raises:
            RuntimeError: NC 响应异常或返回数据缺少 id 时抛出。
        """
        logger.info("[NcApiClient][create_group_folder] mount_point=%s", mount_point)
        # 先检查是否已存在同名挂载点，避免重复创建（任务重试时保证幂等性）
        existing = self.list_group_folders()
        for folder_id, info in existing.items():
            if info.get("mount_point") == mount_point:
                logger.info(
                    "[NcApiClient][create_group_folder] 已存在，复用 folder_id=%s mount_point=%s",
                    folder_id,
                    mount_point,
                )
                return folder_id
        data = self._post_app("/apps/groupfolders/folders", {"mountpoint": mount_point})
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
        self._post_app(f"/apps/groupfolders/folders/{folder_id}/groups", {"group": group_id})
        # 再设置权限
        self._post_app(
            f"/apps/groupfolders/folders/{folder_id}/groups/{group_id}",
            {"permissions": permissions},
        )

    # ------------------------------------------------------------------ #
    #  Group Folders ACL 操作                                           #
    # ------------------------------------------------------------------ #

    def _proppatch(self, dav_path: str, xml_body: str) -> None:
        """**内部**发送 WebDAV PROPPATCH 请求（用于设置 ACL 属性）。

        PROPPATCH 使用 DAV XML 格式，不走 OCS 路由，成功响应为 207 Multi-Status。

        Args:
            dav_path (str): WebDAV 路径（相对于 server_url），
                            如 /remote.php/dav/files/{user}/{mount}/{sub_path}。
            xml_body (str): 完整的 DAV XML 请求体字符串。

        Raises:
            RuntimeError: HTTP 请求失败或状态码非 207/200 时抛出。
        """
        url = f"{self._base}{dav_path}"
        try:
            resp = self._session.request(
                "PROPPATCH",
                url,
                data=xml_body.encode("utf-8"),
                headers={"Content-Type": "application/xml; charset=utf-8"},
                verify=self._verify,
                timeout=30,
            )
            logger.debug(
                "[NcApiClient][_proppatch] %s -> HTTP %s",
                dav_path, resp.status_code,
            )
            if resp.status_code not in (200, 207):
                raise RuntimeError(
                    f"[NcApiClient] PROPPATCH {dav_path} 返回非预期状态码 "
                    f"{resp.status_code}: {resp.text[:300]}"
                )
        except requests.RequestException as exc:
            raise RuntimeError(f"[NcApiClient] PROPPATCH {dav_path} 网络错误: {exc}") from exc

    def enable_folder_acl(self, folder_id: int) -> None:
        """为 Group Folder 开启 ACL 高级权限模式（幂等，可重复调用）。

        开启后才能使用 WebDAV PROPPATCH 为各子路径设置细粒度 ACL 规则。

        Args:
            folder_id (int): NC Group Folder ID。

        Raises:
            RuntimeError: NC 响应异常时抛出。
        """
        logger.info("[NcApiClient][enable_folder_acl] folder_id=%s", folder_id)
        self._put(f"/apps/groupfolders/folders/{folder_id}/acl", {"acl": 1})

    def set_path_acl(
        self,
        nc_path: str,
        group_id: str,
        mask: int,
        permissions: int,
    ) -> None:
        """**为 Group Folder 内子目录设置群组 ACL 规则**（WebDAV PROPPATCH）。

        ACL 规则视该路径的 Group Folder GRANT 基线权限，实现子目录级别的细粒度控制。

        Args:
            nc_path (str): 从 Group Folder 挂载点开始的完整子路径，
                           如 "技术部/机密文档" 或 "技术部"；首尾斜杠自动忽略。
            group_id (str): NC 群组 ID（NcGroup.code）。
            mask (int): ACL 掩码（全位生效传 31；传 0 表示展透/移除该条规则的效果）。
            permissions (int): 实际授予的权限位（READ=1 WRITE=2 CREATE=4 DELETE=8 SHARE=16）。

        Raises:
            RuntimeError: 网络错误或 PROPPATCH 失败时抛出。
        """
        clean_path = nc_path.strip("/")
        dav_path = f"/remote.php/dav/files/{self._admin_user}/{clean_path}"
        xml_body = (
            '<?xml version="1.0"?>'
            '<d:propertyupdate xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">'
            "<d:set><d:prop><oc:acl-list>"
            "<oc:acl>"
            "<oc:acl-mapping-type>group</oc:acl-mapping-type>"
            f"<oc:acl-mapping-id>{group_id}</oc:acl-mapping-id>"
            f"<oc:acl-mask>{mask}</oc:acl-mask>"
            f"<oc:acl-permissions>{permissions}</oc:acl-permissions>"
            "</oc:acl>"
            "</oc:acl-list></d:prop></d:set>"
            "</d:propertyupdate>"
        )
        logger.info(
            "[NcApiClient][set_path_acl] path=%s group=%s mask=%s perms=%s",
            dav_path, group_id, mask, permissions,
        )
        self._proppatch(dav_path, xml_body)

    # ------------------------------------------------------------------ #
    #  WebDAV 目录浏览与创建                                               #
    # ------------------------------------------------------------------ #

    def list_dav_folder(self, dav_path: str) -> list[dict]:
        """通过 WebDAV PROPFIND（Depth: 1）列出指定目录的直属子目录。

        仅返回 resourcetype 为 collection（目录）的条目，文件被过滤掉；
        同时过滤掉首条 response（即请求路径自身）。

        Args:
            dav_path (str): 相对于 NC server 根的 WebDAV 路径，
                            如 /remote.php/dav/files/admin/技术部/ 。

        Returns:
            list[dict]: 子目录列表，每项含 {"name": str, "href": str}。

        Raises:
            RuntimeError: 网络错误或非 207 响应时抛出。
        """
        import xml.etree.ElementTree as ET
        from urllib.parse import unquote

        url = f"{self._base}{dav_path}"
        xml_body = (
            '<?xml version="1.0"?>'
            '<d:propfind xmlns:d="DAV:">'
            "<d:prop><d:resourcetype/><d:displayname/></d:prop>"
            "</d:propfind>"
        )
        logger.info("[NcApiClient][list_dav_folder] %s", dav_path)
        try:
            resp = self._session.request(
                "PROPFIND",
                url,
                data=xml_body.encode("utf-8"),
                headers={
                    "Content-Type": "application/xml; charset=utf-8",
                    "Depth": "1",
                },
                verify=self._verify,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise RuntimeError(
                f"[NcApiClient] PROPFIND {dav_path} 网络错误: {exc}"
            ) from exc
        if resp.status_code != 207:
            raise RuntimeError(
                f"[NcApiClient] PROPFIND {dav_path} 返回状态码 "
                f"{resp.status_code}: {resp.text[:200]}"
            )
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as exc:
            raise RuntimeError(
                f"[NcApiClient] PROPFIND 响应 XML 解析失败: {exc}"
            ) from exc

        ns = {"d": "DAV:"}
        entries: list[dict] = []
        responses = root.findall("d:response", ns)

        for response in responses[1:]:  # 跳过首条（当前目录自身）
            href_el = response.find("d:href", ns)
            if href_el is None:
                continue
            href = href_el.text or ""
            propstat = response.find("d:propstat", ns)
            if propstat is None:
                continue
            prop = propstat.find("d:prop", ns)
            if prop is None:
                continue
            resourcetype = prop.find("d:resourcetype", ns)
            is_collection = (
                resourcetype is not None
                and resourcetype.find("d:collection", ns) is not None
            )
            if not is_collection:
                continue
            displayname_el = prop.find("d:displayname", ns)
            if displayname_el is not None and displayname_el.text:
                name = displayname_el.text
            else:
                # 从 href 推导名称（URL 解码后取最后一段）
                name = unquote(href.rstrip("/").split("/")[-1])
            entries.append({"name": name, "href": href})

        return entries

    def create_dav_folder(self, dav_path: str) -> None:
        """通过 WebDAV MKCOL 创建目录（幂等：已存在返回 405 时静默通过）。

        Args:
            dav_path (str): 相对于 NC server 根的新目录 WebDAV 路径，
                            如 /remote.php/dav/files/admin/技术部/新文件夹 。

        Raises:
            RuntimeError: 网络错误或非 201/405 响应时抛出。
        """
        url = f"{self._base}{dav_path}"
        logger.info("[NcApiClient][create_dav_folder] %s", dav_path)
        try:
            resp = self._session.request(
                "MKCOL", url, verify=self._verify, timeout=15
            )
        except requests.RequestException as exc:
            raise RuntimeError(
                f"[NcApiClient] MKCOL {dav_path} 网络错误: {exc}"
            ) from exc
        if resp.status_code == 405:
            logger.info(
                "[NcApiClient][create_dav_folder] 目录已存在，幂等跳过: %s",
                dav_path,
            )
            return
        if resp.status_code != 201:
            raise RuntimeError(
                f"[NcApiClient] MKCOL {dav_path} 返回状态码 "
                f"{resp.status_code}: {resp.text[:200]}"
            )
