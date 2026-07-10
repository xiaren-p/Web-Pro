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
      <span v-if="otherFields.length" class="more-attrs__count">
        共 {{ otherFields.length }} 个字段
      </span>
    </div>

    <el-row :gutter="24">
      <!-- 左栏：站点内容 -->
      <el-col :span="12">
        <div class="draft-col__header">站点内容</div>
        <div v-loading="loading" class="draft-section__body">
          <el-empty
            v-if="!filteredFields.length && !loading"
            description="暂无更多属性字段"
            :image-size="60"
          />
          <el-form v-else label-position="left" label-width="200px" size="default">
            <el-form-item
              v-for="field in filteredFields"
              :key="field.attrName"
              :label="field.label[1]"
              :required="field.required"
            >
              <DynamicField
                :model-value="dynamicFormData.site[field.attrName]"
                :field-config="field"
                @update:model-value="
                  (val: string) => onSiteInput(field.attrName, field.label[1], val)
                "
              />
              <div v-if="errors[`site.${field.attrName}`]" class="lang-error-hint">
                {{ errors[`site.${field.attrName}`] }}
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
            v-if="!filteredFields.length && !loading"
            description="暂无更多属性字段"
            :image-size="60"
          />
          <el-form v-else label-position="left" label-width="200px" size="default">
            <el-form-item
              v-for="field in filteredFields"
              :key="field.attrName"
              :label="field.label[0]"
              :required="field.required"
            >
              <DynamicField
                :model-value="dynamicFormData.cn[field.attrName]"
                :field-config="field"
                @update:model-value="
                  (val: string) => onCnInput(field.attrName, field.label[0], val)
                "
              />
              <div v-if="errors[`cn.${field.attrName}`]" class="lang-error-hint">
                {{ errors[`cn.${field.attrName}`] }}
              </div>
            </el-form-item>
          </el-form>
        </div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
/**
 * 更多属性 section：基于 Amazon JSON Schema 动态渲染。
 *
 * 数据流：
 * 1. 从 draftForm inject 获取 marketplaceId 和 productType
 * 2. useProductTypeSchema 监听两者，自动拉取 Schema 并解析
 * 3. otherFields（未归入 basic/quote/image/desc 的字段）动态渲染
 * 4. 工具栏：仅必填过滤 + 字段名搜索
 * 5. 双栏布局：左栏站点语言值，右栏中文值
 * 6. 文本字段实时校验语言（站点列校验站点语言，中文列校验中文）
 */
import { ref, computed, inject } from "vue";
import type { ComputedRef } from "vue";
import { Search as SearchIcon } from "@element-plus/icons-vue";
import { useProductTypeSchema, flattenFieldLabels } from "@/composables/useProductTypeSchema";
import { validateSiteLang, validateChinese } from "@/utils/lang-check";
import DynamicField from "./components/DynamicField.vue";

defineOptions({ name: "MoreAttributesSection" });

const f = inject<any>("draftForm");
const siteCode = inject<ComputedRef<string>>("currentSiteCode")!;
const errors = inject<Record<string, string>>("langErrors")!;

/** 从表单数据获取 marketplaceId 和 productType，驱动 Schema 拉取。 */
const { loading, otherFields, dynamicFormData } = useProductTypeSchema(
  () => f?.site?.marketplaceId ?? "",
  () => f?.site?.productType ?? ""
);

/** 搜索关键词。 */
const searchText = ref("");

/** 仅查看必填字段。 */
const onlyShowRequired = ref(false);

/** 过滤后的字段列表（搜索 + 仅必填）。 */
const filteredFields = computed(() => {
  let result = otherFields.value;

  if (searchText.value.trim()) {
    const search = searchText.value.trim().toUpperCase();
    result = result.filter((field) =>
      flattenFieldLabels(field).some((label) => label.includes(search))
    );
  }

  if (onlyShowRequired.value) {
    result = result.filter((field) => field.required);
  }

  return result;
});

/** 站点列输入处理 + 语言校验。 */
function onSiteInput(attrName: string, label: string, val: string) {
  dynamicFormData.site[attrName] = val;
  const result = validateSiteLang(val, siteCode.value, label);
  errors[`site.${attrName}`] = result.message;
}

/** 中文列输入处理 + 语言校验。 */
function onCnInput(attrName: string, label: string, val: string) {
  dynamicFormData.cn[attrName] = val;
  const result = validateChinese(val, label);
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
}
</style>
