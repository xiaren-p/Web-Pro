// https://unocss.nodejs.cn/guide/config-file
import {
  defineConfig,
  presetAttributify,
  presetIcons,
  presetTypography,
  presetUno,
  presetWebFonts,
  transformerDirectives,
  transformerVariantGroup,
} from "unocss";

import { FileSystemIconLoader } from "@iconify/utils/lib/loader/node-loaders";
import fs from "fs";

// 本地SVG图标目录
const iconsDir = "./src/assets/icons";

// 读取本地 SVG 目录，自动生成 safelist
const generateSafeList = () => {
  try {
    return fs
      .readdirSync(iconsDir)
      .filter((file) => file.endsWith(".svg"))
      .map((file) => `i-svg:${file.replace(".svg", "")}`);
  } catch (error) {
    console.error("无法读取图标目录:", error);
    return [];
  }
};

export default defineConfig({
  // 自定义快捷类
  shortcuts: {
    "wh-full": "w-full h-full",
    "flex-center": "flex justify-center items-center",
    "flex-x-center": "flex justify-center",
    "flex-y-center": "flex items-center",
    "flex-x-start": "flex items-center justify-start",
    "flex-x-between": "flex items-center justify-between",
    "flex-x-end": "flex items-center justify-end",
  },
  theme: {
    colors: {
      primary: "var(--el-color-primary)",
      primary_dark: "var(--el-color-primary-light-5)",
    },
    breakpoints: Object.fromEntries(
      [640, 768, 1024, 1280, 1536, 1920, 2560].map((size, index) => [
        ["sm", "md", "lg", "xl", "2xl", "3xl", "4xl"][index],
        `${size}px`,
      ])
    ),
  },
  presets: [
    presetUno(),
    presetAttributify(),
    presetIcons({
      // 额外属性
      extraProperties: {
        display: "inline-block",
        width: "1em",
        height: "1em",
      },
      // 图表集合
      collections: {
        // svg 是图标集合名称，使用 `i-svg:图标名` 调用
        svg: FileSystemIconLoader(iconsDir, (svg) => {
          // 如果 `fill` 没有定义，则添加 `fill="currentColor"`
          return svg.includes('fill="') ? svg : svg.replace(/^<svg /, '<svg fill="currentColor" ');
        }),
        // Tabler Icons：使用 `i-tabler:图标名` 调用，如 i-tabler:activity
        tabler: () => import("@iconify-json/tabler/icons.json"),
      },
    }),
    presetTypography(),
    presetWebFonts({
      fonts: {
        // ...
      },
    }),
  ],
  // 预置需要用到的图标，避免运行时未被扫描导致不生成样式
  safelist: [
    ...generateSafeList(),
    // ── 商品 / 目录 ───────────────────────────────────────────────────────
    "i-tabler:box",
    "i-tabler:package",
    "i-tabler:packages",
    "i-tabler:package-export",
    "i-tabler:package-import",
    "i-tabler:barcode",
    "i-tabler:qrcode",
    "i-tabler:scan",
    "i-tabler:tag",
    "i-tabler:tags",
    "i-tabler:tag-off",
    "i-tabler:photo",
    "i-tabler:list-details",
    "i-tabler:layout-grid",
    "i-tabler:layout-list",
    "i-tabler:category",
    "i-tabler:category-2",
    "i-tabler:cube",
    "i-tabler:color-swatch",
    // ── 订单 / 交易 ───────────────────────────────────────────────────────
    "i-tabler:shopping-cart",
    "i-tabler:shopping-cart-plus",
    "i-tabler:shopping-cart-off",
    "i-tabler:shopping-cart-discount",
    "i-tabler:shopping-bag",
    "i-tabler:basket",
    "i-tabler:basket-plus",
    "i-tabler:basket-off",
    "i-tabler:receipt",
    "i-tabler:receipt-2",
    "i-tabler:receipt-tax",
    "i-tabler:file-invoice",
    "i-tabler:clipboard-list",
    "i-tabler:clipboard-check",
    "i-tabler:notes",
    // ── 物流 / 仓储 ───────────────────────────────────────────────────────
    "i-tabler:truck",
    "i-tabler:truck-delivery",
    "i-tabler:truck-return",
    "i-tabler:truck-off",
    "i-tabler:ship",
    "i-tabler:plane",
    "i-tabler:plane-departure",
    "i-tabler:plane-arrival",
    "i-tabler:building-warehouse",
    "i-tabler:map-pin",
    "i-tabler:map-2",
    "i-tabler:map",
    "i-tabler:route",
    "i-tabler:location",
    // ── 财务 / 支付 ───────────────────────────────────────────────────────
    "i-tabler:credit-card",
    "i-tabler:credit-card-off",
    "i-tabler:wallet",
    "i-tabler:cash",
    "i-tabler:coin",
    "i-tabler:coins",
    "i-tabler:building-bank",
    "i-tabler:moneybag",
    "i-tabler:currency-dollar",
    "i-tabler:currency-yuan",
    "i-tabler:currency-euro",
    "i-tabler:report-money",
    "i-tabler:percentage",
    // ── 营销 / 广告 ───────────────────────────────────────────────────────
    "i-tabler:ad",
    "i-tabler:ad-2",
    "i-tabler:speakerphone",
    "i-tabler:discount",
    "i-tabler:discount-filled",
    "i-tabler:gift",
    "i-tabler:gift-card",
    "i-tabler:star",
    "i-tabler:star-filled",
    "i-tabler:heart",
    "i-tabler:heart-filled",
    "i-tabler:heart-handshake",
    "i-tabler:bell-ringing",
    "i-tabler:confetti",
    // ── 数据 / 报表 ───────────────────────────────────────────────────────
    "i-tabler:chart-bar",
    "i-tabler:chart-line",
    "i-tabler:chart-pie",
    "i-tabler:chart-pie-2",
    "i-tabler:chart-area",
    "i-tabler:chart-dots",
    "i-tabler:trending-up",
    "i-tabler:trending-down",
    "i-tabler:report",
    "i-tabler:report-analytics",
    "i-tabler:dashboard",
    "i-tabler:device-analytics",
    "i-tabler:analyze",
    // ── 供应商 / 采购 ─────────────────────────────────────────────────────
    "i-tabler:building-factory",
    "i-tabler:building-factory-2",
    "i-tabler:building-store",
    "i-tabler:building-community",
    "i-tabler:building",
    "i-tabler:briefcase",
    "i-tabler:file-text",
    "i-tabler:user-dollar",
    // ── 客服 / 用户 ───────────────────────────────────────────────────────
    "i-tabler:users",
    "i-tabler:user-check",
    "i-tabler:user-circle",
    "i-tabler:user-plus",
    "i-tabler:headset",
    "i-tabler:headphones",
    "i-tabler:message-circle",
    "i-tabler:message-dots",
    "i-tabler:message-2",
    "i-tabler:messages",
    "i-tabler:phone",
    "i-tabler:help-circle",
    // ── 平台 / 店铺 ───────────────────────────────────────────────────────
    "i-tabler:brand-amazon",
    "i-tabler:world",
    "i-tabler:world-www",
    "i-tabler:affiliate",
    "i-tabler:home",
    "i-tabler:home-2",
    "i-tabler:flag",
    "i-tabler:apps",
    "i-tabler:api",
    "i-tabler:link",
  ],
  transformers: [transformerDirectives(), transformerVariantGroup()],
});
