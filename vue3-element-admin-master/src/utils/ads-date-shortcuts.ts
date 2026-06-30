/**
 * 广告模块日期范围选择器快捷选项：近 7 天 / 近 30 天 / 本月 / 上月 / 本年 / 去年。
 * 所有范围的结束日期均为昨天（广告数据有 T+1 延迟，当天数据不完整）。
 */

/**
 * el-date-picker shortcuts 数组元素签名。
 */
interface DateShortcut {
  text: string;
  value: () => [Date, Date];
}

/**
 * 获取昨天 23:59:59.999 的 Date 对象。
 */
function yesterday(): Date {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  d.setHours(23, 59, 59, 999);
  return d;
}

/**
 * 获取 n 天前 00:00:00.000 的 Date 对象。
 */
function daysAgo(n: number): Date {
  const d = new Date();
  d.setDate(d.getDate() - n);
  d.setHours(0, 0, 0, 0);
  return d;
}

/** 广告模块通用日期快捷选项，所有范围结束于昨天。 */
export const DATE_SHORTCUTS: DateShortcut[] = [
  {
    text: "近 7 天",
    value: () => [daysAgo(6), yesterday()],
  },
  {
    text: "近 30 天",
    value: () => [daysAgo(29), yesterday()],
  },
  {
    text: "本月",
    value: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      return [start, yesterday()];
    },
  },
  {
    text: "上月",
    value: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const end = new Date(now.getFullYear(), now.getMonth(), 0, 23, 59, 59, 999);
      return [start, end];
    },
  },
  {
    text: "本年",
    value: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), 0, 1);
      return [start, yesterday()];
    },
  },
  {
    text: "去年",
    value: () => {
      const now = new Date();
      const start = new Date(now.getFullYear() - 1, 0, 1);
      const end = new Date(now.getFullYear() - 1, 11, 31, 23, 59, 59, 999);
      return [start, end];
    },
  },
];
