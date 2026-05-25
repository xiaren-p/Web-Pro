/**
 * 开发者应用类型定义。
 * 对应后端 api_v2/developer/apps/ 接口数据契约。
 */

/** 应用列表项（不含 Client Secret） */
export interface DeveloperApp {
  /** 应用主键 */
  id: number;
  /** 应用名称 */
  name: string;
  /** Client ID（可公开） */
  client_id: string;
  /** 创建时间（ISO 8601） */
  created: string;
  /** 最后更新时间（ISO 8601） */
  updated: string;
}

/** 应用创建成功响应（含 Client Secret，仅此一次） */
export interface DeveloperAppCreated extends Omit<DeveloperApp, "updated"> {
  /** Client Secret —— 仅在创建响应中出现，前端必须立即引导用户保存 */
  client_secret: string;
}

/** 密钥轮换成功响应 */
export interface SecretRotated {
  /** 新 Client Secret（仅此一次显示） */
  client_secret: string;
  /** 轮换时间（ISO 8601 UTC） */
  rotated_at: string;
}

/** 创建应用请求体 */
export interface AppCreatePayload {
  name: string;
}

/** 一次性凭据展示数据（兼容创建与轮换两种场景） */
export interface OneTimeCredentials {
  /** 应用名称（轮换时从列表中取，创建时来自响应） */
  name: string;
  /** Client ID */
  client_id: string;
  /** Client Secret（仅此一次） */
  client_secret: string;
  /** 场景标识 */
  scene: "created" | "rotated";
}
