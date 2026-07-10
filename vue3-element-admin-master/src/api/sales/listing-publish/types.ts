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
