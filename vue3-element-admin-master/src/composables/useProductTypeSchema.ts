/**
 * 商品类型 JSON Schema 解析 composable。
 *
 * 仿写领星 parse_json_mixins.js 的 getFormData() 逻辑：
 * 1. 调用后端 API 获取 Schema（后端已预处理，返回 fields / fieldsZh / requiredFields）
 * 2. 遍历 fields，将 JSON Schema 字段定义翻译为 ParsedFieldConfig
 * 3. fieldClassification() 按字段名硬编码清单分类，未匹配的字段归入 otherFields
 * 4. otherFields 供"更多属性" section 动态渲染
 *
 * 类型映射规则（来自领星 getFormData 内层函数 l）：
 * - string + enum      -> select（options 从 enum/enumNames 构建）
 * - string + oneOf     -> date
 * - string + anyOf(enum) -> select（allowCreate = true）
 * - string             -> string
 * - number             -> number（含 minimum / maximum / multipleOf）
 * - integer            -> integer
 * - boolean            -> radio
 */
import { ref, reactive, watch, toValue } from "vue";
import type { Ref, MaybeRefOrGetter } from "vue";
import { ListingPublishAPI } from "@/api/sales/listing-publish";
import type { SchemaFieldDef, ProductTypeSchemaVO } from "@/api/sales/listing-publish/types";

// ── 类型定义 ──────────────────────────────────────────────────────────────────

/** 解析后的表单字段配置。 */
export interface ParsedFieldConfig {
  /** 字段名（如 item_name、style）。 */
  attrName: string;
  /** 标签 [中文, 站点语言]。 */
  label: [string, string];
  /** 描述 [中文, 站点语言]。 */
  description: [string, string];
  /** 表单控件类型。 */
  fieldType: "string" | "select" | "number" | "integer" | "date" | "radio" | "group";
  /** 是否必填。 */
  required: boolean;
  /** 最大长度。 */
  maxLength?: number;
  /** 最小长度。 */
  minLength?: number;
  /** 数值下限。 */
  minimum?: number;
  /** 数值上限。 */
  maximum?: number;
  /** 数值步进。 */
  multipleOf?: number;
  /** select / radio 的选项列表。 */
  options?: { name: string; value: string }[];
  /** 最大数组项数。 */
  maxUniqueItems?: number;
  /** 最小数组项数。 */
  minUniqueItems?: number;
  /** placeholder 文本。 */
  placeholder?: string;
  /** select 是否允许自定义输入。 */
  allowCreate?: boolean;
  /** 如果是组字段，子字段列表。 */
  subFields?: ParsedFieldConfig[];
}

// ── 字段分类硬编码清单（仿领星 fieldClassification）────────────────────────────

/** 基本信息字段（对齐领星 basicFields）。 */
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

/** 报价/变体字段（对齐领星 skuVariationFields）。 */
const QUOTE_FIELD_NAMES = new Set([
  "variation_theme",
  "externally_assigned_product_identifier",
  "condition_type",
  "condition_note",
  "purchasable_offer",
  "supplier_declared_has_product_identifier_exemption",
]);

/** 图片字段。 */
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

/** 描述字段。 */
const DESC_FIELD_NAMES = new Set(["product_description", "bullet_point"]);

/** 系统默认字段（自动赋值，不在表单中渲染）。 */
const SYSTEM_FIELD_NAMES = new Set(["marketplace_id", "language_tag"]);

/** 需过滤掉的字段（领星 filterValueFields + otherSpecialField）。 */
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

// ── 核心解析逻辑 ──────────────────────────────────────────────────────────────

/**
 * 从 array 类型字段定义中递归提取 value 子字段定义。
 *
 * Amazon Schema 中大部分字段结构为：
 * { type: "array", items: { type: "object", properties: { value: {...}, marketplace_id: {...} } } }
 * 此函数优先提取 items.properties.value。
 *
 * 部分嵌套字段没有 value 键（如 outer -> material），
 * 此时取第一个非系统子字段并递归提取，直到遇到非数组类型或找到 value。
 *
 * @param fieldDef - 原始字段定义。
 * @returns 最终可映射的叶子字段定义。
 */
function extractValueFieldDef(fieldDef: SchemaFieldDef): SchemaFieldDef {
  if (fieldDef.type !== "array" || !fieldDef.items?.properties) {
    return fieldDef;
  }
  const subProps = fieldDef.items.properties;
  if (subProps.value) {
    return subProps.value;
  }
  // 无 value 键时取第一个非系统子字段，递归提取（如 outer -> material -> value）
  for (const key of Object.keys(subProps)) {
    if (!SYSTEM_FIELD_NAMES.has(key)) {
      return extractValueFieldDef(subProps[key]);
    }
  }
  return fieldDef;
}

/**
 * 判断字段是否为对象组类型（如 dimensions 含 length/width/height）。
 *
 * @param fieldDef - 原始字段定义。
 * @returns true 表示是对象组，需要递归处理。
 */
function isGroupField(fieldDef: SchemaFieldDef): boolean {
  if (fieldDef.type !== "array" || !fieldDef.items?.properties) return false;
  const subKeys = Object.keys(fieldDef.items.properties).filter((k) => !SYSTEM_FIELD_NAMES.has(k));
  return subKeys.length > 1;
}

/**
 * 将 JSON Schema 字段定义映射为表单控件类型。
 *
 * @param valueDef - value 子字段定义（已从 array.items.properties.value 提取）。
 * @returns fieldType + options + allowCreate。
 */
function mapFieldType(
  valueDef: SchemaFieldDef
): Pick<ParsedFieldConfig, "fieldType" | "options" | "allowCreate"> {
  const t = valueDef.type;

  // string + enum -> select
  if (t === "string" && valueDef.enum?.length) {
    return {
      fieldType: "select",
      options: valueDef.enum.map((v, i) => ({
        name: valueDef.enumNames?.[i] ?? String(v),
        value: String(v),
      })),
    };
  }

  // string + oneOf -> date
  if (t === "string" && valueDef.oneOf?.length) {
    return { fieldType: "date" };
  }

  // string + anyOf(enum) -> select (allowCreate)
  if (t === "string" && valueDef.anyOf?.length) {
    const enumBranch = valueDef.anyOf.find((b) => b.type === "string" && b.enum?.length);
    if (enumBranch?.enum) {
      return {
        fieldType: "select",
        options: enumBranch.enum.map((v, i) => ({
          name: enumBranch.enumNames?.[i] ?? String(v),
          value: String(v),
        })),
        allowCreate: true,
      };
    }
  }

  // boolean -> radio
  if (t === "boolean") {
    return {
      fieldType: "radio",
      options: [
        { name: "是", value: "true" },
        { name: "否", value: "false" },
      ],
    };
  }

  // number / integer
  if (t === "number") return { fieldType: "number" };
  if (t === "integer") return { fieldType: "integer" };

  // default: string
  return { fieldType: "string" };
}

/**
 * 解析单个字段为 ParsedFieldConfig。
 *
 * @param attrName - 字段名。
 * @param siteDef - 站点语言字段定义。
 * @param zhDef - 中文字段定义。
 * @param requiredFields - 根级必填字段名集合。
 * @returns 解析后的字段配置，若字段应跳过则返回 null。
 */
function parseField(
  attrName: string,
  siteDef: SchemaFieldDef,
  zhDef: SchemaFieldDef | undefined,
  requiredFields: Set<string>
): ParsedFieldConfig | null {
  if (SYSTEM_FIELD_NAMES.has(attrName) || FILTER_VALUE_FIELDS.has(attrName)) {
    return null;
  }

  // 提取标签和描述（组字段和普通字段共用）
  const zhTitle = zhDef?.title ?? attrName;
  const siteTitle = siteDef.title ?? attrName;
  const zhDesc = zhDef?.description ?? "";
  const siteDesc = siteDef.description ?? "";

  // 对象组字段：递归解析子字段
  if (isGroupField(siteDef)) {
    const subFields = parseSubFields(siteDef, zhDef);
    if (subFields.length === 0) return null;
    // 组的必填状态：任一子字段必填
    const groupRequired = subFields.some((f) => f.required);
    return {
      attrName,
      label: [zhTitle, siteTitle],
      description: [zhDesc, siteDesc],
      fieldType: "group",
      required: groupRequired,
      subFields,
    };
  }

  // hidden 字段跳过
  const valueDef = extractValueFieldDef(siteDef);
  if (valueDef.hidden === true) return null;

  // 映射类型
  const { fieldType, options, allowCreate } = mapFieldType(valueDef);

  // 判断必填：只看根级 required 数组
  const required = requiredFields.has(attrName);

  // placeholder
  const placeholder = siteDef.examples?.[0] ?? valueDef.examples?.[0] ?? "";

  return {
    attrName,
    label: [zhTitle, siteTitle],
    description: [zhDesc, siteDesc],
    fieldType,
    required,
    maxLength: valueDef.maxLength === 0 ? undefined : valueDef.maxLength,
    minLength: valueDef.minLength || undefined,
    minimum: valueDef.minimum,
    maximum: valueDef.maximum,
    multipleOf: valueDef.multipleOf,
    options,
    maxUniqueItems: siteDef.maxUniqueItems,
    minUniqueItems: siteDef.minUniqueItems,
    placeholder,
    allowCreate,
  };
}

/**
 * 解析对象组字段的子字段列表。
 *
 * 对于 items.properties 含多个非系统子字段的字段（如 item_dimensions），
 * 遍历每个子字段递归提取 value 定义，构建 ParsedFieldConfig 数组。
 *
 * @param siteDef - 站点语言组字段定义。
 * @param zhDef - 中文组字段定义。
 * @returns 子字段配置数组。
 */
function parseSubFields(
  siteDef: SchemaFieldDef,
  zhDef: SchemaFieldDef | undefined
): ParsedFieldConfig[] {
  if (!siteDef.items?.properties) return [];
  const result: ParsedFieldConfig[] = [];
  const zhSubProps = zhDef?.items?.properties ?? {};

  for (const [subKey, subDef] of Object.entries(siteDef.items.properties)) {
    if (SYSTEM_FIELD_NAMES.has(subKey)) continue;

    const valueDef = extractValueFieldDef(subDef);
    if (valueDef.hidden === true) continue;

    const { fieldType, options, allowCreate } = mapFieldType(valueDef);
    const zhSubDef = zhSubProps[subKey] as SchemaFieldDef | undefined;
    const subZhTitle = zhSubDef?.title ?? subKey;
    const subSiteTitle = subDef.title ?? subKey;

    // 子字段必填：items.required 包含该子字段名
    const subRequired = siteDef.items?.required?.includes(subKey) ?? false;

    const placeholder = subDef.examples?.[0] ?? valueDef.examples?.[0] ?? "";

    result.push({
      attrName: subKey,
      label: [subZhTitle, subSiteTitle],
      description: ["", ""],
      fieldType,
      required: subRequired,
      maxLength: valueDef.maxLength === 0 ? undefined : valueDef.maxLength,
      minLength: valueDef.minLength || undefined,
      minimum: valueDef.minimum,
      maximum: valueDef.maximum,
      multipleOf: valueDef.multipleOf,
      options,
      placeholder,
      allowCreate,
    });
  }
  return result;
}

/**
 * 遍历 fields + fieldsZh，解析全部字段并分类。
 *
 * @param schema - 后端返回的 Schema 数据。
 * @returns 所有解析后的字段配置数组。
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

/**
 * 字段分类：将解析后的字段分配到 6 个类别。
 *
 * 仿领星 fieldClassification()，未匹配任何清单的字段归入 otherFields。
 *
 * @param allFields - 全部解析后的字段。
 * @returns 分类后的字段对象。
 */
export function classifyFields(allFields: ParsedFieldConfig[]) {
  const basicFields: ParsedFieldConfig[] = [];
  const quoteFields: ParsedFieldConfig[] = [];
  const imageFields: ParsedFieldConfig[] = [];
  const descFields: ParsedFieldConfig[] = [];
  const otherFields: ParsedFieldConfig[] = [];

  for (const field of allFields) {
    if (BASIC_FIELD_NAMES.has(field.attrName)) {
      basicFields.push(field);
    } else if (QUOTE_FIELD_NAMES.has(field.attrName)) {
      quoteFields.push(field);
    } else if (IMAGE_FIELD_NAMES.has(field.attrName)) {
      imageFields.push(field);
    } else if (DESC_FIELD_NAMES.has(field.attrName)) {
      descFields.push(field);
    } else {
      otherFields.push(field);
    }
  }

  return { basicFields, quoteFields, imageFields, descFields, otherFields };
}

/**
 * 提取字段的搜索关键词（用于搜索框过滤）。
 *
 * @param field - 解析后的字段配置。
 * @returns 大写关键词数组。
 */
export function flattenFieldLabels(field: ParsedFieldConfig): string[] {
  const result: string[] = [field.attrName.toUpperCase()];
  if (field.label[0]) result.push(field.label[0].toUpperCase());
  if (field.label[1]) result.push(field.label[1].toUpperCase());
  if (field.subFields) {
    for (const sf of field.subFields) {
      result.push(sf.attrName.toUpperCase());
      if (sf.label[0]) result.push(sf.label[0].toUpperCase());
      if (sf.label[1]) result.push(sf.label[1].toUpperCase());
    }
  }
  return result;
}

// ── Composable ───────────────────────────────────────────────────────────────

/**
 * 商品类型 Schema 解析 composable。
 *
 * 监听 marketplaceId 和 productTypeOrigin，两者都有值时自动拉取 Schema 并解析。
 * 返回 otherFields（供"更多属性"渲染）和 dynamicFormData（双向绑定的表单数据）。
 *
 * @param marketplaceId - 市场 ID（响应式或 getter）。
 * @param productTypeOrigin - 商品类型标识（响应式或 getter）。
 * @returns 解析状态、字段列表、表单数据。
 */
export function useProductTypeSchema(
  marketplaceId: MaybeRefOrGetter<string>,
  productTypeOrigin: MaybeRefOrGetter<string>
) {
  const loading = ref(false);
  const error = ref("");
  const allFields = ref<ParsedFieldConfig[]>([]) as Ref<ParsedFieldConfig[]>;
  const otherFields = ref<ParsedFieldConfig[]>([]) as Ref<ParsedFieldConfig[]>;
  const schemaData = ref<ProductTypeSchemaVO | null>(null);

  /** 动态表单数据（site / cn 双栏，每栏 key=attrName, value=字符串）。 */
  const dynamicFormData = reactive<{
    site: Record<string, string>;
    cn: Record<string, string>;
  }>({
    site: {},
    cn: {},
  });

  /** 默认字段值（marketplace_id / language_tag）。 */
  const defaultFields = ref<Record<string, string>>({});

  /**
   * 拉取并解析 Schema。
   *
   * @param mpId - 市场 ID。
   * @param ptOrigin - 商品类型标识。
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

      // 解析全部字段
      const parsed = parseAllFields(data);
      allFields.value = parsed;

      // 分类，提取 otherFields
      const classified = classifyFields(parsed);
      otherFields.value = classified.otherFields;

      // 初始化表单数据
      dynamicFormData.site = {};
      dynamicFormData.cn = {};
      for (const field of classified.otherFields) {
        dynamicFormData.site[field.attrName] = "";
        dynamicFormData.cn[field.attrName] = "";
      }
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
      if (mpId && ptOrigin) {
        fetchSchema(mpId, ptOrigin);
      } else {
        otherFields.value = [];
        dynamicFormData.site = {};
        dynamicFormData.cn = {};
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
    defaultFields,
    schemaData,
    fetchSchema,
  };
}
