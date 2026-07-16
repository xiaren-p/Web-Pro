/** 更多属性 Section - 对齐领星 DraftOtherDetail 平铺渲染（无分组）。 */
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
          <el-form v-else label-position="left" label-width="200px" size="default">
            <el-form-item
              v-for="cf in filteredClassified"
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
          <el-form v-else label-position="left" label-width="200px" size="default">
            <el-form-item
              v-for="cf in filteredClassified"
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
const { loading, dynamicFormData, dynamicDescInfo, schemaData } = useProductTypeSchema(
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
 * dynamicFormData.site 仅含 otherFields，所以 classifiedFields 天然只有"更多属性"字段。
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

// ── 输入处理 ──

function onSiteInput(attrName: string, label: string, val: unknown[]) {
  dynamicFormData.site[attrName] = val;
  const valueStr = String((val?.[0] as Record<string, unknown>)?.value ?? "");
  const result = validateSiteLang(valueStr, siteCode.value, label);
  errors[`site.${attrName}`] = result.message;
}

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
}
</style>
