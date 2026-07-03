/**
 * 开发者应用管理 API 模块。
 * 封装开发者 Client Credentials 应用的 CRUD 与密钥轮换接口。
 * 仅供登录用户调用，不接受机器令牌。
 */
import request from "@/utils/request";
import type {
  AppCreatePayload,
  DeveloperApp,
  DeveloperAppCreated,
  SecretRotated,
} from "@/types/developer/app";

/**
 * 获取当前用户的应用列表。
 *
 * @returns {Promise<{ results: DeveloperApp[] }>} 应用列表（不含 Secret）。
 */
export function fetchApps(): Promise<{ results: DeveloperApp[] }> {
  return request.get("/api/v1/developer/apps/");
}

/**
 * 创建新的 Client Credentials 应用。
 *
 * @param {AppCreatePayload} payload - 包含 name 字段的创建参数。
 * @returns {Promise<DeveloperAppCreated>} 创建结果（含 client_secret，仅此一次）。
 */
export function createApp(payload: AppCreatePayload): Promise<DeveloperAppCreated> {
  return request.post("/api/v1/developer/apps/create/", payload);
}

/**
 * 删除指定应用（级联撤销所有关联 AccessToken）。
 *
 * @param {number} appId - 应用主键 ID。
 * @returns {Promise<void>}
 */
export function deleteApp(appId: number): Promise<void> {
  return request.delete(`/api/v1/developer/apps/${appId}/`);
}

/**
 * 轮换应用 Client Secret（同步撤销当前全部有效 AccessToken）。
 *
 * @param {number} appId - 应用主键 ID。
 * @returns {Promise<SecretRotated>} 新 Secret 及轮换时间（仅此一次）。
 */
export function rotateAppSecret(appId: number): Promise<SecretRotated> {
  return request.post(`/api/v1/developer/apps/${appId}/rotate-secret/`);
}
