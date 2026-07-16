/** * 更多属性 Section。 * * ============================================================ *
职责：渲染"更多属性"区域，展示未匹配 basic/quote/image/desc 的字段。 *
============================================================ * * 数据流： * 1. inject 获取
draftForm（表单全局状态）和 currentSiteCode * 2. useProductTypeSchema 监听 marketplaceId +
productType，拉取 Schema * 3. 解析出 otherFields（未分类字段）和 dynamicDescInfo（字段配置映射） *
4. useFieldClassification 根据表单数据形状分类字段 * 5. DynamicField
路由组件根据分类结果渲染对应子组件 * 6. 双栏布局：左栏站点语言值，右栏中文值 * *
============================================================ * 数据格式变更（匹配灵星） *
============================================================ * * 旧格式（扁平字符串）： *
dynamicFormData.site[attrName] = "商品名称" * * 新格式（灵星兼容嵌套数组）： *
dynamicFormData.site[attrName] = [{ value: "商品名称", marketplace_id: "ATVPDKIKX0DER" }] * *
组字段格式： * dynamicFormData.site[field_attr] = [{ * subKey1: { value: "10", marketplace_id:
"ATVPDKIKX0DER" }, * subKey2: { value: "inches", marketplace_id: "ATVPDKIKX0DER" }, *
marketplace_id: "ATVPDKIKX0DER", * }] * *
============================================================ * 字段路由流程 *
============================================================ * * 每个字段 → useFieldClassification →
ClassifiedField.category * → DynamicField.category → 选择子组件 * * @see useProductTypeSchema -
Schema 解析 * @see useFieldClassification - 字段分类 * @see DynamicField - 字段路由组件 */
<template>
  <section class="draft-section">
    <div class="draft-section__header">
      <span class="draft-section__bar" />
      更多属性
    </div>

    <!-- 工具栏：仅必填 + 搜索 -->
    <div class="more-attrs__toolbar">
      <el-checkbox v-model="onlyShowRequired">仅查看必填字段</el-checkbox>
      <el-input
        v-model="searchText"
        placeholder="搜索字段名称"
        clearable
        size="small"
        class="more-attrs__search"
        :prefix-icon="SearchIcon"
      />
      <span v-if="filteredClassified.length" class="more-attrs__count">
        共 {{ filteredClassified.length }} 个字段
      </span>
    </div>

    <el-row :gutter="24">
      <!-- 左栏：站点内容 -->
      <el-col :span="12">
        <div class="draft-col__header">站点内容</div>
        <div v-loading="loading" class="draft-section__body">
          <el-empty
            v-if="!filteredClassified.length && !loading"
            description="暂无更多属性字段"
            :image-size="60"
          />
          <template v-else>
            <div v-for="group in groupedFields" :key="group.title" class="more-attrs__group">
              <div class="more-attrs__group-title">{{ group.title }}</div>
              <el-form label-position="left" label-width="200px" size="default">
                <el-form-item
                  v-for="cf in group.fields"
                  :key="cf.attrName"
                  :required="cf.requiredFields.length > 0"
                >
                  <template #label>
                    <div class="more-attrs__label">
                      <p class="more-attrs__label-zh">
                        <span v-if="cf.requiredFields.length > 0" class="more-attrs__label-star">
                          *
                        </span>
                        {{ dynamicDescInfo[cf.attrName]?.label[1] ?? cf.attrName }}
                      </p>
                      <p class="more-attrs__label-en">
                        {{ dynamicDescInfo[cf.attrName]?.label[0] ?? cf.attrName }}
                      </p>
                    </div>
                  </template>
                  <DynamicField
                    :field-config="dynamicDescInfo[cf.attrName]"
                    :category="cf.category"
                    :model-value="(dynamicFormData.site[cf.attrName] as unknown[]) ?? []"
                    :required-fields="cf.requiredFields"
                    :marketplace-id="siteCode"
                    @update:model-value="
                      (val: unknown[]) =>
                        onSiteInput(
                          cf.attrName,
                          dynamicDescInfo[cf.attrName]?.label[1] ?? cf.attrName,
                          val
                        )
                    "
                  />
                  <div v-if="errors[`site.${cf.attrName}`]" class="lang-error-hint">
                    {{ errors[`site.${cf.attrName}`] }}
                  </div>
                </el-form-item>
              </el-form>
            </div>
          </template>
        </div>
      </el-col>

      <!-- 右栏：中文内容 -->
      <el-col :span="12">
        <div class="draft-col__header">中文内容</div>
        <div v-loading="loading" class="draft-section__body">
          <el-empty
            v-if="!filteredClassified.length && !loading"
            description="暂无更多属性字段"
            :image-size="60"
          />
          <template v-else>
            <div v-for="group in groupedFields" :key="group.title" class="more-attrs__group">
              <div class="more-attrs__group-title">{{ group.title }}</div>
              <el-form label-position="left" label-width="200px" size="default">
                <el-form-item
                  v-for="cf in group.fields"
                  :key="cf.attrName"
                  :required="cf.requiredFields.length > 0"
                >
                  <template #label>
                    <div class="more-attrs__label">
                      <p class="more-attrs__label-zh">
                        <span v-if="cf.requiredFields.length > 0" class="more-attrs__label-star">
                          *
                        </span>
                        {{ dynamicDescInfo[cf.attrName]?.label[0] ?? cf.attrName }}
                      </p>
                      <p class="more-attrs__label-en">
                        {{ dynamicDescInfo[cf.attrName]?.label[1] ?? cf.attrName }}
                      </p>
                    </div>
                  </template>
                  <DynamicField
                    :field-config="dynamicDescInfo[cf.attrName]"
                    :category="cf.category"
                    :model-value="(dynamicFormData.cn[cf.attrName] as unknown[]) ?? []"
                    :required-fields="cf.requiredFields"
                    :marketplace-id="siteCode"
                    @update:model-value="
                      (val: unknown[]) =>
                        onCnInput(
                          cf.attrName,
                          dynamicDescInfo[cf.attrName]?.label[0] ?? cf.attrName,
                          val
                        )
                    "
                  />
                  <div v-if="errors[`cn.${cf.attrName}`]" class="lang-error-hint">
                    {{ errors[`cn.${cf.attrName}`] }}
                  </div>
                </el-form-item>
              </el-form>
            </div>
          </template>
        </div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, inject } from "vue";
import { Search as SearchIcon } from "@element-plus/icons-vue";
import { useProductTypeSchema, flattenFieldLabels } from "@/composables/useProductTypeSchema";
import { useFieldClassification } from "./composables/useFieldClassification";
import { buildRequiredFieldRuleObj } from "@/composables/useDynamicRequiredFields";
import { validateSiteLang, validateChinese } from "@/utils/lang-check";
import DynamicField from "./components/DynamicField.vue";

defineOptions({ name: "MoreAttributesSection" });

const f = inject<any>("draftForm");
const siteCode = inject<import("vue").ComputedRef<string>>("currentSiteCode")!;
const errors = inject<Record<string, string>>("langErrors")!;

// ── Schema 解析 ──
const { loading, dynamicFormData, dynamicDescInfo, schemaData, propertyGroupsZh } =
  useProductTypeSchema(
    () => f?.site?.marketplaceId ?? "",
    () => f?.site?.productType ?? ""
  );

// ── 搜索与过滤 ──
const searchText = ref("");
const onlyShowRequired = ref(false);

/**
 * 必填规则映射（根级 required + 条件必填）。
 */
const requiredFieldRuleMap = computed(() => {
  if (!schemaData.value || !Object.keys(dynamicFormData.site).length) return undefined;
  return buildRequiredFieldRuleObj(
    schemaData.value,
    dynamicFormData.site as unknown as Record<string, unknown>
  );
});

/**
 * 分类后的字段列表。
 *
 * @description 根据 dynamicFormData.site 的当前值对字段分类。
 * 当表单数据变化时自动重算。
 */
const classifiedFields = useFieldClassification(
  computed(() => dynamicFormData.site as unknown as Record<string, unknown[]>),
  computed(() => dynamicDescInfo.value),
  computed(() => requiredFieldRuleMap.value)
);

/**
 * 过滤后的分类字段列表（搜索 + 仅必填）。
 */
const filteredClassified = computed(() => {
  let result = classifiedFields.value;

  if (searchText.value.trim()) {
    const search = searchText.value.trim().toUpperCase();
    result = result.filter((cf) => {
      const fieldConfig = dynamicDescInfo.value[cf.attrName];
      if (!fieldConfig) return false;
      return flattenFieldLabels(fieldConfig).some((label) => label.includes(search));
    });
  }

  if (onlyShowRequired.value) {
    result = result.filter((cf) => cf.requiredFields.length > 0);
  }

  return result;
});

/**
 * 按 propertyGroups 分组后的字段列表。
 *
 * @description 匹配领星分组渲染：每组带标题头，字段按 propertyNames 归属。
 * 未匹配任何分组的字段归于"其他"。
 */
const groupedFields = computed(() => {
  const groups: {
    title: string;
    fields: import("./composables/useFieldClassification").ClassifiedField[];
  }[] = [];
  const pg = propertyGroupsZh.value ?? {};

  // 初始化组
  const groupsMap = new Map<string, typeof groups extends (infer U)[] ? U : never>();
  for (const [id, g] of Object.entries(pg)) {
    groupsMap.set(id, { title: g.title, fields: [] });
  }

  // 分配字段到组（属性已展平，子字段为独立根级条目 → 直接匹配）
  const ungrouped: import("./composables/useFieldClassification").ClassifiedField[] = [];
  for (const cf of filteredClassified.value) {
    let assigned = false;
    for (const [id, g] of Object.entries(pg)) {
      if (g.propertyNames.includes(cf.attrName)) {
        const entry = groupsMap.get(id);
        if (entry) entry.fields.push(cf);
        assigned = true;
        break;
      }
    }
    if (!assigned) ungrouped.push(cf);
  }

  // 输出非空组
  for (const [id] of Object.entries(pg)) {
    const entry = groupsMap.get(id);
    if (entry && entry.fields.length) groups.push(entry);
  }

  if (ungrouped.length) groups.push({ title: "其他", fields: ungrouped });

  return groups;
});

// ── 输入处理 ──

/**
 * 站点列输入处理。
 *
 * @param attrName - 字段名
 * @param label - 字段中文标签（用于校验提示）
 * @param val - 新的表单值（完整数组）
 */
function onSiteInput(attrName: string, label: string, val: unknown[]) {
  dynamicFormData.site[attrName] = val;
  const valueStr = String((val?.[0] as Record<string, unknown>)?.value ?? "");
  const result = validateSiteLang(valueStr, siteCode.value, label);
  errors[`site.${attrName}`] = result.message;
}

/**
 * 中文列输入处理。
 *
 * @param attrName - 字段名
 * @param label - 字段中文标签（用于校验提示）
 * @param val - 新的表单值（完整数组）
 */
function onCnInput(attrName: string, label: string, val: unknown[]) {
  dynamicFormData.cn[attrName] = val;
  const valueStr = String((val?.[0] as Record<string, unknown>)?.value ?? "");
  const result = validateChinese(valueStr, label);
  errors[`cn.${attrName}`] = result.message;
}
</script>

<style scoped lang="scss">
.more-attrs {
  &__toolbar {
    display: flex;
    gap: 12px;
    align-items: center;
    padding: 0 0 16px;
  }

  &__search {
    width: 240px;
  }

  &__count {
    font-size: var(--font-size-xs);
    color: var(--text-tertiary);
    white-space: nowrap;
  }

  &__label {
    line-height: 1.5;

    &-zh {
      margin: 0;
      font-size: 12px;
      color: #33363c;
    }

    &-en {
      margin: 0;
      font-size: 12px;
      color: #888c94;
    }

    &-star {
      margin-right: 4px;
      font-size: 10px;
      color: #f5222d;
    }
  }

  &__group {
    margin-bottom: 20px;
  }

  &__group-title {
    padding: 6px 12px;
    margin-bottom: 12px;
    font-size: 13px;
    font-weight: 700;
    color: #0b1019;
    background: #f5f7fa;
    border-radius: 2px;
  }
}
</style>
