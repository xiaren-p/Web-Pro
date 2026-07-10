/**
 * 刊登管理 - 商品类型 Schema API 类型定义。
 *
 * 对应后端 ProductTypeSchemaSerializer 输出，后端已将 properties / properties_zh
 * 的 JSON 文本解析为 fields / fieldsZh / requiredFields / defaultFields。
 */

/** JSON Schema 原始字段定义（宽松类型，兼容 Amazon Schema 各种变体）。 */
export interface SchemaFieldDef {
  title?: string;
  description?: string;
  type?: string;
  minItems?: number;
  maxItems?: number;
  minUniqueItems?: number;
  maxUniqueItems?: number;
  selectors?: string[];
  required?: string[];
  enum?: (string | number)[];
  enumNames?: string[];
  maxLength?: number;
  minLength?: number;
  minimum?: number;
  maximum?: number;
  multipleOf?: number;
  items?: SchemaFieldDef;
  properties?: Record<string, SchemaFieldDef>;
  anyOf?: SchemaFieldDef[];
  oneOf?: SchemaFieldDef[];
  allOf?: SchemaFieldDef[];
  examples?: string[];
  editable?: boolean;
  hidden?: boolean;
  default?: unknown;
}

/** getProductType 接口响应。 */
export interface ProductTypeSchemaVO {
  productTypeUniqueId: string;
  marketplaceId: string;
  productTypeOrigin: string;
  displayName: string;
  /** 根级必填字段名列表（来自 JSON Schema required 数组）。 */
  requiredFields: string[];
  /** $defs 中 marketplace_id / language_tag 的默认值。 */
  defaultFields: Record<string, string>;
  /** 站点语言版本的字段定义（properties.properties）。 */
  fields: Record<string, SchemaFieldDef>;
  /** 中文版本的字段定义。 */
  fieldsZh: Record<string, SchemaFieldDef>;
}

/** getProductType 接口查询参数。 */
export interface ProductTypeSchemaQuery {
  marketplaceId: string;
  productTypeOrigin: string;
}

// ── Amazon 分类 ──────────────────────────────────────────────────────────────

/** Amazon 分类节点（对应 AmazonRootCategorySerializer 输出）。 */
export interface AmazonCategoryVO {
  categoryUniqueId: string;
  categoryName: string;
  categoryId: number;
  marketplaceId: string;
  parentId: number;
  isRoot: number;
  hasChildren: number;
  childCategories: string[];
  productTypeOrigin: string[];
  browseNodeAttributes: string;
  categoryPathId: string;
  categoryPathName: string;
}

/** 分类搜索类型。 */
export type CategorySearchType = "category_name" | "product_type_origin" | "category_id";

// ── 店铺 ──────────────────────────────────────────────────────────────────────

/** 店铺下拉选项（对应 ShopOptionsViewSet 输出）。 */
export interface ShopOptionVO {
  sid: number;
  mid: number | null;
  name: string;
  country: string;
  region: string;
  accountName: string;
  marketplaceId: string;
}

// ── Amazon 市场列表 ──────────────────────────────────────────────────────────

/** 市场下拉选项（对应 MarketplaceViewSet 输出）。 */
export interface MarketplaceVO {
  marketplaceId: string;
  country: string;
  code: string;
  region: string;
  awsRegion: string;
}

// ── 刊登模板 ──────────────────────────────────────────────────────────────────

/** 模板列表行（不含 data_json）。 */
export interface PublishTemplateListVO {
  id: number;
  templateName: string;
  marketplaceId: string;
  productType: string;
  productTypeUniqueId: string;
  countryCode: string;
  createUserName: string;
  updateUserName: string;
  createdAt: string;
  updatedAt: string;
}

/** 模板详情（含 dataJson）。 */
export interface PublishTemplateDetailVO extends PublishTemplateListVO {
  /** 动态 Amazon 属性数据。 */
  dataJson: Record<string, unknown>;
}

/** 模板写入表单（新增/编辑）。 */
export interface PublishTemplateForm {
  templateName: string;
  marketplaceId: string;
  productType: string;
  productTypeUniqueId: string;
  countryCode: string;
  /** 动态 Amazon 属性数据，后端映射到 data_json。 */
  amazonData: Record<string, unknown>;
}

/** 模板分页查询参数。 */
export interface PublishTemplatePageQuery {
  pageNum?: number;
  pageSize?: number;
  keyword?: string;
}

/** 模板分页响应。 */
export interface PublishTemplatePageResult {
  total: number;
  list: PublishTemplateListVO[];
}
