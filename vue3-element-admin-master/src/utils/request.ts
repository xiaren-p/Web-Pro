import axios, { type InternalAxiosRequestConfig, type AxiosResponse } from "axios";
import qs from "qs";
import { ApiCodeEnum } from "@/enums/api/code-enum";
import { AuthStorage, redirectToLogin } from "@/utils/auth";
import { useTokenRefresh } from "@/composables/auth/useTokenRefresh";
import { authConfig } from "@/settings";

// 初始化token刷新组合式函数
const { refreshTokenAndRetry } = useTokenRefresh();

// ── 拦截器函数（提取为命名函数，供多实例复用）────────────────────────────────

/**
 * 请求拦截器：注入 Bearer Token，并处理 FormData Content-Type 自动清除。
 */
function requestFulfilled(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
  const accessToken = AuthStorage.getAccessToken();

  if (config.headers.Authorization !== "no-auth" && accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  } else {
    delete config.headers.Authorization;
  }

  // 若为 FormData 上传，移除固定的 JSON Content-Type，让浏览器自动设置 multipart 边界
  if (config.data instanceof FormData) {
    try {
      // @ts-ignore
      if (config.headers && typeof (config.headers as any).delete === "function") {
        (config.headers as any).delete("Content-Type");
      }
      if (config.headers) {
        // @ts-ignore
        delete config.headers["Content-Type"];
        // @ts-ignore
        delete config.headers["content-type"];
      }
    } catch {
      // ignore
    }
  }

  return config;
}

function requestRejected(error: unknown): Promise<never> {
  console.error("Request interceptor error:", error);
  return Promise.reject(error);
}

/**
 * 响应拦截器：解包统一返回格式 {code, data, msg}，处理 401/403/500 等错误码。
 */
function responseFulfilled(response: AxiosResponse<ApiResponse | any>): any {
  if (response.config.responseType === "blob" || response.config.responseType === "arraybuffer") {
    return response;
  }

  const body = response.data as any;

  if (
    !body ||
    typeof body !== "object" ||
    (!("code" in body) && response.status >= 200 && response.status < 300)
  ) {
    return body;
  }

  const { code, data, msg } = body as ApiResponse;

  if (code === ApiCodeEnum.SUCCESS) {
    return data;
  }
  if ((code as any) === 0) {
    return body;
  }

  ElMessage.error(msg || "系统出错");
  return Promise.reject(new Error(msg || "Business Error"));
}

async function responseRejected(error: any): Promise<unknown> {
  console.error("Response interceptor error:", error);

  const { config, response } = error;

  if (!response) {
    ElMessage.error("网络连接失败，请检查网络设置");
    return Promise.reject(error);
  }

  const { code, msg } = response.data as ApiResponse;

  switch (code) {
    case ApiCodeEnum.AUTH_REQUIRED:
    case ApiCodeEnum.ACCESS_TOKEN_INVALID:
      if (authConfig.enableTokenRefresh) {
        return refreshTokenAndRetry(config, httpRequest);
      } else {
        await redirectToLogin("登录已过期，请重新登录");
        return Promise.reject(new Error(msg || "Access Token Invalid"));
      }

    case ApiCodeEnum.REFRESH_TOKEN_INVALID:
      await redirectToLogin("登录已过期，请重新登录");
      return Promise.reject(new Error(msg || "Refresh Token Invalid"));

    case ApiCodeEnum.PERMISSION_DENIED:
      ElMessage.error(msg || "无权限访问");
      return Promise.reject(new Error(msg || "Permission Denied"));

    default: {
      // api_v2 端点采用 DRF 标准错误格式 {detail: "..."}，需展开公共字段兼容
      const detailMsg: string = msg || response.data?.detail || "请求失败";
      ElMessage.error(detailMsg);
      return Promise.reject(new Error(detailMsg));
    }
  }
}

// ── api_v1 请求实例 ───────────────────────────────────────────────────────────

/**
 * 默认请求实例，baseURL = VITE_APP_BASE_API（/api/v1）。
 * 用于所有 api_v1 端点，直接以相对路径调用（如 `/ads/campaigns`）。
 */
const httpRequest = axios.create({
  baseURL: import.meta.env.VITE_APP_BASE_API,
  timeout: 50000,
  headers: { "Content-Type": "application/json;charset=utf-8" },
  paramsSerializer: (params) => qs.stringify(params, { arrayFormat: "repeat" }),
  withCredentials: true,
});

httpRequest.interceptors.request.use(requestFulfilled, requestRejected);
httpRequest.interceptors.response.use(responseFulfilled, responseRejected);

// ── api_v2 请求实例 ───────────────────────────────────────────────────────────

/**
 * api_v2 专用请求实例，baseURL 自动适配环境：
 *   - 生产环境（VITE_APP_API_ORIGIN 非空）：`https://api.hanlis.cn/api/v2`
 *     → 绝对 URL，Axios 完全忽略 VITE_APP_BASE_API 的 /api/v1，不再拼错。
 *   - 开发环境（VITE_APP_API_ORIGIN 为空）：`/dev-api/api/v2`
 *     → Vite 代理匹配 /dev-api/api/v2/* 并剥去 /dev-api，转发到 Django localhost:8000。
 *
 * 使用方式：`import { requestV2 } from "@/utils/request"`
 * 路径只需写端点相对路径（如 `/ads/queue/`），无需拼接域名或版本前缀。
 */
const _v2BaseURL = import.meta.env.VITE_APP_API_ORIGIN
  ? `${import.meta.env.VITE_APP_API_ORIGIN}/api/v2`
  : `${import.meta.env.VITE_APP_BASE_API}/api/v2`;

const httpRequestV2 = axios.create({
  baseURL: _v2BaseURL,
  timeout: 50000,
  headers: { "Content-Type": "application/json;charset=utf-8" },
  paramsSerializer: (params) => qs.stringify(params, { arrayFormat: "repeat" }),
  withCredentials: true,
});

httpRequestV2.interceptors.request.use(requestFulfilled, requestRejected);
httpRequestV2.interceptors.response.use(responseFulfilled, responseRejected);

export { httpRequestV2 as requestV2 };
export default httpRequest;
