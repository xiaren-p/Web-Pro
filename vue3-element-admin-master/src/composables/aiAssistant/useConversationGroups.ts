/**
 * 会话列表分组与搜索辅助工具。
 *
 * 千问风格：按 "今天 / 昨天 / 7 天内 / 30 天内 / 更早" 5 段分组，
 * 每组内部按 ``updated_at`` 倒序，未匹配过的搜索关键词不分组。
 */

import type { AiConversation } from "@/types/aiAssistant/planSchema";

/**
 * 单组对话。
 */
export interface ConversationGroup {
  /** 分组标签：今天 / 昨天 / 7 天内 / 30 天内 / 更早 */
  label: string;
  /** 该分组内的会话列表（已按 updated_at 倒序） */
  items: AiConversation[];
}

const _MS_PER_DAY = 24 * 60 * 60 * 1000;

/**
 * 计算两个日期之间的"自然日差"（按本地时区的零点计算）。
 *
 * @param from - 起始时间
 * @param to - 结束时间（默认 now）
 * @returns 自然日差（>= 0）
 */
function diffDays(from: Date, to: Date = new Date()): number {
  const a = new Date(from.getFullYear(), from.getMonth(), from.getDate()).getTime();
  const b = new Date(to.getFullYear(), to.getMonth(), to.getDate()).getTime();
  return Math.round((b - a) / _MS_PER_DAY);
}

/**
 * 把会话列表按相对时间分组。
 *
 * @param conversations - 后端返回的会话列表（已按 updated_at 倒序）
 * @returns 分组数组，按从近到远排列；空分组会被过滤
 */
export function groupConversationsByDate(conversations: AiConversation[]): ConversationGroup[] {
  const today: AiConversation[] = [];
  const yesterday: AiConversation[] = [];
  const week: AiConversation[] = [];
  const month: AiConversation[] = [];
  const older: AiConversation[] = [];

  for (const conv of conversations) {
    const updated = new Date(conv.updated_at);
    const days = diffDays(updated);
    if (days === 0) today.push(conv);
    else if (days === 1) yesterday.push(conv);
    else if (days <= 7) week.push(conv);
    else if (days <= 30) month.push(conv);
    else older.push(conv);
  }

  return [
    { label: "今天", items: today },
    { label: "昨天", items: yesterday },
    { label: "7 天内", items: week },
    { label: "30 天内", items: month },
    { label: "更早", items: older },
  ].filter((g) => g.items.length > 0);
}

/**
 * 按关键词过滤会话（仅匹配标题）。
 *
 * @param conversations - 全量会话
 * @param keyword - 关键词（不区分大小写）
 * @returns 过滤后的会话列表
 */
export function filterConversations(
  conversations: AiConversation[],
  keyword: string,
): AiConversation[] {
  const trimmed = keyword.trim().toLowerCase();
  if (!trimmed) return conversations;
  return conversations.filter((c) => (c.title || "").toLowerCase().includes(trimmed));
}
