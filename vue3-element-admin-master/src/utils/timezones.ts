/**
 * 国家 → IANA 时区映射表，与后端 _COUNTRY_TIMEZONE 保持一致。
 * 前/后端统一映射，避免每模块重复创建。
 */
export const COUNTRY_TIMEZONE: Record<string, string> = {
  US: "America/Los_Angeles",
  CA: "America/Toronto",
  MX: "America/Mexico_City",
  BR: "America/Sao_Paulo",
  GB: "Europe/London",
  UK: "Europe/London",
  DE: "Europe/Berlin",
  FR: "Europe/Paris",
  IT: "Europe/Rome",
  ES: "Europe/Madrid",
  NL: "Europe/Amsterdam",
  SE: "Europe/Stockholm",
  PL: "Europe/Warsaw",
  BE: "Europe/Brussels",
  TR: "Europe/Istanbul",
  AE: "Asia/Dubai",
  SA: "Asia/Riyadh",
  IN: "Asia/Kolkata",
  JP: "Asia/Tokyo",
  AU: "Australia/Sydney",
  SG: "Asia/Singapore",
  CN: "Asia/Shanghai",
}

/**
 * IANA 时区 → UTC 偏移（冬季基准），前端展示 fallback。
 * 用于无法动态计算的场景，主路径应使用 getLocalTimeString。
 */
export const TIMEZONE_UTC_OFFSET: Record<string, number> = {
  "America/Los_Angeles": -8,
  "America/Toronto": -5,
  "America/Mexico_City": -6,
  "America/Sao_Paulo": -3,
  "Europe/London": 0,
  "Europe/Berlin": 1,
  "Europe/Paris": 1,
  "Europe/Rome": 1,
  "Europe/Madrid": 1,
  "Europe/Amsterdam": 1,
  "Europe/Stockholm": 1,
  "Europe/Warsaw": 1,
  "Europe/Brussels": 1,
  "Europe/Istanbul": 3,
  "Asia/Dubai": 4,
  "Asia/Riyadh": 3,
  "Asia/Kolkata": 5,
  "Asia/Tokyo": 9,
  "Australia/Sydney": 10,
  "Asia/Singapore": 8,
  "Asia/Shanghai": 8,
}

/**
 * 将 UTC ISO 字符串按指定 IANA 时区格式化为本地时间。
 * 时区名无效时回退为浏览器本地时间。
 */
export function formatTimeInZone(utcIso: string, timezone?: string): string {
  if (!utcIso) return "-"
  const d = new Date(utcIso)
  const opts: Intl.DateTimeFormatOptions = {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  }
  if (timezone) {
    try {
      return d.toLocaleString("zh-CN", { ...opts, timeZone: timezone })
    } catch {
      // fallback：无效时区 → 浏览器本地时间
    }
  }
  return d.toLocaleString("zh-CN", opts)
}
