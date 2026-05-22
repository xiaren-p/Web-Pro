/**
 * 认证 API：登录、登出、刷新 token、图形验证码。
 */
import request from "@/utils/request";

export interface LoginFormData {
  username: string;
  password: string;
  captchaKey?: string;
  captchaCode?: string;
  rememberMe?: boolean;
}

const AUTH_BASE_URL = "/auth";

export const AuthAPI = {
  login(data: LoginFormData) {
    return request<
      any,
      { accessToken: string; refreshToken: string; tokenType?: string; expiresIn: number }
    >({ url: `${AUTH_BASE_URL}/login`, method: "post", data });
  },
  logout() {
    return request({ url: `${AUTH_BASE_URL}/logout`, method: "delete" });
  },
  refreshToken(refreshToken: string) {
    return request<
      any,
      { accessToken: string; refreshToken?: string; tokenType?: string; expiresIn: number }
    >({
      url: `${AUTH_BASE_URL}/refresh-token`,
      method: "post",
      data: { refreshToken },
      headers: { Authorization: "no-auth" },
      withCredentials: false,
    });
  },
  getCaptcha() {
    return request<any, { img: string; uuid: string }>({
      url: `${AUTH_BASE_URL}/captcha`,
      method: "get",
      headers: { Authorization: "no-auth" },
    });
  },
  /**
   * 用当前 Bearer JWT 换取 Django Session Cookie。
   *
   * 在登录成功后静默调用，使后端 /o/authorize/ 认可当前用户已登录，
   * 从而实现「打开 Nextcloud 地址直接完成 SSO，无需二次输入密码」。
   *
   * @returns {Promise} 成功时后端 Set-Cookie 写入 sessionid，前端无需处理返回值。
   */
  ssoSession() {
    return request<any, { detail: string }>({
      url: `${AUTH_BASE_URL}/sso-session`,
      method: "post",
    }).catch(() => {
      // SSO Session 建立失败不影响主系统正常使用，静默忽略
    });
  },
};
