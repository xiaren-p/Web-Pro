/**
 * 亏损订单页通用辅助：常量、纯函数、行映射工厂。
 * 所属板块：statistics / lossmakingOrders。
 *
 * 注意：本文件仅承载视图无关的纯逻辑。任何与 DOM / Element Plus 交互的代码请放入页面或子组件。
 */
import type { Ref } from "vue";

/** 全选店铺标记。 */
export const ALL_SHOPS_VALUE = "__ALL__";

/** 全选负责人标记。 */
export const ALL_OWNERS_VALUE = "__ALL_OWNERS__";

/** 币种下拉选项（含原币种）。 */
export const currencies: Array<{ label: string; value: string }> = [
  { label: "原币种", value: "original" },
  { label: "CNY", value: "CNY" },
  { label: "USD", value: "USD" },
  { label: "EUR", value: "EUR" },
  { label: "JPY", value: "JPY" },
  { label: "AUD", value: "AUD" },
  { label: "CAD", value: "CAD" },
  { label: "MXN", value: "MXN" },
  { label: "GBP", value: "GBP" },
  { label: "INR", value: "INR" },
  { label: "AED", value: "AED" },
  { label: "SGD", value: "SGD" },
  { label: "SAR", value: "SAR" },
  { label: "BRL", value: "BRL" },
  { label: "SEK", value: "SEK" },
  { label: "PLN", value: "PLN" },
  { label: "TRY", value: "TRY" },
  { label: "HKD", value: "HKD" },
];

/** 解析任意输入为数字，剥离千分位与货币符号；无法解析返回 NaN。 */
export function parseNumber(v: any): number {
  try {
    if (v === null || v === undefined || v === "") return NaN;
    if (typeof v === "number") return v;
    const s = String(v)
      .replace(/,/g, "")
      .replace(/[^0-9.\-eE]/g, "");
    const n = parseFloat(s);
    return isNaN(n) ? NaN : n;
  } catch {
    return NaN;
  }
}

/** 把 Date 格式化为 `YYYY-MM-DD` 字符串。 */
export function formatDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** 前端规则二次预览占位：当前直接返回，后续如需本地筛选可扩展。 */
export function applyFrontendRule(items: any[], _rule: string | null): any[] {
  if (!_rule) return items;
  try {
    return items;
  } catch {
    return items;
  }
}

/** 根据规则代码返回中文描述（用于提示气泡）。 */
export function ruleDescription(rule: string | null): string {
  if (!rule) return "";
  if (rule === "rule1")
    return "规则一：满足任一条件 — 毛利润 < 0，或 退款率 > 15%，或 广告费率 > 10%";
  if (rule === "rule2")
    return "规则二：同时满足三项条件 — 毛利润 < 0 且 退款率 > 15% 且 广告费率 > 10%";
  if (rule === "rule3") return "规则三：满足毛利润 < 0 且 退款率 > 15%";
  if (rule === "rule4") return "规则四：满足毛利润 < 0 且 广告费率 > 10%";
  return "";
}

/** 店铺下拉项响应式引用类型。 */
export type ShopOptionRef = Ref<Array<{ label: string; value: string; country?: string }>>;

/**
 * 创建后端 item → 表格 row 的映射函数。
 * 之所以用工厂模式：mapItemToRow 需要读取当前 shops 列表来回填 shop_label / shop_country，
 * 通过闭包注入 shopsRef 可保持响应式且避免视图层耦合。
 */
export function createRowMapper(shopsRef: ShopOptionRef) {
  return function mapItemToRow(it: any) {
    const price_list = it.price_list || [];
    const msku =
      Array.isArray(price_list) && price_list.length
        ? price_list.map((p: any) => p && (p.local_sku || p.sku)).filter(Boolean)
        : it.seller_sku
          ? Array.isArray(it.seller_sku)
            ? it.seller_sku
            : [it.seller_sku]
          : [];
    const asin =
      Array.isArray(price_list) && price_list.length
        ? price_list.map((p: any) => p && p.asin).filter(Boolean)
        : it.asin
          ? Array.isArray(it.asin)
            ? it.asin
            : [it.asin]
          : [];
    const parent_asin = it.parent_asins || [];
    const raw_local_infos = it.local_infos || [];
    const local_infos = Array.isArray(raw_local_infos)
      ? raw_local_infos
          .map((li: any) => {
            if (!li) return null;
            if (typeof li === "string") return { local_name: "", local_sku: li };
            return {
              local_name: li.local_name || li.name || "",
              local_sku: li.local_sku || li.sku || "",
            };
          })
          .filter(Boolean)
      : [];
    const title_sku_pairs = local_infos
      .map((li: any) => ({
        name: li.local_name || "",
        sku: li.local_sku || "",
      }))
      .filter((p: any) => p.name || p.sku);

    const raw_principals = it.principal_names || it.principals || it.principal || [];
    let principal_names: string[] = [];
    if (Array.isArray(raw_principals)) {
      principal_names = raw_principals.map((p: any) => String(p).trim()).filter(Boolean);
    } else if (typeof raw_principals === "string") {
      principal_names = raw_principals
        .split(/[\n,;]+/)
        .map((s: string) => s.trim())
        .filter(Boolean);
    } else if (raw_principals) {
      principal_names = [String(raw_principals)];
    }

    const raw_countries = it.seller_store_countries || [];
    const country_names = Array.isArray(raw_countries)
      ? raw_countries
          .map((c: any) => (typeof c === "string" ? c : (c && (c.name || c.label)) || ""))
          .filter(Boolean)
      : [];

    let shop_label = "";
    let shop_country = "";
    try {
      const sid = (it.sids && it.sids[0]) || null;
      if (sid) {
        const found = shopsRef.value.find((s) => String(s.value) === String(sid));
        if (found) {
          shop_label = found.label || String(sid);
          shop_country = found.country || "";
        } else if (country_names.length) {
          shop_label = country_names[0];
          shop_country = "";
        } else {
          shop_label = String(sid);
          shop_country = "";
        }
      } else if (country_names.length) {
        shop_label = country_names[0];
        shop_country = "";
      }
    } catch {
      shop_label = "";
      shop_country = "";
    }

    const imageFallback = ((): string => {
      if (it.small_image_url) return it.small_image_url;
      if (Array.isArray(price_list) && price_list.length) {
        for (const p of price_list) {
          if (!p) continue;
          if (p.small_main_image_url) return p.small_main_image_url;
          if (p.small_image_url) return p.small_image_url;
          if (p.small_image) return p.small_image;
        }
      }
      return "";
    })();

    const gross_profit_num = parseNumber(it.gross_profit);
    const refund_amount_rate_num = parseNumber(it.refund_amount_rate);
    const spend_rate_num = parseNumber(it.spend_rate);
    const cond1 = !isNaN(gross_profit_num) && gross_profit_num < 0;
    const cond2 = !isNaN(refund_amount_rate_num) && refund_amount_rate_num > 0.15;
    const cond3 = !isNaN(spend_rate_num) && spend_rate_num > 0.1;
    let matched_rule: string | null = null;
    if (cond1 && cond2 && cond3) matched_rule = "rule2";
    else if (cond1 && cond2) matched_rule = "rule3";
    else if (cond1 && cond3) matched_rule = "rule4";

    return {
      image: imageFallback,
      msku: Array.isArray(msku) ? msku : [msku].filter(Boolean),
      asin: Array.isArray(asin) ? asin : [asin].filter(Boolean),
      parent_asin: Array.isArray(parent_asin) ? parent_asin : [parent_asin].filter(Boolean),
      title_sku_pairs,
      title_sku: title_sku_pairs.map((p: any) => (p.name || "") + (p.sku ? " / " + p.sku : "")),
      principal_names,
      shop_label,
      shop_country,
      currency_icon: it.currency_icon || it.currency_code || "",
      gross_profit: it.gross_profit,
      gross_margin: it.gross_margin,
      net_gross_margin: it.net_gross_margin,
      return_rate: it.return_rate,
      refund_amount_rate: it.refund_amount_rate,
      total_stock_fee: it.total_stock_fee,
      spend: it.spend,
      spend_rate: it.spend_rate,
      matched_rule,
    };
  };
}
