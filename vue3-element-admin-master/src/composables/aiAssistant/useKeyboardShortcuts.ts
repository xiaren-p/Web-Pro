/**
 * 全局键盘快捷键注册（仅在 AI 抽屉打开时生效）。
 *
 * 支持的快捷键：
 *   - Ctrl/Cmd + K     聚焦搜索框
 *   - Ctrl/Cmd + /     新建对话
 *   - Esc              关闭抽屉
 *
 * 设计原则：
 *   - 调用方传入回调，不在此处直接操作 store / DOM，便于复用
 *   - 表单输入元素聚焦时不响应（avoid hijacking text editing keys）
 *   - 在 onUnmounted 自动解绑，杜绝多实例叠加
 */

import { onMounted, onBeforeUnmount } from "vue";

/**
 * 快捷键回调集合。
 */
export interface ShortcutHandlers {
  /** Ctrl/Cmd + K：通常用于聚焦搜索框 */
  onFocusSearch?: () => void;
  /** Ctrl/Cmd + /：通常用于新建对话 */
  onNewConversation?: () => void;
  /** Esc：通常用于关闭面板 */
  onEscape?: () => void;
}

/**
 * 当前焦点是否落在可编辑元素（input / textarea / contenteditable）上。
 *
 * @returns true 表示用户正在编辑文本，应忽略全局快捷键
 */
function isEditing(): boolean {
  const el = document.activeElement as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (el.isContentEditable) return true;
  return false;
}

/**
 * 注册 AI 助手全局快捷键。
 *
 * @param handlers - 各快捷键对应的回调
 * @param enabled - 响应式 getter，返回 true 时才生效（如抽屉打开状态）
 */
export function useKeyboardShortcuts(handlers: ShortcutHandlers, enabled: () => boolean): void {
  function onKeyDown(event: KeyboardEvent): void {
    if (!enabled()) return;

    const isMod = event.ctrlKey || event.metaKey;

    // Ctrl/Cmd + K：聚焦搜索（即便在 input 里也允许，便于快速跳转到搜索）
    if (isMod && event.key.toLowerCase() === "k") {
      event.preventDefault();
      handlers.onFocusSearch?.();
      return;
    }

    // Ctrl/Cmd + /：新建对话（在编辑状态下也允许）
    if (isMod && event.key === "/") {
      event.preventDefault();
      handlers.onNewConversation?.();
      return;
    }

    // Esc：关闭抽屉（仅在非编辑态生效，避免抢走 IME 取消等行为）
    if (event.key === "Escape" && !isEditing()) {
      handlers.onEscape?.();
    }
  }

  onMounted(() => {
    window.addEventListener("keydown", onKeyDown);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("keydown", onKeyDown);
  });
}
