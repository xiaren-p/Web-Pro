/**
 * 商品类型 JSON Schema 解析 composable。
 *
 * ============================================================
 * 职责：将后端返回的 Amazon ProductType JSON Schema 解析为前端可渲染的字段配置。
 * ============================================================
 *
 * 仿写领星 parse_json_mixins.js 的 getFormData() 逻辑：
 *
 * ```
 * 后端 API 返回的原始结构（getProductTypeNew）：
 * {
 *   properties: "{..., properties: { item_name: { type: 'array', items: {...} } } }"  ← JSON 字符串
 *   properties_zh: "{...}"
 * }
 *
 * 本 composable 的输入：后端已解析为 fields / fieldsZh / requiredFields
 *                      （即 ProductTypeSchemaVO）
 * 本 composable 的输出：ParsedFieldConfig[]（嵌套结构，保持 Amazon Schema 的层次）
 * ```
 *
 * 类型映射规则（来自领星 getFormData 内层函数 l）：
 *
 * | 原始 JSON Schema 类型 | 映射结果 | 说明 |
 * |----------------------|---------|------|
 * | string + enum        | select  | options 从 enum/enumNames 构建 |
 * | string + oneOf       | date    | oneOf 表示日期格式约束 |
 * | string + anyOf(enum) | select  | allowCreate=true，允许用户输入 |
 * | string               | string  | 纯文本输入框 |
 * | number               | number  | 数字输入，带 minimum/maximum/multipleOf 约束 |
 * | integer              | integer | 整数输入，同上 |
 * | boolean              | radio   | 是/否 单选 |
 *
 * 字段分类规则（仿领星 fieldClassification）：
 * - 按 attrName 硬编码匹配 5 个清单（BASIC/QUOTE/IMAGE/DESC/FILTER）
 * - 未匹配的归入 otherFields，由"更多属性" section 动态渲染
 *
 * @example 典型数据流
 * ```typescript
 * // 在组件中使用：
 * const { loading, otherFields, dynamicFormData } = useProductTypeSchema(
 *   () => marketplaceId,
 *   () => productType
 * );
 * // otherFields.value 是解析后的字段配置数组
 * // dynamicFormData.site[field.attrName] = [{ value: "", marketplace_id: "ATVPDKIKX0DER" }]
 * ```
 */
import { ref, reactive, watch, toValue } from "vue";
import type { Ref, MaybeRefOrGetter } from "vue";
import { ListingPublishAPI } from "@/api/sales/listing-publish";
import type { SchemaFieldDef, ProductTypeSchemaVO } from "@/api/sales/listing-publish/types";

// ─────────────────────────────────────────────────────────────────────────────
// 类型定义
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 解析后的表单字段配置。
 *
 * @description 完整保留 Amazon Schema 的嵌套结构，不压平。
 * 领星的 fieldConfig 结构为：
 * ```
 * {
 *   attr_name: "item_dimensions",
 *   label: ["尺寸", "Item Dimensions"],     // [中文, 站点语言]
 *   description: ["描述", "Description"],
 *   fields: {                                // ← 组字段专有
 *     length: { attrName: "length", type: "number", label: [...], ... },
 *     width: { attrName: "width", type: "number", label: [...], ... },
 *     height: { attrName: "height", type: "number", label: [...], ... },
 *   },
 *   itemsRequired: ["length", "width"],      // ← items.required
 * }
 * ```
 * 叶子字段（无 fields）直接映射为输入控件 type。
 *
 * @see useFieldClassification.ts - 消费此配置做渲染分类
 * @see DynamicFieldItem.vue - 消费 type 和 options 渲染控件
 */
export interface ParsedFieldConfig {
  /**
   * 字段标识名。
   *
   * @description 对应 Amazon Schema properties 的 key，
   * 如 item_name、item_dimensions、language 等。
   * 也用于表单数据的 key 匹配（dynamicFormData.site[attrName]）。
   */
  attrName: string;

  /**
   * 双语标签 [中文, 站点语言]。
   *
   * @description label[0] 为中文标题（取自 properties_zh.title 或字段名），
   * label[1] 为站点语言标题（取自 properties.title 或字段名）。
   * 渲染时 label[0] 加上 * 红色星号，label[1] 灰色显示在下方。
   *
   * @example ["商品名称", "Item Name"]
   */
  label: [string, string];

  /**
   * 双语描述 [中文, 站点语言]。
   *
   * @description description[0] 为中文描述，
   * description[1] 为站点语言描述。
   * 当 description 非空时，Label 旁渲染 tooltip 图标。
   */
  description: [string, string];

  /**
   * 表单控件类型。
   *
   * @description 由 mapFieldType() 根据 JSON Schema 的 type + 约束推导：
   * - "string"：纯文本 el-input
   * - "select"：el-select 下拉框（allowCreate 控制是否允许自定义）
   * - "number"：数字 el-input（小数，带 minimum/maximum 后缀提示）
   * - "integer"：整数 el-input
   * - "date"：el-date-picker 日期选择器
   * - "radio"：el-radio-group 是/否单选
   *
   * 注意：type 仅对叶子字段有意义。组字段（有 fields）的 type 固定为 "string"，
   * 但实际不会渲染为自己，而是由路由组件根据 fields 渲染子字段。
   */
  type: "string" | "select" | "number" | "integer" | "date" | "radio";

  /**
   * 是否根级必填。
   *
   * @description 来自 JSON Schema 顶层的 required 数组（backend 的 requiredFields）。
   * 注意：这仅仅是根级必填，不包含 items.required（见 itemsRequired）、
   * 也不包含 AJV 动态条件必填（见 useDynamicRequiredFields）。
   *
   * 领星使用 getDynamicRequiredFields() 做完整且准确的必填判断。
   */
  required: boolean;

  /** 最大字符长度（text 类字段）。 */
  maxLength?: number;

  /** 最小字符长度（text 类字段）。 */
  minLength?: number;

  /** 数值下限（number/integer 类字段）。 */
  minimum?: number;

  /** 数值上限（number/integer 类字段）。 */
  maximum?: number;

  /** 数值步进约束。 */
  multipleOf?: number;

  /**
   * select / radio 的选项列表。
   *
   * @description 由 enum + enumNames 构建。
   * 当 allowCreate 为 true 时，el-select 允许用户输入不在列表中的值。
   *
   * @example [{ name: "书籍", value: "BOOK" }, { name: "电子", value: "ELECTRONICS" }]
   */
  options?: { name: string; value: string }[];

  /**
   * 最大数组项数。
   *
   * @description 对应 JSON Schema 的 maxItems。
   * 当 maxUniqueItems > 1 时，该字段为多值字段，
   * 需要渲染 DynamicFieldList 或 DynamicFieldGroupList（带 add/remove 按钮）。
   *
   * 领星：maxUniqueItems 来自 `t.maxItems || 1`。
   */
  maxUniqueItems?: number;

  /** 最小数组项数（对应 JSON Schema 的 minItems）。 */
  minUniqueItems?: number;

  /**
   * 输入框占位提示文本。
   *
   * @description 格式为 "示例：xxx"，与领星一致。
   * xxx 来自 JSON Schema 的 examples 数组第一项。
   * 示例：`示例：Enter your product name` → label 下方灰色提示。
   */
  placeholder?: string;

  /**
   * select 是否允许自定义输入。
   *
   * @description 当 JSON Schema 使用 anyOf(enum) 时 allowCreate=true。
   * 对应 el-select 的 allow-create 属性。
   */
  allowCreate?: boolean;

  /**
   * 子字段配置映射（对象组字段专用）。
   *
   * @description key 为子字段 attrName，value 为子字段 ParsedFieldConfig。
   * 与领星 fieldConfig.fields 结构一致。
   *
   * 典型结构：
   * ```
   * item_package_dimensions: {
   *   attrName: "item_package_dimensions",
   *   label: ["包装尺寸", "Package Dimensions"],
   *   fields: {
   *     length: { attrName: "length", type: "number", ... },
   *     width:  { attrName: "width", type: "number", ... },
   *     height: { attrName: "height", type: "number", ... },
   *     unit:   { attrName: "unit", type: "select", options: [...], ... },
   *   },
   *   itemsRequired: ["length", "width", "height", "unit"],
   * }
   * ```
   *
   * 组字段的渲染流程：
   * 1. classifyAllFields() 检测到该字段有 fields 且数据含多子键
   * 2. 分类为 "multi" → 使用 DynamicFieldGroup 组件
   * 3. DynamicFieldGroup 遍历 fields 渲染每个子字段
   */
  fields?: Record<string, ParsedFieldConfig>;

  /**
   * items.required 记录的子字段必填名单。
   *
   * @description 仅组字段/数组字段有效，标记 items.properties 内哪些子字段必填。
   * 例如 item_package_dimensions 的 items.required = ["length", "width", "height", "unit"]。
   *
   * 注意：这不是 AJV 动态必填（见 useDynamicRequiredFields）。
   * itemsRequired 直接来自 schema 定义，不依赖表单当前值。
   */
  itemsRequired?: string[];
}

// ─────────────────────────────────────────────────────────────────────────────
// 字段分类硬编码清单
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 系统默认字段集合。
 *
 * @description 这些字段由后端自动填充（marketplace_id、language_tag），
 * 不在表单中渲染，不参与任何前端逻辑。
 *
 * 领星对应：defaultAssignFields = ["marketplace_id", "language_tag"]
 */
const SYSTEM_FIELD_NAMES = new Set(["marketplace_id", "language_tag"]);

/**
 * 基本信息字段清单。
 *
 * @description 对齐领星 basicFields。
 * 这些字段在其他区域（如"基本信息"卡片）中渲染，
 * 不在"更多属性"中重复显示。
 *
 * 领星 fieldClassification() 源码：
 * ```javascript
 * const basicFields = [
 *   "item_name", "generic_keyword", "brand",
 *   "item_package_dimensions", "item_package_weight",
 *   ...
 * ];
 * ```
 */
const BASIC_FIELD_NAMES = new Set([
  "item_name",
  "generic_keyword",
  "brand",
  "item_package_dimensions",
  "item_package_weight",
  "fulfillment_availability",
  "merchant_shipping_group",
  "recommended_browse_nodes",
  "item_type_keyword",
]);

/**
 * 报价/变体字段清单。
 *
 * @description 对齐领星 skuVariationFields。
 * 这些字段在报价/变体区域中渲染。
 */
const QUOTE_FIELD_NAMES = new Set([
  "item_sku",
  "parent_sku",
  "variation_theme",
  "externally_assigned_product_identifier",
  "condition_type",
  "condition_note",
  "purchasable_offer",
  "supplier_declared_has_product_identifier_exemption",
]);

/**
 * 图片字段清单。
 *
 * @description 对齐领星 imageFields。
 * 这些字段在图片区域中渲染。
 */
const IMAGE_FIELD_NAMES = new Set([
  "main_product_image_locator",
  "other_product_image_locator_1",
  "other_product_image_locator_2",
  "other_product_image_locator_3",
  "other_product_image_locator_4",
  "other_product_image_locator_5",
  "other_product_image_locator_6",
  "other_product_image_locator_7",
  "other_product_image_locator_8",
]);

/**
 * 描述字段清单。
 *
 * @description 对齐领星 descriptionFields。
 * 这些字段在描述区域中渲染。
 */
const DESC_FIELD_NAMES = new Set(["product_description", "bullet_point"]);

/**
 * 需过滤掉的字段清单。
 *
 * @description 对齐领星 filterValueFields + otherSpecialField。
 * 这些字段不在任何区域中渲染（后端自动处理或前端无用）。
 *
 * 领星 filterValueFields 会根据 sale_mall 动态变化：
 * ```javascript
 * filterValueFields() {
 *   return this.draftForm.sale_mall == 1
 *     ? ["main_offer_image_locator", ..., "parentage_level", "child_parent_sku_relationship"]
 *     : [... , "merchant_suggested_asin", "supplier_declared_has_product_identifier_exemption"];
 * }
 * ```
 * 这里我们使用固定集合（领星的基础集合）。
 */
const FILTER_VALUE_FIELDS = new Set([
  "main_offer_image_locator",
  "other_offer_image_locator_1",
  "other_offer_image_locator_2",
  "other_offer_image_locator_3",
  "other_offer_image_locator_4",
  "other_offer_image_locator_5",
  "parentage_level",
  "child_parent_sku_relationship",
  "swatch_product_image_locator",
]);

// ─────────────────────────────────────────────────────────────────────────────
// 内部工具函数
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 从 array 类型字段定义中递归提取 value 子字段定义。
 *
 * ============================================================
 * 背景：Amazon JSON Schema 的字段结构
 * ============================================================
 *
 * 几乎所有字段在最外层都是 array 类型：
 * ```
 * item_name: {
 *   type: "array",
 *   items: {
 *     type: "object",
 *     properties: {
 *       value: { type: "string", maxLength: 200, ... },      // ← 目标
 *       marketplace_id: { type: "string", const: "ATVPDKIKX0DER" },
 *     }
 *   }
 * }
 * ```
 *
 * 我们需要从这种包装结构中找到真正定义输入控件的子字段（value）。
 *
 * 特殊情况：部分字段嵌套更深，没有直接的 value 键：
 * ```
 * outer: {
 *   type: "array",
 *   items: {
 *     type: "object",
 *     properties: {
 *       material: {               // ← 非系统字段，递归进入
 *         type: "array",
 *         items: {
 *           type: "object",
 *           properties: {
 *             value: { type: "string", ... },  // ← 最终找到 value
 *             marketplace_id: { ... }
 *           }
 *         }
 *       }
 *     }
 *   }
 * }
 * ```
 *
 * 递归策略：
 * 1. 如果字段不是 array 或没有 items.properties → 返回自身（终止条件）
 * 2. 如果 properties 中有 value → 直接返回 value 定义
 * 3. 否则取第一个非系统字段，递归调用自身
 *
 * @param fieldDef - 原始字段定义（通常来自 fields 的 value，即 SchemaFieldDef）
 * @returns 最终可映射的叶子字段定义
 *
 * @see mapFieldType - 使用此函数的返回值做类型映射
 *
 * @example
 * ```typescript
 * const itemNameDef = { type: "array", items: { type: "object", properties: { value: { type: "string" }, marketplace_id: { ... } } } };
 * const valueDef = extractValueFieldDef(itemNameDef);
 * // valueDef = { type: "string" }  ← 提取成功
 * ```
 */
function extractValueFieldDef(fieldDef: SchemaFieldDef): SchemaFieldDef {
  if (fieldDef.type !== "array" || !fieldDef.items?.properties) return fieldDef;
  const subProps = fieldDef.items.properties;
  if (subProps.value) return subProps.value;
  for (const key of Object.keys(subProps)) {
    if (!SYSTEM_FIELD_NAMES.has(key)) return extractValueFieldDef(subProps[key]);
  }
  return fieldDef;
}

/**
 * 将 JSON Schema 字段定义映射为表单控件类型。
 *
 * ============================================================
 * 映射规则（对齐领星 getFormData 内层函数 l）
 * ============================================================
 *
 * 领星源码关键逻辑：
 * ```javascript
 * if (t.type === "string" && t.enum?.length) → type: "select", options: [...]
 * if (t.type === "string" && t.oneOf?.length) → type: "date"
 * if (t.type === "string" && t.anyOf?.length && anyOf 含 enum) → type: "select", allowCreate: true
 * if (t.type === "boolean") → type: "radio", options: [{ name: "是", value: "true" }, ...]
 * if (t.type === "number") → type: "number"
 * if (t.type === "integer") → type: "integer"
 * else → type: "string"
 * ```
 *
 * @param valueDef - value 子字段定义（已从 array.items.properties.value 提取）
 * @returns 映射结果：控件类型 + 选项列表 + 是否允许自定义输入
 *
 * @throws 不会抛出异常，无法匹配的类型默认返回 "string"
 *
 * @example
 * ```typescript
 * // 带枚举的字符串 → select
 * mapFieldType({ type: "string", enum: ["BOOK", "ELECTRONICS"], enumNames: ["书籍", "电子"] })
 * // → { type: "select", options: [{ name: "书籍", value: "BOOK" }, { name: "电子", value: "ELECTRONICS" }] }
 *
 * // 日期 → date
 * mapFieldType({ type: "string", oneOf: [{ format: "date" }] })
 * // → { type: "date" }
 * ```
 */
function mapFieldType(
  valueDef: SchemaFieldDef
): Pick<ParsedFieldConfig, "type" | "options" | "allowCreate"> {
  const t = valueDef.type;

  // string + enum → select 下拉框
  if (t === "string" && valueDef.enum?.length) {
    return {
      type: "select",
      options: valueDef.enum.map((v, i) => ({
        name: valueDef.enumNames?.[i] ?? String(v),
        value: String(v),
      })),
    };
  }

  // string + oneOf → 日期选择器
  // oneOf 通常用于日期格式约束
  if (t === "string" && valueDef.oneOf?.length) return { type: "date" };

  // string + anyOf(含 enum 分支) → 可自定义输入的 select
  // 领星：从 anyOf 中找出 enum 分支，用它的值做选项
  if (t === "string" && valueDef.anyOf?.length) {
    const enumBranch = valueDef.anyOf.find((b) => b.type === "string" && b.enum?.length);
    if (enumBranch?.enum) {
      return {
        type: "select",
        options: enumBranch.enum.map((v, i) => ({
          name: enumBranch.enumNames?.[i] ?? String(v),
          value: String(v),
        })),
        allowCreate: true,
      };
    }
  }

  // boolean → 是/否 单选
  if (t === "boolean") {
    return {
      type: "radio",
      options: [
        { name: "是", value: "true" },
        { name: "否", value: "false" },
      ],
    };
  }

  // number / integer → 数字输入
  if (t === "number") return { type: "number" };
  if (t === "integer") return { type: "integer" };

  // 兜底：string 文本输入
  return { type: "string" };
}

/**
 * 判断字段是否为对象组类型。
 *
 * ============================================================
 * 判断逻辑
 * ============================================================
 *
 * 当一个字段满足以下条件时，判定为对象组：
 * 1. 类型为 "array"
 * 2. 含有 items.properties
 * 3. 去除 marketplace_id / language_tag 后，子字段数 > 1
 *
 * 例如：
 * ```
 * item_package_dimensions: {
 *   type: "array",
 *   items: {
 *     type: "object",
 *     properties: {
 *       length: { type: "number", ... },  // ← 非系统字段
 *       width:  { type: "number", ... },  // ← 非系统字段
 *       height: { type: "number", ... },  // ← 非系统字段
 *       unit:   { type: "string", ... },  // ← 非系统字段
 *       marketplace_id: { type: "string", ... },  // ← 系统字段，忽略
 *     }
 *   }
 * }
 * // subKeys = ["length", "width", "height", "unit"] → 4 > 1 → true
 * ```
 *
 * 而 item_name 只有一个 value 非系统字段，不会被判定为组：
 * ```
 * item_name: {
 *   type: "array",
 *   items: { properties: { value: {...}, marketplace_id: {...} } }
 * }
 * // subKeys = ["value"] → 1 <= 1 → false
 * ```
 *
 * @param fieldDef - 原始字段定义
 * @returns true 表示是对象组，需要递归处理子字段
 */
function isGroupField(fieldDef: SchemaFieldDef): boolean {
  if (fieldDef.type !== "array" || !fieldDef.items?.properties) return false;
  const subKeys = Object.keys(fieldDef.items.properties).filter((k) => !SYSTEM_FIELD_NAMES.has(k));
  return subKeys.length > 1;
}

// ─────────────────────────────────────────────────────────────────────────────
// 核心解析函数
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 解析单个字段为 ParsedFieldConfig。
 *
 * ============================================================
 * 处理流程（对齐领星内层函数 l）
 * ============================================================
 *
 * 对于每个字段：
 * 1. 过滤系统字段（SYSTEM_FIELD_NAMES）和过滤字段（FILTER_VALUE_FIELDS）→ 返回 null
 * 2. 提取双语标签和描述（优先取 zhDef/siteDef 的 title/description）
 * 3. 判断是否为组字段：
 *    a. 是组字段 → 递归解析子字段，返回带 fields 的配置
 *    b. 是普通字段 → 提取 valueDef → 映射控件类型 → 返回叶子配置
 * 4. 判断必填（从 requiredFields Set 中查找）
 * 5. 提取 placeholder（"示例：xxx" 格式）
 * 6. 提取验证约束（maxLength, minLength, minimum, maximum, multipleOf）
 *
 * @param attrName - 字段名
 * @param siteDef - 站点语言字段定义
 * @param zhDef - 中文字段定义（无对应定义时为 undefined）
 * @param requiredFields - 根级必填字段名集合
 * @returns 解析后的字段配置，若字段应跳过则返回 null
 *
 * @see parseAllFields - 遍历全部字段调用此函数
 * @see parseSubFields - 组字段内部递归调用此函数
 */
function parseField(
  attrName: string,
  siteDef: SchemaFieldDef,
  zhDef: SchemaFieldDef | undefined,
  requiredFields: Set<string>
): ParsedFieldConfig | null {
  // 第 1 步：过滤不需要渲染的字段
  if (SYSTEM_FIELD_NAMES.has(attrName) || FILTER_VALUE_FIELDS.has(attrName)) return null;

  // 第 2 步：组字段处理（外层 title/description）
  if (isGroupField(siteDef)) {
    const zhTitle = zhDef?.title ?? attrName;
    const siteTitle = siteDef.title ?? attrName;
    const zhDesc = zhDef?.description ?? "";
    const siteDesc = siteDef.description ?? "";
    const fields = parseSubFields(siteDef, zhDef);
    if (!fields || Object.keys(fields).length === 0) return null;
    return {
      attrName,
      label: [zhTitle, siteTitle],
      description: [zhDesc, siteDesc],
      type: "string",
      required: false,
      fields,
      itemsRequired: siteDef.items?.required,
    };
  }

  // 第 3 步：提取 value 子字段定义（叶子字段）
  const valueSiteDef = extractValueFieldDef(siteDef);
  if (valueSiteDef.hidden === true) return null;

  // 对齐领星 DynamicFormItem：叶子字段 label/description 取自 items.properties.value
  // 例：merchant_suggested_asin 外层 title=错误自动生成，valueDef.title=正确中文
  const valueZhDef = zhDef ? extractValueFieldDef(zhDef) : undefined;
  const zhTitle = valueZhDef?.title || zhDef?.title || attrName;
  const siteTitle = valueSiteDef?.title || siteDef.title || attrName;
  const zhDesc = valueZhDef?.description || zhDef?.description || "";
  const siteDesc = valueSiteDef?.description || siteDef.description || "";

  // 第 4 步：映射控件类型
  const { type, options, allowCreate } = mapFieldType(valueSiteDef);

  // 第 5 步：判断必填（根级 required）
  const required = requiredFields.has(attrName);

  // 第 6 步：提取 placeholder
  const example = siteDef.examples?.[0] ?? valueSiteDef.examples?.[0] ?? "";
  const placeholder = example ? `示例：${example}` : "";

  // 第 7 步：返回完整配置
  return {
    attrName,
    label: [zhTitle, siteTitle],
    description: [zhDesc, siteDesc],
    type,
    required,
    maxLength: valueSiteDef.maxLength || valueSiteDef.maxUtf8ByteLength || undefined,
    minLength: valueSiteDef.minLength || undefined,
    minimum: valueSiteDef.minimum,
    maximum: valueSiteDef.maximum,
    multipleOf: valueSiteDef.multipleOf,
    options,
    maxUniqueItems: siteDef.maxItems,
    minUniqueItems: siteDef.minItems,
    placeholder,
    allowCreate,
    itemsRequired: siteDef.items?.required,
  };
}

/**
 * 解析对象组字段的子字段映射。
 *
 * ============================================================
 * 处理流程
 * ============================================================
 *
 * 对于组字段的每个子字段（items.properties 的 entry）：
 * 1. 过滤系统字段（marketplace_id, language_tag）
 * 2. 提取 value 子定义，跳过 hidden 字段
 * 3. 映射控件类型
 * 4. 提取双语标签
 * 5. 判断 items.required 包含性
 * 6. 提取 placeholder
 * 7. 返回 attrName → ParsedFieldConfig 映射
 *
 * @param siteDef - 站点语言组字段定义（必须含 items.properties）
 * @param zhDef - 中文组字段定义（可能为空）
 * @returns 子字段名到配置的映射
 *
 * @example
 * ```typescript
 * const siteDef = {
 *   type: "array",
 *   items: {
 *     required: ["length", "width", "height", "unit"],
 *     properties: {
 *       length: { type: "number", title: "Length" },
 *       width: { type: "number", title: "Width" },
 *       height: { type: "number", title: "Height" },
 *       unit: { type: "string", title: "Unit", enum: ["inches", "centimeters"] },
 *     }
 *   }
 * };
 * const zhDef = { items: { properties: { length: { title: "长度" }, ... } } };
 * parseSubFields(siteDef, zhDef);
 * // → {
 * //   length: { attrName: "length", type: "number", label: ["长度", "Length"], required: true },
 * //   width:  { attrName: "width", type: "number", label: ["宽度", "Width"], required: true },
 * //   height: { attrName: "height", type: "number", label: ["高度", "Height"], required: true },
 * //   unit:   { attrName: "unit", type: "select", label: ["单位", "Unit"], required: true, options: [...] },
 * // }
 * ```
 */
function parseSubFields(
  siteDef: SchemaFieldDef,
  zhDef: SchemaFieldDef | undefined
): Record<string, ParsedFieldConfig> {
  if (!siteDef.items?.properties) return {};
  const result: Record<string, ParsedFieldConfig> = {};
  const zhSubProps = zhDef?.items?.properties ?? {};

  for (const [subKey, subDef] of Object.entries(siteDef.items.properties)) {
    // 跳过系统字段
    if (SYSTEM_FIELD_NAMES.has(subKey)) continue;

    // 提取 value 定义
    const valueDef = extractValueFieldDef(subDef);
    if (valueDef.hidden === true) continue;

    // 映射控件类型
    const { type, options, allowCreate } = mapFieldType(valueDef);

    // 提取标签
    const zhSubDef = zhSubProps[subKey] as SchemaFieldDef | undefined;
    const subZhTitle = zhSubDef?.title ?? subKey;
    const subSiteTitle = subDef.title ?? subKey;

    // 判断必填（items.required 包含该子字段名）
    const subRequired = siteDef.items?.required?.includes(subKey) ?? false;

    // 提取 placeholder
    const subExample = subDef.examples?.[0] ?? valueDef.examples?.[0] ?? "";
    const placeholder = subExample ? `示例：${subExample}` : "";

    result[subKey] = {
      attrName: subKey,
      label: [subZhTitle, subSiteTitle],
      description: ["", ""],
      type,
      required: subRequired,
      maxLength: valueDef.maxLength === 0 ? undefined : valueDef.maxLength,
      minLength: valueDef.minLength || undefined,
      minimum: valueDef.minimum,
      maximum: valueDef.maximum,
      multipleOf: valueDef.multipleOf,
      options,
      placeholder,
      allowCreate,
    };
  }
  return result;
}

/**
 * 遍历 fields + fieldsZh，解析全部字段并分类。
 *
 * @description 作为 parseField 的调度入口，遍历 ProductTypeSchemaVO 中所有字段，
 * 调用 parseField 逐个解析，收集非 null 结果。
 *
 * @param schema - 后端返回的 Schema 数据（ProductTypeSchemaVO）
 * @returns 所有解析后的字段配置数组
 *
 * @example
 * ```typescript
 * const parsed = parseAllFields(schema);
 * // parsed 是 Array<ParsedFieldConfig>，包含所有非跳过字段
 * ```
 */
function parseAllFields(schema: ProductTypeSchemaVO): ParsedFieldConfig[] {
  const requiredFields = new Set(schema.requiredFields);
  const { fields, fieldsZh } = schema;
  const result: ParsedFieldConfig[] = [];
  for (const [attrName, siteDef] of Object.entries(fields)) {
    const zhDef = fieldsZh[attrName];
    const parsed = parseField(attrName, siteDef, zhDef, requiredFields);
    if (parsed) result.push(parsed);
  }
  return result;
}

// ─────────────────────────────────────────────────────────────────────────────
// 导出函数
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 字段分类：将解析后的字段分配到 6 个类别。
 *
 * ============================================================
 * 分类清单（对齐领星 fieldClassification）
 * ============================================================
 *
 * | 分类 | 对应清单 | 渲染区域 |
 * |------|---------|---------|
 * | basicFields | BASIC_FIELD_NAMES | 基本信息 section |
 * | quoteFields | QUOTE_FIELD_NAMES | 报价/变体 section |
 * | imageFields | IMAGE_FIELD_NAMES | 图片 section |
 * | descFields  | DESC_FIELD_NAMES  | 描述 section |
 * | otherFields | 以上未匹配 | 更多属性 section |
 *
 * 领星 fieldClassification() 源码对照：
 * ```javascript
 * function fieldClassification(fields) {
 *   const result = [{},{},{},{},{}];
 *   for (const [key, field] of Object.entries(fields)) {
 *     if ((basicFields).indexOf(key) > -1) result[0][key] = field;
 *     else if ((skuVariationFields).indexOf(key) > -1) result[1][key] = field;
 *     else if ((imageFields).indexOf(key) > -1) result[2][key] = field;
 *     else if ((descriptionFields).indexOf(key) > -1) result[3][key] = field;
 *     else result[4][key] = field;
 *   }
 *   return result;
 * }
 * ```
 *
 * @param allFields - 全部解析后的字段
 * @returns 分类后的 5 个字段数组
 *
 * @example
 * ```typescript
 * const { basicFields, otherFields } = classifyFields(parsed);
 * // otherFields → 供"更多属性" section 动态渲染
 * ```
 */
export function classifyFields(allFields: ParsedFieldConfig[]) {
  const basicFields: ParsedFieldConfig[] = [];
  const quoteFields: ParsedFieldConfig[] = [];
  const imageFields: ParsedFieldConfig[] = [];
  const descFields: ParsedFieldConfig[] = [];
  const otherFields: ParsedFieldConfig[] = [];
  for (const field of allFields) {
    if (BASIC_FIELD_NAMES.has(field.attrName)) basicFields.push(field);
    else if (QUOTE_FIELD_NAMES.has(field.attrName)) quoteFields.push(field);
    else if (IMAGE_FIELD_NAMES.has(field.attrName)) imageFields.push(field);
    else if (DESC_FIELD_NAMES.has(field.attrName)) descFields.push(field);
    else otherFields.push(field);
  }
  return { basicFields, quoteFields, imageFields, descFields, otherFields };
}

/**
 * 创建字段的初始嵌套表单值。
 *
 * @description 对齐领星 recursiveProcessDynamicForm 的初始化逻辑，
 * 但子字段值使用 { value, marketplace_id } 包装（匹配 DynamicField* 子组件的读取方式）。
 *
 * - 叶子字段（无 fields）：`[{ value: "", marketplace_id: "xxx" }]`
 * - 组字段（有 fields）：`[{ subKey1: { value: "", marketplace_id: "xxx" }, ..., marketplace_id: "xxx" }]`
 *
 * @param field - 解析后的字段配置
 * @param marketplaceId - 市场 ID
 * @returns 嵌套数组格式的初始值
 */
export function createFieldDefaultValue(
  field: ParsedFieldConfig,
  marketplaceId: string
): unknown[] {
  if (!field.fields) {
    // 叶子字段
    return [{ value: "", marketplace_id: marketplaceId }];
  }
  // 组字段：每个子字段初始化为 { value: "", marketplace_id }
  const item: Record<string, unknown> = { marketplace_id: marketplaceId };
  for (const [subKey, subConfig] of Object.entries(field.fields)) {
    if (SYSTEM_FIELD_NAMES.has(subKey)) {
      item[subKey] = marketplaceId;
    } else if (subConfig.fields) {
      // 嵌套更深层的组字段（罕见），递归处理
      item[subKey] = (createFieldDefaultValue(subConfig, marketplaceId) as unknown[])[0];
    } else {
      item[subKey] = { value: "", marketplace_id: marketplaceId };
    }
  }
  return [item];
}

/**
 * 提取字段的搜索关键词。
 *
 * @description 用于搜索框过滤，返回字段名 + 双语标签 + 子字段关键词的大写数组。
 * 组字段递归包含子字段的关键词。
 *
 * @param field - 解析后的字段配置
 * @returns 大写关键词数组
 *
 * @example
 * ```typescript
 * flattenFieldLabels({
 *   attrName: "item_name",
 *   label: ["商品名称", "Item Name"],
 *   fields: undefined,
 * });
 * // → ["ITEM_NAME", "商品名称", "ITEM NAME"]
 *
 * flattenFieldLabels({
 *   attrName: "item_dimensions",
 *   label: ["尺寸", "Dimensions"],
 *   fields: {
 *     length: { attrName: "length", label: ["长度", "Length"] },
 *     width:  { attrName: "width", label: ["宽度", "Width"] },
 *   }
 * });
 * // → ["ITEM_DIMENSIONS", "尺寸", "DIMENSIONS", "LENGTH", "长度", "WIDTH", "宽度"]
 * ```
 */
export function flattenFieldLabels(field: ParsedFieldConfig): string[] {
  const result: string[] = [field.attrName.toUpperCase()];
  if (field.label[0]) result.push(field.label[0].toUpperCase());
  if (field.label[1]) result.push(field.label[1].toUpperCase());
  if (field.fields) {
    for (const sf of Object.values(field.fields)) {
      result.push(sf.attrName.toUpperCase());
      if (sf.label[0]) result.push(sf.label[0].toUpperCase());
      if (sf.label[1]) result.push(sf.label[1].toUpperCase());
    }
  }
  return result;
}

// ─────────────────────────────────────────────────────────────────────────────
// Composable
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 商品类型 Schema 解析 composable。
 *
 * ============================================================
 * 职责与数据流
 * ============================================================
 *
 * 1. 监听 marketplaceId 和 productTypeOrigin（两者都必须有值）
 * 2. 调用 ListingPublishAPI.getProductTypeSchema() 拉取 Schema
 * 3. 解析 Schema 为 ParsedFieldConfig[]（parseAllFields）
 * 4. 分类字段（classifyFields），提取 otherFields
 * 5. 构建 dynamicDescInfo 映射（key=attrName → ParsedFieldConfig）
 * 6. 初始化 dynamicFormData（site/cn 双栏，每项为 [{value: "", marketplace_id: "..."}]）
 *
 * ============================================================
 * 响应式设计
 * ============================================================
 *
 * - marketplaceId / productTypeOrigin 使用 MaybeRefOrGetter 模式，
 *   可传入 ref、computed 或普通字符串
 * - watch 自动监听两者变化，变化时重新拉取 schema
 * - dynamicFormData 使用 reactive，字段值直接绑定到表单控件
 *
 * ============================================================
 * 返回数据格式
 * ============================================================
 *
 * dynamicFormData.site / dynamicFormData.cn — 双栏表单数据
 * 格式：{ [attrName]: Array<{ value: string, marketplace_id?: string }> }
 *
 * 匹配领星 formData 结构：
 * ```javascript
 * // 简单字段
 * draftForm.item_name = [{ value: "商品名", marketplace_id: "ATVPDKIKX0DER" }]
 *
 * // 组字段
 * draftForm.item_dimensions = [{
 *   length: { value: 10 },
 *   width: { value: 8 },
 *   height: { value: 2 },
 *   unit: { value: "inches" },
 *   marketplace_id: "ATVPDKIKX0DER"
 * }]
 *
 * // 多值字段
 * draftForm.language = [
 *   { value: "chi", marketplace_id: "ATVPDKIKX0DER" },
 *   { value: "eng", marketplace_id: "ATVPDKIKX0DER" },
 * ]
 * ```
 *
 * @param marketplaceId - 市场 ID（响应式或 getter）
 *   可传 ref、computed、普通字符串。
 *   例：`ref("ATVPDKIKX0DER")` 或 `() => form.marketplaceId`
 *
 * @param productTypeOrigin - 商品类型标识（响应式或 getter）
 *   可传 ref、computed、普通字符串。
 *   例：`ref("ABIS_BOOK")` 或 `() => form.productType`
 *
 * @returns 解析状态与数据
 *
 * @example
 * ```typescript
 * // 模板编辑器使用（单栏）
 * const { loading, otherFields, dynamicDescInfo } = useProductTypeSchema(
 *   () => form.marketplaceId,
 *   () => form.productType
 * );
 *
 * // 草稿编辑器使用（双栏 site/cn）
 * const { dynamicFormData } = useProductTypeSchema(
 *   () => f?.site?.marketplaceId ?? "",
 *   () => f?.site?.productType ?? ""
 * );
 * ```
 */
export function useProductTypeSchema(
  marketplaceId: MaybeRefOrGetter<string>,
  productTypeOrigin: MaybeRefOrGetter<string>
) {
  /**
   * Schema 加载状态。
   *
   * @description true 时表示正在请求后端 API。
   * 页面可用 v-loading 绑定此变量。
   */
  const loading = ref(false);

  /**
   * 错误信息。
   *
   * @description Schema 请求失败时的错误描述。
   */
  const error = ref("");

  /**
   * 全部分析后的字段配置。
   *
   * @description 包含所有非跳过字段（包括 basic、quote、image、desc、other）。
   * 供需要全局字段信息的场景使用。
   */
  const allFields = ref<ParsedFieldConfig[]>([]) as Ref<ParsedFieldConfig[]>;

  /**
   * other 类别的字段配置。
   *
   * @description 仅包含未匹配任何分类清单的字段。
   * 由"更多属性" section 消费。
   */
  const otherFields = ref<ParsedFieldConfig[]>([]) as Ref<ParsedFieldConfig[]>;

  /**
   * 后端返回的原始 Schema 数据。
   *
   * @description 保留完整数据，供其他 composable 使用
   * （如 useDynamicRequiredFields 需要原始 JSON Schema）。
   */
  const schemaData = ref<ProductTypeSchemaVO | null>(null);

  /**
   * 字段配置映射（attrName → ParsedFieldConfig）。
   *
   * @description 对齐领星 dynamicDescInfo。
   * 用于字段分类（useFieldClassification）时快速查找字段配置。
   * O(1) 访问，避免数组遍历。
   */
  const dynamicDescInfo = ref<Record<string, ParsedFieldConfig>>({});

  /**
   * 默认字段值。
   *
   * @description 包含 marketplace_id / language_tag 等系统字段的默认值。
   * 来自 Schema 的 $defs。
   */
  const defaultFields = ref<Record<string, string>>({});

  /**
   * 动态表单数据。
   *
   * @description 响应式对象，key=attrName，value=灵星兼容的嵌套数组格式。
   * site → 站点语言列，cn → 中文内容列。
   * 每项初始化为 [{ value: "", marketplace_id: "xxx" }]。
   *
   * 初始化逻辑：当 defaultFields.marketplace_id 存在时，自动填充到每项的 marketplace_id。
   */
  const dynamicFormData = reactive({
    site: {} as Record<string, any[]>,
    cn: {} as Record<string, any[]>,
  });

  /**
   * 拉取并解析 Schema。
   *
   * @description 核心数据加载函数。
   * 1. 调用 API 获取 Schema
   * 2. 解析全部字段
   * 3. 分类提取 otherFields
   * 4. 构建 dynamicDescInfo 映射
   * 5. 初始化表单数据（嵌套数组格式，匹配灵星）
   *
   * @param mpId - 市场 ID
   * @param ptOrigin - 商品类型标识
   */
  async function fetchSchema(mpId: string, ptOrigin: string) {
    if (!mpId || !ptOrigin) return;
    loading.value = true;
    error.value = "";
    try {
      const data = await ListingPublishAPI.getProductTypeSchema({
        marketplaceId: mpId,
        productTypeOrigin: ptOrigin,
      });
      schemaData.value = data;
      defaultFields.value = data.defaultFields;

      // 解析（嵌套结构，不展平）
      const parsed = parseAllFields(data);
      allFields.value = parsed;

      // 分类（对齐领星 fieldClassification）
      const classified = classifyFields(parsed);
      otherFields.value = classified.otherFields;

      // 构建 dynamicDescInfo 映射
      const descInfo: Record<string, ParsedFieldConfig> = {};
      for (const field of parsed) descInfo[field.attrName] = field;
      dynamicDescInfo.value = descInfo;

      // 初始化表单数据（嵌套数组格式，对齐领星 recursiveProcessDynamicForm）
      const marketplaceId = data.defaultFields.marketplace_id ?? "";
      const siteData: Record<string, unknown[]> = {};
      const cnData: Record<string, unknown[]> = {};
      for (const field of classified.otherFields) {
        const initVal = createFieldDefaultValue(field, marketplaceId);
        siteData[field.attrName] = JSON.parse(JSON.stringify(initVal));
        cnData[field.attrName] = JSON.parse(JSON.stringify(initVal));
      }
      dynamicFormData.site = siteData;
      dynamicFormData.cn = cnData;
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : "Schema 加载失败";
      otherFields.value = [];
    } finally {
      loading.value = false;
    }
  }

  // 监听输入变化，自动拉取
  watch(
    [() => toValue(marketplaceId), () => toValue(productTypeOrigin)],
    ([mpId, ptOrigin]) => {
      if (mpId && ptOrigin) fetchSchema(mpId, ptOrigin);
      else {
        otherFields.value = [];
        dynamicFormData.site = {} as Record<string, any[]>;
        dynamicFormData.cn = {} as Record<string, any[]>;
      }
    },
    { immediate: true }
  );

  return {
    loading,
    error,
    allFields,
    otherFields,
    dynamicFormData,
    dynamicDescInfo,
    defaultFields,
    schemaData,
    fetchSchema,
  };
}
