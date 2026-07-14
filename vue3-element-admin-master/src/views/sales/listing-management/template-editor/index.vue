<template>
  <div v-loading="loading" class="template-editor">
    <!-- 侧边导航 -->
    <aside class="template-editor__sidebar">
      <div class="template-editor__nav-back" @click="router.back()">← 返回模板列表</div>
      <div
        v-for="section in sections"
        :key="section.key"
        class="template-editor__nav-item"
        :class="{ 'is-active': activeSection === section.key }"
        @click="scrollTo(section.key)"
      >
        {{ section.label }}
      </div>
    </aside>

    <!-- 右侧内容 + 底部操作 -->
    <div class="template-editor__right">
      <main ref="contentRef" class="template-editor__content">
        <!-- 基本信息 -->
        <section id="basic" class="template-editor__section">
          <div class="template-editor__section-header">
            <span class="template-editor__section-bar" />
            基本信息
          </div>
          <div class="template-editor__section-body">
            <el-form
              ref="formRef"
              label-position="left"
              label-width="200px"
              size="default"
              :model="form"
            >
              <el-form-item label="模板名称" required>
                <el-input
                  v-model="form.templateName"
                  maxlength="50"
                  show-word-limit
                  clearable
                  placeholder="请输入模板名称"
                  class="template-editor__input"
                />
              </el-form-item>
              <el-form-item label="国家/市场" required>
                <el-select
                  v-model="form.marketplaceId"
                  filterable
                  placeholder="请选择市场"
                  class="template-editor__input"
                  @change="onMarketplaceChange"
                >
                  <el-option
                    v-for="m in marketplaceList"
                    :key="m.marketplaceId"
                    :label="`${m.country} (${m.code})`"
                    :value="m.marketplaceId"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="商品类型" required>
                <span v-if="form.productType" class="template-editor__product-type">
                  {{ form.productType }}
                </span>
                <el-button
                  size="small"
                  :disabled="!form.marketplaceId"
                  @click="showCategoryDialog = true"
                >
                  {{ form.productType ? "更改商品类型" : "选择商品类型" }}
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </section>

        <!-- 更多属性 -->
        <section id="more" class="template-editor__section">
          <div class="template-editor__section-header">
            <span class="template-editor__section-bar" />
            更多属性
          </div>

          <!-- 工具栏 -->
          <div v-if="otherFields.length" class="template-editor__toolbar">
            <el-checkbox v-model="onlyShowRequired">仅查看必填字段</el-checkbox>
            <el-input
              v-model="searchText"
              placeholder="搜索字段名称"
              clearable
              size="small"
              class="template-editor__search"
            />
            <span class="template-editor__count">共 {{ otherFields.length }} 个字段</span>
          </div>

          <div class="template-editor__section-body">
            <el-empty
              v-if="!filteredFields.length && !loading"
              description="请先选择商品类型"
              :image-size="60"
            />
            <template v-else>
              <div
                v-for="group in groupedFields"
                :key="group.key"
                class="template-editor__field-group"
              >
                <div class="template-editor__field-group-title">{{ group.title }}</div>
                <div class="template-editor__section-body template-editor__section-body--flush">
                  <el-form label-position="left" label-width="200px" size="default">
                    <el-form-item
                      v-for="field in group.fields"
                      :key="field.attrName"
                      :required="field.required"
                    >
                      <template #label>
                        <div class="template-editor__label">
                          <p class="template-editor__label-zh">
                            <span v-if="field.required" class="template-editor__label-star">*</span>
                            {{ field.label[0] }}
                          </p>
                          <p class="template-editor__label-en">{{ field.label[1] }}</p>
                        </div>
                      </template>
                      <DynamicField
                        :model-value="templateFormData[field.attrName]"
                        :field-config="field"
                        @update:model-value="(val: string) => onFieldInput(field.attrName, val)"
                      />
                    </el-form-item>
                  </el-form>
                </div>
              </div>
            </template>
          </div>
        </section>
      </main>

      <!-- 底部操作栏 -->
      <footer class="template-editor__footer">
        <el-button @click="router.back()">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </footer>
    </div>

    <!-- 分类选择弹窗 -->
    <CategorySelectDialog
      v-model:visible="showCategoryDialog"
      :marketplace-id="form.marketplaceId"
      @select="onCategorySelect"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 刊登模板编辑器。
 *
 * 两种模式：
 * - 新增（无 query.id）：空表单 -> 保存调 POST createTemplate
 * - 编辑（有 query.id）：加载详情回填 -> 保存调 PUT updateTemplate
 *
 * 数据流：
 * 1. 加载市场列表（LxMarketplace）
 * 2. 用户选市场 + 选商品类型（CategorySelectDialog）
 * 3. useProductTypeSchema 拉取 JSON Schema -> otherFields 动态渲染
 * 4. 编辑模式下加载 dataJson 回填动态字段
 * 5. 保存时收集动态字段 -> amazonData -> API
 */
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { ListingPublishAPI } from "@/api/sales/listing-publish";
import type {
  MarketplaceVO,
  AmazonCategoryVO,
  PublishTemplateForm,
} from "@/api/sales/listing-publish";
import { useProductTypeSchema, flattenFieldLabels } from "@/composables/useProductTypeSchema";
import type { ParsedFieldConfig } from "@/composables/useProductTypeSchema";
import CategorySelectDialog from "../draft-editor/components/CategorySelectDialog.vue";
import DynamicField from "../draft-editor/components/DynamicField.vue";

defineOptions({ name: "TemplateEditor" });

const route = useRoute();
const router = useRouter();

/** 是否编辑模式。 */
const isEditMode = computed(() => !!route.query.id);

/** section 导航。 */
const sections = [
  { key: "basic", label: "基本信息" },
  { key: "more", label: "更多属性" },
];

/** 当前可见 section。 */
const activeSection = ref("basic");
const contentRef = ref<HTMLElement>();

/** 全局加载/保存状态。 */
const loading = ref(false);
const saving = ref(false);

/** 基本信息表单。 */
const form = reactive({
  templateName: "",
  marketplaceId: "",
  productType: "",
  productTypeUniqueId: "",
  countryCode: "",
});

/** 市场列表。 */
const marketplaceList = ref<MarketplaceVO[]>([]);

/** 分类弹窗状态。 */
const showCategoryDialog = ref(false);

/** 搜索 + 仅必填。 */
const searchText = ref("");
const onlyShowRequired = ref(false);

/**
 * 使用 ProductTypeSchema composable 解析动态字段。
 * 监听 form.marketplaceId + form.productType，两者有值时自动拉取。
 * 模板编辑器使用单栏（不需要 site/cn 双栏），因此用自己的 formData。
 */
const { otherFields, propertyGroups } = useProductTypeSchema(
  () => form.marketplaceId,
  () => form.productType
);

/** 模板动态字段数据（单栏，key=attrName, value=字符串）。 */
const templateFormData = reactive<Record<string, string>>({});

/** 监听 otherFields 变化，初始化表单数据。 */
watch(otherFields, (fields) => {
  for (const field of fields) {
    if (!(field.attrName in templateFormData)) {
      templateFormData[field.attrName] = "";
    }
  }
});

/** 过滤后的字段列表（搜索 + 仅必填）。 */
const filteredFields = computed<ParsedFieldConfig[]>(() => {
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

/** 字段名 → 分组 key 映射（从 propertyGroups 构建）。 */
const fieldGroupMap = computed(() => {
  const map: Record<string, string> = {};
  for (const [groupKey, group] of Object.entries(propertyGroups.value)) {
    for (const fieldName of group.propertyNames) {
      map[fieldName] = groupKey;
    }
  }
  return map;
});

/** 按分组排列的字段列表。 */
const groupedFields = computed(() => {
  const groups: { key: string; title: string; fields: ParsedFieldConfig[] }[] = [];
  const seen = new Set<string>();
  const groupOrder: string[] = [];

  for (const field of filteredFields.value) {
    const gk = fieldGroupMap.value[field.attrName] || "product_details";
    if (!seen.has(gk)) {
      seen.add(gk);
      groupOrder.push(gk);
      groups.push({
        key: gk,
        title: propertyGroups.value[gk]?.title || gk,
        fields: [],
      });
    }
    groups[groupOrder.indexOf(gk)].fields.push(field);
  }
  return groups;
});

/**
 * 平滑滚动到指定 section。
 *
 * @param key - section 标识。
 */
function scrollTo(key: string) {
  document.getElementById(key)?.scrollIntoView({ behavior: "smooth" });
}

/**
 * 加载市场列表。
 */
async function loadMarketplaces() {
  try {
    marketplaceList.value = await ListingPublishAPI.getMarketplaces();
  } catch {
    marketplaceList.value = [];
  }
}

/**
 * 市场变更时重置商品类型。
 */
function onMarketplaceChange() {
  form.productType = "";
  form.productTypeUniqueId = "";
}

/**
 * 分类选中回调：设商品类型，触发 Schema 拉取。
 *
 * @param category - 选中的分类节点。
 */
function onCategorySelect(category: AmazonCategoryVO) {
  form.productType = category.productTypeOrigin[0] || "";
  form.productTypeUniqueId = "";
}

/**
 * 动态字段输入处理。
 *
 * @param attrName - 字段名。
 * @param val - 输入值。
 */
function onFieldInput(attrName: string, val: string) {
  templateFormData[attrName] = val;
}

/**
 * 编辑模式：加载模板详情并回填。
 */
async function loadTemplateDetail() {
  if (!isEditMode.value) return;
  loading.value = true;
  try {
    const detail = await ListingPublishAPI.getTemplateForm(String(route.query.id));
    form.templateName = detail.templateName;
    form.marketplaceId = detail.marketplaceId;
    form.productType = detail.productType;
    form.productTypeUniqueId = detail.productTypeUniqueId;
    form.countryCode = detail.countryCode;

    // 等 Schema 拉取完成后回填动态字段
    if (detail.dataJson) {
      watch(
        otherFields,
        (fields) => {
          if (fields.length) {
            for (const field of fields) {
              const saved = (detail.dataJson as Record<string, unknown>)[field.attrName];
              if (Array.isArray(saved) && saved[0] && typeof saved[0] === "object") {
                templateFormData[field.attrName] = String(
                  (saved[0] as Record<string, unknown>).value ?? ""
                );
              }
            }
          }
        },
        { once: true }
      );
    }
  } catch {
    ElMessage.error("加载模板详情失败");
  } finally {
    loading.value = false;
  }
}

/**
 * 保存模板（新增或编辑）。
 */
async function handleSave() {
  if (!form.templateName.trim()) {
    ElMessage.warning("请输入模板名称");
    return;
  }
  if (!form.marketplaceId || !form.productType) {
    ElMessage.warning("请选择市场和商品类型");
    return;
  }

  saving.value = true;
  try {
    /** 将动态字段值转换为 Amazon data_json 格式。 */
    const amazonData: Record<string, unknown> = {};
    for (const field of otherFields.value) {
      if (templateFormData[field.attrName]) {
        amazonData[field.attrName] = [
          { value: templateFormData[field.attrName], marketplace_id: form.marketplaceId },
        ];
      }
    }

    const payload: PublishTemplateForm = {
      templateName: form.templateName.trim(),
      marketplaceId: form.marketplaceId,
      productType: form.productType,
      productTypeUniqueId: form.productTypeUniqueId,
      countryCode: form.countryCode,
      amazonData,
    };

    if (isEditMode.value) {
      await ListingPublishAPI.updateTemplate(String(route.query.id), payload);
      ElMessage.success("模板已更新");
    } else {
      await ListingPublishAPI.createTemplate(payload);
      ElMessage.success("模板已创建");
    }
    router.back();
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  await loadMarketplaces();
  if (isEditMode.value) {
    await loadTemplateDetail();
  }
});
</script>

<style scoped lang="scss">
.template-editor {
  display: flex;
  height: 100%;
  background: var(--app-bg);

  &__sidebar {
    flex-shrink: 0;
    width: 220px;
    overflow-y: auto;
    background: var(--surface-base);
    border-right: 1px solid var(--border-base);
    box-shadow: 2px 0 8px rgb(15 23 42 / 4%);
  }

  &__nav-back {
    padding: 18px 24px;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--text-tertiary);
    cursor: pointer;
    border-bottom: 1px solid var(--border-subtle);
    transition: color var(--transition-ui);

    &:hover {
      color: var(--color-primary-600);
    }
  }

  &__nav-item {
    padding: 14px 24px;
    font-size: var(--font-size-base);
    color: var(--text-secondary);
    cursor: pointer;
    border-left: 3px solid transparent;
    transition: all var(--transition-ui);

    &:hover {
      color: var(--text-primary);
      background: var(--surface-subtle);
    }

    &.is-active {
      font-weight: var(--font-weight-semibold);
      color: var(--color-primary-600);
      background: var(--color-primary-50);
      border-left-color: var(--color-primary-600);
    }
  }

  &__right {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
  }

  &__content {
    flex: 1;
    padding: 28px 32px;
    overflow-y: auto;
  }

  &__section {
    margin-bottom: 24px;
  }

  &__section-header {
    display: flex;
    gap: 10px;
    align-items: center;
    padding-bottom: 14px;
    margin-bottom: 20px;
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    border-bottom: 2px solid var(--border-subtle);
  }

  &__section-bar {
    display: inline-block;
    width: 4px;
    height: 20px;
    background: var(--color-primary-600);
    border-radius: 2px;
  }

  &__section-body {
    padding: 24px;
    background: var(--surface-base);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-xs);

    &--flush {
      margin-bottom: 0;
      border-top: 0;
      border-radius: 0 0 var(--radius-xl) var(--radius-xl);
      box-shadow: none;
    }
  }

  &__field-group {
    margin-bottom: 16px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  &__field-group-title {
    padding: 10px 24px;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    background: var(--surface-subtle);
    border: 1px solid var(--border-subtle);
    border-bottom: 0;
    border-radius: var(--radius-md) var(--radius-md) 0 0;
  }

  &__input {
    width: 320px;
  }

  &__product-type {
    margin-right: 12px;
    font-size: var(--font-size-sm);
    color: var(--text-primary);
  }

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
      color: #f5222d;
      font-size: 10px;
      margin-right: 4px;
    }
  }

  &__footer {
    display: flex;
    flex-shrink: 0;
    gap: 12px;
    justify-content: center;
    padding: 14px 32px;
    background: var(--surface-base);
    border-top: 1px solid var(--border-base);
    box-shadow: 0 -2px 8px rgb(15 23 42 / 4%);
  }
}
</style>
