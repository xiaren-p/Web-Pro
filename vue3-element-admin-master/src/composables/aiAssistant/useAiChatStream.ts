/**
 * AI 消息 SSE 订阅 composable。
 *
 * 设计要点：
 *   - 使用 fetch + ReadableStream 而非 EventSource：
 *       EventSource 不支持自定义 Authorization 头（项目用 Bearer Token），
 *       fetch 模式可手动注入 token，且能在断流后主动 abort。
 *   - 自动解析 SSE 协议（``event:`` + ``data:`` + 空行帧分隔），
 *     按 event 类型分发到对应回调（onToken / onPlan / onMessageMeta / onError / onDone）。
 *   - 暴露 abort 方法，组件卸载或用户切换会话时主动断流。
 *   - 该 composable 可被多次调用以支持"同一页面多个对话同时进行"。
 */

import { AuthStorage } from "@/utils/auth";
import type { PlanProposal } from "@/types/aiAssistant/planSchema";

/**
 * 构造 SSE 订阅完整 URL。
 *
 * 与 src/utils/request.ts 中 requestV2 的 baseURL 推导逻辑保持一致：
 *   - 生产环境（VITE_APP_API_ORIGIN 非空）：``https://api.hanlis.cn/api/v1/ai/stream/<id>/``
 *   - 开发环境（VITE_APP_API_ORIGIN 为空）：``/dev-api/ai/stream/<id>/``，由 Vite 代理转发
 *
 * @param messageId - 要订阅的 AI 消息 ID
 * @returns SSE 端点完整 URL
 */
function buildStreamUrl(messageId: string): string {
  const origin = import.meta.env.VITE_APP_API_ORIGIN;
  const base = origin ? `${origin}/api/v1` : import.meta.env.VITE_APP_BASE_API;
  return `${base}/ai/stream/${messageId}/`;
}

/**
 * SSE 订阅回调集合。
 */
export interface SubscribeHandlers {
  /** 收到一段 token：text 为本次新增的字（replay=true 表示是历史回放，前端可考虑重置展示） */
  onToken?: (data: { text: string; replay?: boolean }) => void;
  /** 收到 plan 提案，前端切换为卡片渲染 */
  onPlan?: (plan: PlanProposal) => void;
  /** 收到消息元数据（首帧后即可拿到 conversation_id / message_id，UUID 字符串） */
  onMessageMeta?: (meta: { conversation_id: string; message_id: string }) => void;
  /** 后端业务错误（不是网络错误） */
  onError?: (err: { code: string; message: string }) => void;
  /** 流结束（正常完成 / 取消 / 失败 / 超时均会触发一次） */
  onDone?: (data: { reason?: string; cancelled?: boolean; final_status?: string }) => void;
  /** 网络层异常（fetch 抛出、连接断开、解析错误） */
  onNetworkError?: (err: Error) => void;
}

/**
 * 订阅句柄，调用 abort() 可主动断流。
 */
export interface SubscribeHandle {
  abort: () => void;
}

/**
 * 单条 SSE 帧的解析结果。
 */
interface ParsedFrame {
  event: string;
  data: string;
}

/**
 * 启动一次 SSE 订阅，返回可中止的句柄。
 *
 * @param messageId - 要订阅的 AI 消息 ID
 * @param handlers - 事件回调集合
 * @returns 可中止订阅的句柄
 */
export function useAiChatStream(messageId: string, handlers: SubscribeHandlers): SubscribeHandle {
  const controller = new AbortController();

  void runSubscribe(messageId, handlers, controller).catch((err: Error) => {
    if (err.name === "AbortError") return;
    handlers.onNetworkError?.(err);
  });

  return {
    abort: () => controller.abort(),
  };
}

/**
 * 实际跑订阅循环的内部函数。分离出来便于在外层捕获异常。
 *
 * @param messageId - 消息 ID
 * @param handlers - 回调
 * @param controller - 中止信号
 */
async function runSubscribe(
  messageId: string,
  handlers: SubscribeHandlers,
  controller: AbortController
): Promise<void> {
  const token = AuthStorage.getAccessToken();
  const response = await fetch(`${buildStreamUrl(messageId)}`, {
    method: "GET",
    headers: {
      Accept: "text/event-stream",
      Authorization: token ? `Bearer ${token}` : "",
    },
    signal: controller.signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`SSE 订阅失败 status=${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE 帧以"空行"分隔（\n\n），可能跨多个 chunk，所以累积到 buffer 再切
    let separatorIdx: number;
    while ((separatorIdx = buffer.indexOf("\n\n")) !== -1) {
      const rawFrame = buffer.slice(0, separatorIdx);
      buffer = buffer.slice(separatorIdx + 2);
      const parsed = parseFrame(rawFrame);
      if (parsed) {
        dispatchFrame(parsed, handlers);
      }
    }
  }
}

/**
 * 解析单条 SSE 帧为 { event, data } 结构。
 *
 * 注释行（以 ``:`` 开头）属心跳，本函数返回 null 由调用方丢弃。
 *
 * @param rawFrame - 原始帧文本（不含尾部空行）
 * @returns 解析结果，注释帧或非法帧返回 null
 */
function parseFrame(rawFrame: string): ParsedFrame | null {
  if (!rawFrame || rawFrame.startsWith(":")) return null;

  let event = "message";
  const dataLines: string[] = [];

  for (const line of rawFrame.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

/**
 * 把已解析的 SSE 帧分发到合适的回调。
 *
 * @param frame - 解析后的帧
 * @param handlers - 用户提供的回调集合
 */
function dispatchFrame(frame: ParsedFrame, handlers: SubscribeHandlers): void {
  let payload: unknown;
  try {
    payload = JSON.parse(frame.data);
  } catch {
    return;
  }

  switch (frame.event) {
    case "token":
      handlers.onToken?.(payload as { text: string; replay?: boolean });
      break;
    case "plan":
      handlers.onPlan?.(payload as PlanProposal);
      break;
    case "message_meta":
      handlers.onMessageMeta?.(payload as { conversation_id: string; message_id: string });
      break;
    case "error":
      handlers.onError?.(payload as { code: string; message: string });
      break;
    case "done":
      handlers.onDone?.(payload as { reason?: string; cancelled?: boolean; final_status?: string });
      break;
    default:
      break;
  }
}
