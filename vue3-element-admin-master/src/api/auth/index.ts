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
};
