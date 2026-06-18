/**
 * Plan Mode 数据契约类型定义。
 *
 * 与后端 ``api_v2/services/ai/plan_translator.py`` 输出的字段一一对应。
 * 任何字段调整必须前后端同步修改，避免 SSE 帧出现"前端不识别字段"的回归。
 */

/**
 * Plan 提案的可选项。
 */
export interface PlanOption {
  /** 选项稳定标识符（提交 confirm_action 时用 key 数组回传） */
  key: string;
  /** 选项展示文案 */
  label: string;
  /** 默认是否选中 */
  selected: boolean;
}

/**
 * Plan 提案中的"自定义输入"配置。
 */
export interface PlanCustomField {
  /** 提交时携带的字段名 */
  key: string;
  /** 输入框前的标签文案 */
  label: string;
  /** 输入框 placeholder 提示 */
  placeholder: string;
}

/**
 * Plan 提案确认动作。
 */
export interface PlanConfirmAction {
  /** 提交目标接口；空字符串表示业务端点尚未接入，前端只做本地反馈 */
  endpoint: string;
  /** HTTP 方法，统一大写（POST / PUT / PATCH） */
  method: string;
  /** 按钮文案 */
  button_text: string;
}

/**
 * Plan 提案完整结构（与 PlanCard 组件 props 一致）。
 */
export interface PlanProposal {
  type: "plan_proposal";
  plan_id: string;
  title: string;
  description: string;
  options: PlanOption[];
  multi_select: boolean;
  allow_custom: boolean;
  custom_field: PlanCustomField | null;
  confirm_action: PlanConfirmAction;
  cancellable: boolean;
}

/**
 * 用户在 PlanCard 上确认后回传给"业务执行端点"的载荷。
 */
export interface PlanConfirmPayload {
  plan_id: string;
  selected_keys: string[];
  custom_value: string;
}

/**
 * 单条 AI 消息（来自后端 AiMessageSerializer，已枚举翻译）。
 *
 * id 与 conversation_id 都是后端 ``public_id`` 字段映射的 UUID 字符串，
 * 前端不应感知后端内部整数主键。
 */
export interface AiMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  role_label: string;
  message_type: "text" | "plan";
  message_type_label: string;
  status: "pending" | "streaming" | "done" | "failed" | "cancelled";
  status_label: string;
  content: string;
  raw_plan_json: PlanProposal | null;
  error_msg: string;
  created_at: string;
  updated_at: string;
}

/**
 * 会话列表项（来自 AiConversationSerializer）。
 *
 * 含分组归属与置顶状态，前端据此决定排序与展示。
 */
export interface AiConversation {
  id: string;
  title: string;
  dify_conversation_id: string;
  /** 所属分组 UUID；null 表示未分组 */
  group_id: string | null;
  /** 是否已置顶 */
  is_pinned: boolean;
  /** 置顶时间；未置顶为 null */
  pinned_at: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * 用户自定义分组。
 */
export interface AiConversationGroup {
  id: string;
  name: string;
  order: number;
  created_at: string;
  updated_at: string;
}

/**
 * 全文搜索命中条目。
 */
export interface AiSearchHit {
  conversation_id: string;
  conversation_title: string;
  /** 命中消息 UUID；命中标题时为 null */
  message_id: string | null;
  /** 命中消息角色；命中标题时为 null */
  role: "user" | "assistant" | null;
  /** 命中片段（前后已截断） */
  snippet: string;
  /** 匹配时间，用于二级排序 */
  matched_at: string;
}

/**
 * ``POST /api/v2/ai/chat/`` 的响应结构。
 *
 * 所有 ID 字段均为 UUID 字符串。
 */
export interface ChatStartResponse {
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  task_id: string;
}
