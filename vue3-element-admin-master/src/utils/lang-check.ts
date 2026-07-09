/**
 * 语言检测工具：基于 franc 库校验输入文本是否匹配期望语言。
 *
 * 使用场景：刊登草稿编辑器双栏表单，左栏站点语言、右栏中文。
 * 校验时机：@input 实时校验，校验失败 → 输入框飘红 + 警告提示 + 阻止发布。
 */

import { franc } from "franc";

/**
 * 站点 → 期望语言（ISO 639-3）映射表。
 * key 为店铺后缀（如 DE/US/FR），value 为 franc 语言代码。
 */
export const SITE_LANG_MAP: Record<string, { code: string; label: string }> = {
  DE: { code: "deu", label: "德语" },
  US: { code: "eng", label: "英语" },
  UK: { code: "eng", label: "英语" },
  FR: { code: "fra", label: "法语" },
  ES: { code: "spa", label: "西班牙语" },
  IT: { code: "ita", label: "意大利语" },
  PT: { code: "por", label: "葡萄牙语" },
  NL: { code: "nld", label: "荷兰语" },
  PL: { code: "pol", label: "波兰语" },
  SE: { code: "swe", label: "瑞典语" },
  JP: { code: "jpn", label: "日语" },
  MX: { code: "spa", label: "西班牙语" },
  BR: { code: "por", label: "葡萄牙语" },
  AU: { code: "eng", label: "英语" },
  CA: { code: "eng", label: "英语" },
};

/** 中文语言代码 */
const CN_LANG_CODE = "cmn";

/**
 * 从店铺名称中提取站点代码。
 * 例："AS（本本）-DE" → "DE"，"Amazon US" → "US"
 */
export function extractSiteCode(shopName: string): string {
  if (!shopName) return "";
  const match = shopName.match(/[-_]?([A-Z]{2})\b/i);
  return match ? match[1].toUpperCase() : "";
}

/**
 * 检测文本语言是否匹配期望语言。
 *
 * @param text - 待检测文本
 * @param expectedCode - 期望语言代码（ISO 639-3）
 * @returns true = 匹配或文本太短无法判定，false = 不匹配
 */
export function isLangMatch(text: string, expectedCode: string): boolean {
  if (!text || text.trim().length < 3) return true;
  const detected = franc(text, { minLength: 3 });
  if (detected === "und") return true;
  return detected === expectedCode;
}

/**
 * 检测文本是否为中文。
 */
export function isChinese(text: string): boolean {
  return isLangMatch(text, CN_LANG_CODE);
}

/**
 * 检测文本是否为指定站点语言。
 */
export function isSiteLang(text: string, siteCode: string): boolean {
  const lang = SITE_LANG_MAP[siteCode];
  if (!lang) return true;
  return isLangMatch(text, lang.code);
}

/**
 * 校验结果接口。
 */
export interface LangCheckResult {
  valid: boolean;
  message: string;
}

/**
 * 校验中文内容字段：必须为中文。
 */
export function validateChinese(text: string, fieldName: string): LangCheckResult {
  if (!text || text.trim().length < 3) return { valid: true, message: "" };
  if (!isChinese(text)) {
    return { valid: false, message: `${fieldName}：请输入中文内容` };
  }
  return { valid: true, message: "" };
}

/**
 * 校验站点语言字段：必须为站点语言（非中文）。
 */
export function validateSiteLang(
  text: string,
  siteCode: string,
  fieldName: string
): LangCheckResult {
  if (!text || text.trim().length < 3) return { valid: true, message: "" };
  const lang = SITE_LANG_MAP[siteCode];
  if (!lang) return { valid: true, message: "" };
  if (!isSiteLang(text, siteCode)) {
    return { valid: false, message: `${fieldName}：请输入${lang.label}内容` };
  }
  return { valid: true, message: "" };
}
