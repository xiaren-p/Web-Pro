/**
 * 路由标题国际化翻译工具。
 */
import i18n from "@/lang/index";

/**
 * 翻译路由 meta.title，用于面包屑、侧边栏、标签页。
 *
 * @param title - 路由标题。
 * @returns 翻译后的标题，无配置时返回原文。
 */
export function translateRouteTitle(title: string) {
  const hasKey = i18n.global.te("route." + title);
  if (hasKey) return i18n.global.t("route." + title);
  return title;
}
