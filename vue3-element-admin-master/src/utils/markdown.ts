/**
 * AI 消息 Markdown 渲染工具。
 *
 * 设计要点：
 *   - 任何 AI 输出在 v-html 之前都必须经过 markdown-it + DOMPurify 双保险
 *   - DOMPurify 默认配置即可阻断 <script>、on* 事件、javascript: URL
 *   - 代码块支持 highlight.js 着色
 *
 * 依赖（首次启用前需安装）：
 *   pnpm add markdown-it @types/markdown-it dompurify @types/dompurify highlight.js
 */

import MarkdownIt from "markdown-it";
import DOMPurify from "dompurify";
import hljs from "highlight.js";

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight: (code: string, lang: string): string => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value;
      } catch {
        return md.utils.escapeHtml(code);
      }
    }
    return md.utils.escapeHtml(code);
  },
});

/**
 * 把 AI Markdown 文本渲染为可直接 v-html 的安全 HTML 串。
 *
 * @param markdown - AI 流式输出累积到当前为止的 markdown 文本
 * @returns 经 DOMPurify 清洗后的安全 HTML 字符串
 */
export function renderAiMarkdown(markdown: string): string {
  if (!markdown) return "";
  const rawHtml = md.render(markdown);
  return DOMPurify.sanitize(rawHtml, {
    USE_PROFILES: { html: true },
  });
}
