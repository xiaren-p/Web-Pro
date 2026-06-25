/** 日期工具函数。 */

/**
 * 返回今天前 7 天的日期范围。
 *
 * @returns {[string, string]} [开始日期, 结束日期]，格式 YYYY-MM-DD
 */
export function getDefaultDateRange(): [string, string] {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 7);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  return [fmt(start), fmt(end)];
}

/** 日期同步 localStorage key — 子面板与主页共享 */
export const DATE_RANGE_KEY = "ADS_SP_DATE_RANGE";
