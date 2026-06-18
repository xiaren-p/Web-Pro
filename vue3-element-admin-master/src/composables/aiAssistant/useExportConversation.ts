/**
 * 导出 AI 对话为 Markdown 文件。
 *
 * 设计要点：
 *   - 纯前端实现，零后端依赖（消息数据已经在内存里）
 *   - 文件命名：``<会话标题>_<日期>.md``，标题做安全转义防文件系统非法字符
 *   - 内容格式：标题 + 元信息 + 双层分隔的 user / assistant 段
 *   - Plan 卡片消息额外渲染为 JSON 代码块附在文本下方
 */

import type { AiConversation, AiMessage } from "@/types/aiAssistant/planSchema";

/** Windows / macOS / Linux 通用文件名非法字符 */
const _UNSAFE_CHARS_PATTERN = /[\\/:*?"<>|]/g;

/**
 * 把字符串清洗为合法文件名片段。
 *
 * @param raw - 原始字符串
 * @param maxLength - 最大长度
 * @returns 清洗后的安全字符串
 */
function sanitizeFileName(raw: string, maxLength: number = 60): string {
  const cleaned = (raw || "").replace(_UNSAFE_CHARS_PATTERN, "_").trim();
  if (!cleaned) return "未命名对话";
  return cleaned.length > maxLength ? cleaned.slice(0, maxLength) : cleaned;
}

/**
 * 把 ISO 时间字符串格式化为 ``YYYY-MM-DD HH:mm:ss``（本地时区）。
 *
 * @param iso - ISO 时间串
 * @returns 本地化字符串
 */
function formatLocalTime(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number): string => n.toString().padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

/**
 * 把单条消息转换为 Markdown 段落。
 *
 * @param msg - 消息对象
 * @returns Markdown 文本段
 */
function messageToMarkdown(msg: AiMessage): string {
  const heading = msg.role === "user" ? "### 🧑 用户" : "### 🤖 AI 助手";
  const time = formatLocalTime(msg.created_at);
  const lines = [`${heading}  _${time}_`, "", msg.content || "_(无内容)_"];

  if (msg.message_type === "plan" && msg.raw_plan_json) {
    lines.push(
      "",
      "**Plan 提案：**",
      "",
      "```json",
      JSON.stringify(msg.raw_plan_json, null, 2),
      "```"
    );
  }

  if (msg.status === "failed" && msg.error_msg) {
    lines.push("", `> ⚠️ 生成失败：${msg.error_msg}`);
  } else if (msg.status === "cancelled") {
    lines.push("", "> ⚠️ 已取消");
  }

  return lines.join("\n");
}

/**
 * 触发浏览器下载一个文本文件。
 *
 * @param fileName - 下载文件名（含扩展名）
 * @param content - 文件文本内容
 * @param mimeType - MIME 类型，默认 text/markdown
 */
function downloadTextFile(
  fileName: string,
  content: string,
  mimeType: string = "text/markdown;charset=utf-8"
): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  // 浏览器需要异步释放，避免移动端某些浏览器下载未完成就被回收
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * 导出整个会话为 Markdown 文件。
 *
 * @param conversation - 会话元数据（标题、时间）
 * @param messages - 会话内的消息列表（按时间升序）
 */
export function exportConversationAsMarkdown(
  conversation: AiConversation,
  messages: AiMessage[]
): void {
  const title = conversation.title || "新对话";
  const safeTitle = sanitizeFileName(title);
  const datePart = formatLocalTime(conversation.created_at).slice(0, 10);
  const fileName = `${safeTitle}_${datePart}.md`;

  const segments: string[] = [
    `# ${title}`,
    "",
    `> 创建时间：${formatLocalTime(conversation.created_at)}`,
    `> 最后活跃：${formatLocalTime(conversation.updated_at)}`,
    `> 消息数：${messages.length}`,
    "",
    "---",
    "",
  ];

  for (const msg of messages) {
    segments.push(messageToMarkdown(msg));
    segments.push("", "---", "");
  }

  segments.push("", "_由 ERP AI 助手导出_");

  downloadTextFile(fileName, segments.join("\n"));
}
