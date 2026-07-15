/**
 * 字段分类路由 composable。
 *
 * ============================================================
 * 职责：仿写领星 DraftOtherInfo.vue 的 processDynamicDescInfoList()
 * ============================================================
 *
 * 根据字段定义的 maxUniqueItems 和实际表单数据的形状，将每个字段分类到 7 种渲染类型：
 *
 * ```
 * 分类流程（匹配领星 processDynamicDescInfoList）：
 *
 * 对每个 attr_name：
 *   ├─ maxUniqueItems > 1 ?
 *   │   ├─ 仅 1 个子键 → "singleArray"  → DynamicFieldList (add/remove 列表)
 *   │   └─ 多 个 子键 → "multiArray"   → DynamicFieldGroupList (add/remove 组列表)
 *   │
 *   └─ maxUniqueItems <= 1 ?
 *       └─ value[0] 内子键分析：
 *           ├─ 1 个子键
 *           │   ├─ 值是对象 → "singleObject" → DynamicFieldSingleGroup
 *           │   └─ 值非对象 → "single"       → DynamicFieldItem (基本字段)
 *           │
 *           └─ 多个子键
 *               ├─ 含对象  → "multiObj"   → DynamicFieldMultiGroup
 *               └─ 全非对象 → "multi"      → DynamicFieldGroup (对象组)
 * ```
 *
 * 领星对应的组件映射：
 * | 类型 | 领星组件 | 本实现组件 |
 * |------|---------|-----------|
 * | single | DynamicFormItem / DynamicFormGroupItem | DynamicFieldItem |
 * | singleArray | DynamicFormList | DynamicFieldList |
 * | multiArray | DynamicFormGroupList | DynamicFieldGroupList |
 * | multi | DynamicFormGroup | DynamicFieldGroup |
 * | multiObj | DynamicFormMultiGroup | DynamicFieldMultiGroup |
 * | singleObject | DynamicFormSingleGroup | DynamicFieldSingleGroup |
 * | singleArrayObject | DynamicFormSingleGroup | DynamicFieldSingleGroup |
 *
 * @example
 * ```typescript
 * // 在组件中使用：
 * const classifiedFields = useFieldClassification(
 *   computed(() => dynamicFormData.site),
 *   dynamicDescInfo,
 *   requiredFieldRuleMap
 * );
 *
 * // 遍历分类结果：
 * <DynamicField
 *   v-for="cf in classifiedFields.value"
 *   :key="cf.attrName"
 *   :field-config="dynamicDescInfo[cf.attrName]"
 *   :category="cf.category"
 *   :model-value="dynamicFormData.site[cf.attrName]"
 *   :required-fields="cf.requiredFields"
 * />
 * ```
 */
import { computed, type ComputedRef } from "vue";
import type { ParsedFieldConfig } from "@/composables/useProductTypeSchema";
import type {
  RequiredFieldRule,
  RequiredFieldRuleMap,
} from "@/composables/useDynamicRequiredFields";

/**
 * 字段渲染分类类型。
 *
 * @description 对应领星 processDynamicDescInfoList 输出的第二个元素（category 字符串）。
 * - single: 单值简单字段
 * - singleArray: 多值列表（maxUniqueItems > 1，仅 1 个子键）
 * - multiArray: 多值组列表（maxUniqueItems > 1，多子键）
 * - multi: 对象组（多子字段，全非对象）
 * - multiObj: 混合类型组（多子字段，含对象）
 * - singleObject: 单嵌套对象
 * - singleArrayObject: 多值嵌套对象
 */
export type FieldCategory =
  | "single"
  | "singleArray"
  | "multiArray"
  | "multi"
  | "multiObj"
  | "singleObject"
  | "singleArrayObject";

/**
 * 分类后的字段信息。
 *
 * @description 对应领星 processDynamicDescInfoList 对每个字段生成的元组：
 * [attr_name, category, fieldNames, requiredFields, forbiddenFields, uuid, visible]
 * 我们用对象替代元组，更易读。
 */
export interface ClassifiedField {
  /**
   * 字段名。
   *
   * @description 对应 attr_name，用于查找 fieldConfig 和 formData 中的值。
   */
  attrName: string;

  /**
   * 渲染分类。
   *
   * @description 决定使用 DynamicField 的哪个子组件渲染。
   */
  category: FieldCategory;

  /**
   * 子字段名列表。
   *
   * @description 当前字段 value[0] 中除 marketplace_id / language_tag 外的所有子键。
   * 渲染时遍历此列表渲染子字段。
   */
  fieldNames: string[];

  /**
   * 必填的子字段名列表。
   *
   * @description 来自 AJV 动态必填计算的结果（useDynamicRequiredFields）。
   * 在渲染时标记哪些字段带红色 *。
   */
  requiredFields: string[];

  /**
   * 禁用的子字段名列表。
   *
   * @description 来自 AJV 动态计算的禁用字段（例如低价店铺的价格上限字段）。
   * 禁用的字段在 UI 上置灰不可编辑。
   * 当前实现中常为空数组，预留扩展。
   */
  forbiddenFields: string[];

  /**
   * 该字段是否可见。
   *
   * @description false 表示该字段的所有子字段都被 forbidden 排除。
   * 领星：`!(n.length == ((o=d==null?void 0:d.forbidden)==null?void 0:o.length) && !$)`
   */
  visible: boolean;
}

/**
 * 系统默认字段（不在界面上渲染，仅后端使用）。
 *
 * @description 领星 defaultAssignFields。
 * 这些字段的值由后端自动填充，前端不需要渲染输入控件。
 */
const DEFAULT_ASSIGN_FIELDS = new Set(["marketplace_id", "language_tag"]);

/**
 * 对单个字段执行分类。
 *
 * ============================================================
 * 分类算法
 * ============================================================
 *
 * 1. 检查 maxUniqueItems > 1
 *    - true → 多值类型：
 *      - 仅 1 个子键 → "singleArray"（DynamicFieldList）
 *      - 多个子键 → "multiArray"（DynamicFieldGroupList）
 *
 * 2. maxUniqueItems <= 1 → 单值类型：
 *    - 检查 value[0] 的非系统子键：
 *      - 仅 1 个子键：
 *        - 子键值为对象 → "singleObject"（DynamicFieldSingleGroup）
 *        - 否则 → "single"（DynamicFieldItem）
 *      - 多个子键：
 *        - 含对象值 → "multiObj"（DynamicFieldMultiGroup）
 *        - 全非对象 → "multi"（DynamicFieldGroup）
 *
 * @param attrName - 字段名
 * @param value - 该字段的当前表单值（数组）
 * @param fieldConfig - 该字段的 schema 配置
 * @param rule - 该字段的必填/禁用规则（可选）
 * @returns 分类结果，若 value 结构不符合预期则返回 null
 *
 * @see classifyAllFields - 遍历全部字段调用此函数
 *
 * @example
 * ```typescript
 * // 简单字段：item_name = [{ value: "Book", marketplace_id: "xxx" }]
 * classifySingleField("item_name", [...], { maxUniqueItems: 1 }, undefined)
 * // → { attrName: "item_name", category: "single", fieldNames: ["value"], ... }
 *
 * // 多值字段：language = [{ value: "chi" }, { value: "eng" }]
 * classifySingleField("language", [...], { maxUniqueItems: 5 }, undefined)
 * // → { attrName: "language", category: "singleArray", fieldNames: ["value"], ... }
 *
 * // 组字段：item_dimensions = [{ length: { value: 10 }, width: { value: 8 }, ... }]
 * classifySingleField("item_dimensions", [...], { maxUniqueItems: 1, fields: {...} }, undefined)
 * // → { attrName: "item_dimensions", category: "multi", fieldNames: ["length", "width", ...], ... }
 * ```
 */
export function classifySingleField(
  attrName: string,
  value: unknown[],
  fieldConfig: ParsedFieldConfig,
  rule?: RequiredFieldRule
): ClassifiedField | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const firstItem = value[0];
  if (typeof firstItem !== "object" || firstItem === null) return null;

  const subKeys = Object.keys(firstItem).filter((k) => !DEFAULT_ASSIGN_FIELDS.has(k));
  const requiredList = rule?.required ?? [];
  const forbiddenList = rule?.forbidden ?? [];

  const maxUniqueItems = fieldConfig.maxUniqueItems ?? 1;

  // ── 多值字段 ──
  if (maxUniqueItems > 1) {
    if (subKeys.length <= 1) {
      return {
        attrName,
        category: "singleArray",
        fieldNames: subKeys,
        requiredFields: requiredList,
        forbiddenFields: forbiddenList,
        visible: true,
      };
    }
    return {
      attrName,
      category: "multiArray",
      fieldNames: subKeys,
      requiredFields: requiredList,
      forbiddenFields: forbiddenList,
      visible: true,
    };
  }

  // ── 单值字段 ──
  if (subKeys.length === 1) {
    const val = (firstItem as Record<string, unknown>)[subKeys[0]];
    if (typeof val === "object" && val !== null && !Array.isArray(val)) {
      return {
        attrName,
        category: "singleObject",
        fieldNames: subKeys,
        requiredFields: requiredList,
        forbiddenFields: forbiddenList,
        visible: true,
      };
    }
    return {
      attrName,
      category: "single",
      fieldNames: subKeys,
      requiredFields: requiredList,
      forbiddenFields: forbiddenList,
      visible: true,
    };
  }

  const hasObject = subKeys.some(
    (k) =>
      typeof (firstItem as Record<string, unknown>)[k] === "object" &&
      (firstItem as Record<string, unknown>)[k] !== null &&
      !Array.isArray((firstItem as Record<string, unknown>)[k])
  );

  if (hasObject) {
    return {
      attrName,
      category: "multiObj",
      fieldNames: subKeys,
      requiredFields: requiredList,
      forbiddenFields: forbiddenList,
      visible: true,
    };
  }

  return {
    attrName,
    category: "multi",
    fieldNames: subKeys,
    requiredFields: requiredList,
    forbiddenFields: forbiddenList,
    visible: true,
  };
}

/**
 * 分类全部字段。
 *
 * @description 遍历表单数据的每个 key，匹配 dynamicDescInfo 获取配置，
 * 对每个字段调用 classifySingleField 分类。
 * 过滤掉：
 * - 值缺失或格式不符合预期的字段（classifySingleField 返回 null）
 * - 所有子字段都被 forbidden 排除的字段（visible = false）
 *
 * @param formData - 当前表单数据（key=attrName, value=数组）
 * @param dynamicDescInfo - 字段配置映射（key=attrName）
 *   由 useProductTypeSchema 的 dynamicDescInfo 提供。
 * @param requiredFieldRuleMap - 可选，必填/禁用规则映射
 *   由 useDynamicRequiredFields 的 buildRequiredFieldRuleObj 提供。
 * @returns 分类结果数组
 *
 * @example
 * ```typescript
 * const classified = classifyAllFields(
 *   { item_name: [{ value: "Book" }], language: [{ value: "chi" }, { value: "eng" }] },
 *   { item_name: { fields: undefined }, language: { maxUniqueItems: 5 } }
 * );
 * // → [
 * //   { attrName: "item_name", category: "single", ... },
 * //   { attrName: "language", category: "singleArray", ... },
 * // ]
 * ```
 */
export function classifyAllFields(
  formData: Record<string, unknown[]>,
  dynamicDescInfo: Record<string, ParsedFieldConfig>,
  requiredFieldRuleMap?: RequiredFieldRuleMap
): ClassifiedField[] {
  const result: ClassifiedField[] = [];

  for (const [attrName, value] of Object.entries(formData)) {
    const fieldConfig = dynamicDescInfo[attrName];
    if (!fieldConfig) continue;

    if (!Array.isArray(value) || value.length === 0) continue;

    const rule = requiredFieldRuleMap?.[attrName];
    const classified = classifySingleField(attrName, value, fieldConfig, rule);
    if (!classified) continue;

    // 检查 forbidden 是否排除了全部子字段
    const visibleKeys = classified.fieldNames.filter(
      (k) => !classified.forbiddenFields.includes(k)
    );
    if (visibleKeys.length === 0) continue;

    result.push(classified);
  }

  return result;
}

/**
 * 字段分类 composable。
 *
 * @description 基于 formData 和 dynamicDescInfo 响应式计算字段分类结果。
 * 当 formData、dynamicDescInfo 或 requiredFieldRuleMap 变化时自动重算。
 *
 * 如果不需要动态必填规则，可以省略 requiredFieldRuleMap 参数。
 *
 * @param formData - 响应式表单数据对象（ComputedRef）
 *   - 建议使用 computed(() => dynamicFormData.site) 或 .cn
 *   - 确保响应式变化时触发重算
 *
 * @param dynamicDescInfo - 响应式字段配置映射（ComputedRef）
 *   - 来自 useProductTypeSchema 的 dynamicDescInfo
 *   - dynamicDescInfo 是一个 ref，可直接使用
 *
 * @param requiredFieldRuleMap - 可选，必填/禁用规则映射（ComputedRef）
 *   - 来自 useDynamicRequiredFields 的 buildRequiredFieldRuleObj
 *   - 若不需要动态必填可忽略
 *
 * @returns 分类后的字段数组（ComputedRef<ClassifiedField[]>）
 *
 * @example
 * ```typescript
 * // 在模板编辑器中使用（不含动态规则）
 * const classifiedFields = useFieldClassification(
 *   computed(() => ({ ...动态表单数据 })),
 *   computed(() => dynamicDescInfo.value)
 * );
 *
 * // 在草稿编辑器中使用（含动态规则）
 * const classifiedFields = useFieldClassification(
 *   computed(() => draftForm),
 *   computed(() => dynamicDescInfo.value),
 *   computed(() => requiredFieldRuleMap)
 * );
 * ```
 */
export function useFieldClassification(
  formData: ComputedRef<Record<string, unknown[]>>,
  dynamicDescInfo: ComputedRef<Record<string, ParsedFieldConfig>>,
  requiredFieldRuleMap?: ComputedRef<RequiredFieldRuleMap | undefined>
): ComputedRef<ClassifiedField[]> {
  return computed(() => {
    const data = formData.value;
    const descInfo = dynamicDescInfo.value;
    const rules = requiredFieldRuleMap?.value;
    return classifyAllFields(data, descInfo, rules);
  });
}
