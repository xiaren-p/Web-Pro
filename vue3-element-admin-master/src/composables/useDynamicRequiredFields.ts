/**
 * 动态必填字段计算 composable。
 *
 * ============================================================
 * 职责：仿写领星 required_field_mixins.js 的 getDynamicRequiredFields()
 * ============================================================
 *
 * 领星使用 AJV 实时编译 JSON Schema 条件表达式，递归评估深层嵌套的
 * if/then/else、allOf、anyOf、oneOf 等，算出当前表单值下的动态必填字段列表。
 *
 * ============================================================
 * 为什么需要动态必填？
 * ============================================================
 *
 * Amazon JSON Schema 的必填字段是条件性的，例如：
 * ```json
 * {
 *   "type": "object",
 *   "properties": {
 *     "batteries_included": { "type": "boolean" },
 *     "battery_weight": { "type": "number" }
 *   },
 *   "allOf": [{
 *     "if": { "properties": { "batteries_included": { "const": true } } },
 *     "then": { "required": ["battery_weight"] }
 *   }]
 * }
 * ```
 * 当用户选择 "batteries_included = true" 时，battery_weight 才变为必填。
 * 普通根级 required 无法表达这种条件逻辑。
 *
 * ============================================================
 * 输出格式
 * ============================================================
 *
 * 对齐领星 requiredFieldRuleObj：
 * ```
 * {
 *   item_name: { required: [], forbidden: [], requiredFlag: false },
 *   battery_weight: { required: ["battery_weight"], forbidden: [], requiredFlag: true },
 *   item_dimensions: { required: ["length", "width", "height"], forbidden: [], requiredFlag: true },
 * }
 * ```
 *
 * @example
 * ```typescript
 * import { getDynamicRequiredFields } from "@/composables/useDynamicRequiredFields";
 *
 * // 评估单个字段
 * const required = getDynamicRequiredFields(schema, formData);
 * // → ["battery_weight", "item_name"]
 *
 * // 构建完整规则对象
 * const rules = buildRequiredFieldRuleObj(fullSchema, formData);
 * // → { battery_weight: { required: ["battery_weight"], ... }, ... }
 * ```
 */
import Ajv, { type ValidateFunction } from "ajv";

/**
 * 必填规则对象。
 *
 * @description 对齐领星 requiredFieldRuleObj（每个字段的规则）。
 *
 * @example
 * ```typescript
 * {
 *   required: ["length", "width", "height"],
 *   forbidden: [],
 *   requiredFlag: true,
 * }
 * ```
 */
export interface RequiredFieldRule {
  /**
   * 必填的子字段名列表。
   *
   * @description 当前表单值下必须填写的子字段名。
   * 当 requiredFlag 为 true 时，这些字段必须验证非空。
   */
  required: string[];

  /**
   * 禁用的子字段名列表。
   *
   * @description 当前表单值下禁止编辑的子字段名。
   * 领星某些业务条件（如低价店铺的特定价控字段）会导致字段禁用。
   * 当前实现中固定返回空数组，预留扩展。
   */
  forbidden: string[];

  /**
   * 是否有必填约束。
   *
   * @description true 表示该字段至少有一个必填约束。
   * 等于 required.length > 0。
   */
  requiredFlag: boolean;
}

/**
 * 字段级别的必填规则映射。
 *
 * @description key=attr_name → RequiredFieldRule。
 * 由 buildRequiredFieldRuleObj() 构建。
 *
 * @example
 * ```typescript
 * {
 *   item_name: { required: [], forbidden: [], requiredFlag: false },
 *   battery_weight: { required: ["battery_weight"], forbidden: [], requiredFlag: true },
 * }
 * ```
 */
export type RequiredFieldRuleMap = Record<string, RequiredFieldRule>;

/**
 * 获取动态必填字段列表。
 *
 * ============================================================
 * 算法流程（匹配领星 required_field_mixins.js）
 * ============================================================
 *
 * 递归遍历 schema 节点，按以下顺序处理：
 *
 * 1. required 数组 → 直接收集（无条件必填）
 * 2. if/then/else → 编译 if 条件，匹配时收集 then 的必填，否则收集 else 的必填
 * 3. allOf → 逐个处理，try/catch 保护（领星原版设计，allOf 内某条失败不影响其他）
 * 4. anyOf → 找到第一个匹配的条件，收集其必填，然后 break
 * 5. oneOf → 遍历全部，最后匹配的生效（领星原版行为）
 * 6. not → 编译条件，触发校验（领星原版仅触发校验不收集结果）
 * 7. properties → 递归进入深层子 schema（对应嵌套对象）
 * 8. contains → 对数组类型，找到第一个匹配项后递归
 *
 * 结果去重后返回。
 *
 * ============================================================
 * AJV 编译缓存
 * ============================================================
 *
 * 使用 Map<string, ValidateFunction> 缓存已编译的 schema 片段。
 * 同一 schema 片段（相同 JSON.stringify）只编译一次。
 * 领星：`const r = e => { ... return f.has(t) || f.set(t, this.ajv.compile(e)), f.get(t) }`
 *
 * @param schema - JSON Schema 片段（当前评估节点）
 *   - 可以是完整 schema、allOf 子项、if/then/else 子项等
 *   - 必须包含 AJV 可编译的条件（required / if / allOf 等）
 *
 * @param data - 当前表单值（用于条件评估）
 *   - 与 schema 层级对应的值
 *   - 例如评估 properties.battery_weight 时传入 { batteries_included: true }
 *
 * @returns 去重后的必填字段名数组
 *
 * @example
 * ```typescript
 * const schema = {
 *   type: "object",
 *   required: ["item_name"],
 *   allOf: [{
 *     if: { properties: { batteries_included: { const: true } } },
 *     then: { required: ["battery_weight"] }
 *   }]
 * };
 *
 * getDynamicRequiredFields(schema, { batteries_included: true });
 * // → ["item_name", "battery_weight"]
 *
 * getDynamicRequiredFields(schema, { batteries_included: false });
 * // → ["item_name"]
 * ```
 *
 * @see buildRequiredFieldRuleMap - 对全部字段执行此函数
 */
export function getDynamicRequiredFields(schema: Record<string, unknown>, data: unknown): string[] {
  const result: string[] = [];
  const cache = new Map<string, ValidateFunction>();
  const ajv = new Ajv();

  /**
   * 编译并缓存 AJV 校验函数。
   *
   * @description 领星使用闭包缓存 compile 结果。
   * key = JSON.stringify(subSchema)，不同 schema 不同 key。
   *
   * @param subSchema - 要编译的 schema 片段
   * @returns AJV ValidateFunction
   */
  function compile(subSchema: Record<string, unknown>): ValidateFunction {
    const key = JSON.stringify(subSchema);
    if (!cache.has(key)) cache.set(key, ajv.compile(subSchema));
    return cache.get(key)!;
  }

  // ── 第 1 步：直接必填 ──
  // 领星：i.required && i.required.forEach(e => { o.push(e) })
  if (Array.isArray(schema.required)) {
    for (const field of schema.required as string[]) {
      result.push(field);
    }
  }

  // ── 第 2 步：if/then/else 条件必填 ──
  // 领星：if(i.if) { if(r(i.if)(s)) { i.then && ... } else if(i.else) { ... } }
  if (schema.if && typeof schema.if === "object") {
    if (compile(schema.if as Record<string, unknown>)(data)) {
      if (schema.then && typeof schema.then === "object") {
        const sub = getDynamicRequiredFields(schema.then as Record<string, unknown>, data);
        result.push(...sub);
      }
    } else if (schema.else && typeof schema.else === "object") {
      const sub = getDynamicRequiredFields(schema.else as Record<string, unknown>, data);
      result.push(...sub);
    }
  }

  // ── 第 3 步：allOf 组合 ──
  // 领星加 try/catch：某个条件失败不影响其他条件
  if (Array.isArray(schema.allOf)) {
    for (const sub of schema.allOf) {
      try {
        const subResult = getDynamicRequiredFields(sub as Record<string, unknown>, data);
        result.push(...subResult);
      } catch {
        // 领星原版 try/catch 静默跳过
      }
    }
  }

  // ── 第 4 步：anyOf 组合（取第一个匹配） ──
  // 领星：for(const e of i.anyOf) if(r(e)(s)) { ... break }
  if (Array.isArray(schema.anyOf)) {
    for (const sub of schema.anyOf) {
      if (compile(sub as Record<string, unknown>)(data)) {
        const subResult = getDynamicRequiredFields(sub as Record<string, unknown>, data);
        result.push(...subResult);
        break;
      }
    }
  }

  // ── 第 5 步：oneOf 组合（取最后一个匹配） ──
  // 领星：let e=[]; for(const t of i.oneOf) r(t)(s) && (e = this.getDynamicRequiredFields(t,s))
  if (Array.isArray(schema.oneOf)) {
    let merged: string[] = [];
    for (const sub of schema.oneOf) {
      if (compile(sub as Record<string, unknown>)(data)) {
        merged = getDynamicRequiredFields(sub as Record<string, unknown>, data);
      }
    }
    result.push(...merged);
  }

  // ── 第 6 步：not 条件（仅触发编译，不收集结果） ──
  // 领星：i.not && r(i.not)(s)  （仅调用 compile 触发校验）
  if (schema.not && typeof schema.not === "object") {
    compile(schema.not as Record<string, unknown>)(data);
  }

  // ── 第 7 步：properties 深层递归 ──
  // 领星：if(i.properties) for(const [e,t] of Object.entries(i.properties)) if(s[e]!==void 0) ...
  if (
    schema.properties &&
    typeof schema.properties === "object" &&
    typeof data === "object" &&
    data !== null
  ) {
    for (const [key, subSchema] of Object.entries(schema.properties)) {
      if ((data as Record<string, unknown>)[key] !== undefined) {
        const sub = getDynamicRequiredFields(
          subSchema as Record<string, unknown>,
          (data as Record<string, unknown>)[key]
        );
        result.push(...sub);
      }
    }
  }

  // ── 第 8 步：contains 数组包含 ──
  // 领星：if(i.contains) { const e = r(i.contains); if(Array.isArray(s)) for... }
  if (schema.contains && typeof schema.contains === "object" && Array.isArray(data)) {
    const containsFn = compile(schema.contains as Record<string, unknown>);
    for (const item of data) {
      if (containsFn(item)) {
        const sub = getDynamicRequiredFields(schema.contains as Record<string, unknown>, item);
        result.push(...sub);
        break;
      }
    }
  }

  // 去重
  return [...new Set(result)];
}

/**
 * 构建 requiredFieldRuleObj。
 *
 * @description 重建完整 Schema（含 properties + required），
 * 一次 getDynamicRequiredFields 计算所有根级必填，按 attrName 归类。
 *
 * 匹配领星 DraftOtherDetail.requiredFieldRuleObj 逻辑。
 *
 * @param schemaData - 后端 API 返回的 ProductTypeSchemaVO
 *   - 必须含有 fields（= properties）和 requiredFields（= required）
 *
 * @param formData - 当前表单值
 *   - key=attrName, value=对应的表单数据（嵌套数组格式）
 *
 * @returns 字段级别的必填规则映射（RequiredFieldRuleMap）
 *   - key=attrName
 *   - value={ required, forbidden, requiredFlag }
 *
 * @example
 * ```typescript
 * const rules = buildRequiredFieldRuleObj(schemaData.value, formData);
 * // rules.item_name.requiredFlag === true  （根级 required 命中）
 * ```
 */
/**
 * 获取组字段的子字段名列表。
 *
 * @description 检查 schema field 是否有 items.properties → 取非系统子键。
 * 与 useProductTypeSchema 的 isGroupField 逻辑一致。
 */
const SYSTEM_NAMES = new Set(["marketplace_id", "language_tag"]);
function getGroupChildren(fieldDef: Record<string, unknown>): string[] {
  const items = fieldDef.items as Record<string, unknown> | undefined;
  const subProps = items?.properties as Record<string, unknown> | undefined;
  if (!subProps) return [];
  return Object.keys(subProps).filter((k) => !SYSTEM_NAMES.has(k));
}

export function buildRequiredFieldRuleObj(
  schemaData: Record<string, unknown>,
  formData: Record<string, unknown>
): RequiredFieldRuleMap {
  const result: RequiredFieldRuleMap = {};
  const fields = (schemaData.fields ?? {}) as Record<string, unknown>;

  // 重建完整 Schema（匹配领星 raw schema 的 { type, properties, required } 结构）
  const fullSchema: Record<string, unknown> = {
    type: "object",
    properties: fields,
    required: schemaData.requiredFields ?? [],
  };

  // 预计算组字段映射（父 → 子字段名列表）
  const childrenMap: Record<string, string[]> = {};
  for (const attrName of Object.keys(fields)) {
    const children = getGroupChildren(fields[attrName] as Record<string, unknown>);
    if (children.length > 1 || (children.length === 1 && children[0] !== "value")) {
      childrenMap[attrName] = children;
    }
  }

  // 一次 getDynamicRequiredFields → 捕获根级 required + 条件必填 + 子级必填
  const allRequired = getDynamicRequiredFields(fullSchema, formData);

  for (const attrName of Object.keys(fields)) {
    const children = childrenMap[attrName];
    if (children) {
      // 组字段：收集子字段的必填命中
      const childRequired = allRequired.filter((r) => children.includes(r));
      result[attrName] = {
        required: childRequired,
        forbidden: [],
        requiredFlag: childRequired.length > 0,
      };
    } else {
      const isRequired = allRequired.includes(attrName);
      result[attrName] = {
        required: isRequired ? [attrName] : [],
        forbidden: [],
        requiredFlag: isRequired,
      };
    }
  }

  return result;
}
