/** * 刊登模板编辑器。 * * ============================================================ *
职责：创建/编辑刊登模板。 * ============================================================ * *
两种模式： * - 新增（无 query.id）：空表单 → 保存调 POST createTemplate * - 编辑（有
query.id）：加载详情回填 → 保存调 PUT updateTemplate * * 数据流： * 1. 加载市场列表 * 2. 用户选市场
+ 选商品类型（CategorySelectDialog） * 3. useProductTypeSchema 拉取 JSON Schema → otherFields
动态渲染 * 4. useFieldClassification 根据表单数据分类字段 * 5. DynamicField
路由组件根据分类结果选择子组件渲染 * 6. 编辑模式下加载 dataJson 回填（嵌套数组格式） * 7.
保存时直接使用模板表单数据（已匹配灵星 data_json 格式） * *
============================================================ * 数据格式（匹配灵星） *
============================================================ * * templateFormData[attrName] = [ * {
value: "商品名", marketplace_id: "ATVPDKIKX0DER" } * ] * * 组字段： * templateFormData[attrName] =
[{ * length: { value: 10, marketplace_id: "ATVPDKIKX0DER" }, * width: { value: 8, marketplace_id:
"ATVPDKIKX0DER" }, * marketplace_id: "ATVPDKIKX0DER", * }] */
<template>
  <div v-loading="loading || schemaLoading" class="template-editor">
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
          <div class="template-editor__section-header">基本信息</div>
          <el-form
            ref="formRef"
            label-position="left"
            label-width="300px"
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
        </section>

        <!-- 更多属性 -->
        <section id="more" class="template-editor__section">
          <div class="template-editor__section-header">更多属性</div>

          <!-- 工具栏 -->
          <div v-if="classifiedFields.length" class="template-editor__toolbar">
            <el-checkbox v-model="onlyShowRequired">仅查看必填字段</el-checkbox>
            <el-input
              v-model="searchText"
              placeholder="搜索字段名称"
              clearable
              size="small"
              class="template-editor__search"
            />
            <span class="template-editor__count">共 {{ classifiedFields.length }} 个字段</span>
          </div>

          <el-empty
            v-if="!filteredClassified.length && !schemaLoading"
            description="请先选择商品类型"
            :image-size="60"
          />
          <el-form v-else label-position="left" label-width="300px" size="default">
            <el-form-item
              v-for="cf in filteredClassified"
              :key="cf.attrName"
              :required="cf.requiredFields.length > 0"
            >
              <template #label>
                <div class="template-editor__label">
                  <p class="template-editor__label-zh">
                    <span v-if="cf.requiredFields.length > 0" class="template-editor__label-star">
                      *
                    </span>
                    {{ dynamicDescInfo[cf.attrName]?.label[0] ?? cf.attrName }}
                  </p>
                  <p class="template-editor__label-en">
                    {{ dynamicDescInfo[cf.attrName]?.label[1] ?? cf.attrName }}
                  </p>
                </div>
              </template>
              <DynamicField
                :field-config="dynamicDescInfo[cf.attrName]"
                :category="cf.category"
                :model-value="(templateFormData[cf.attrName] as unknown[]) ?? []"
                :required-fields="cf.requiredFields"
                :marketplace-id="form.marketplaceId"
                @update:model-value="(val: unknown[]) => onFieldInput(cf.attrName, val)"
              />
            </el-form-item>
          </el-form>
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
import { useFieldClassification } from "@/views/sales/listing-management/draft-editor/composables/useFieldClassification";
import CategorySelectDialog from "../draft-editor/components/CategorySelectDialog.vue";
import DynamicField from "../draft-editor/components/DynamicField.vue";

defineOptions({ name: "TemplateEditor" });

const route = useRoute();
const router = useRouter();

const isEditMode = computed(() => !!route.query.id);

const sections = [
  { key: "basic", label: "基本信息" },
  { key: "more", label: "更多属性" },
];

const activeSection = ref("basic");
const contentRef = ref<HTMLElement>();

const loading = ref(false);
const saving = ref(false);

const form = reactive({
  templateName: "",
  marketplaceId: "",
  productType: "",
  productTypeUniqueId: "",
  countryCode: "",
});

const marketplaceList = ref<MarketplaceVO[]>([]);
const showCategoryDialog = ref(false);
const searchText = ref("");
const onlyShowRequired = ref(false);

const {
  loading: schemaLoading,
  otherFields,
  dynamicDescInfo,
} = useProductTypeSchema(
  () => form.marketplaceId,
  () => form.productType
);

/** 模板动态字段数据（单栏，key=attrName, value=嵌套数组格式）。 */
const templateFormData = reactive<Record<string, any[]>>({});

/**
 * 初始化模板表单数据。
 *
 * @description 当 otherFields 变化时，为新字段初始化默认值。
 * 默认值格式：`[{ value: "", marketplace_id: form.marketplaceId }]`
 */
watch(otherFields, (fields) => {
  for (const field of fields) {
    if (!(field.attrName in templateFormData)) {
      templateFormData[field.attrName] = [{ value: "", marketplace_id: form.marketplaceId }];
    }
  }
});

/**
 * 分类后的字段列表。
 *
 * @description 根据 templateFormData 的当前值对字段分类。
 */
const classifiedFields = useFieldClassification(
  computed(() => templateFormData as Record<string, unknown[]>),
  computed(() => dynamicDescInfo.value)
);

/**
 * 过滤后的分类字段列表（搜索 + 仅必填）。
 */
const filteredClassified = computed(() => {
  let result = classifiedFields.value;

  if (searchText.value.trim()) {
    const search = searchText.value.trim().toUpperCase();
    result = result.filter((cf) => {
      const config = dynamicDescInfo.value[cf.attrName];
      if (!config) return false;
      return flattenFieldLabels(config).some((label) => label.includes(search));
    });
  }

  if (onlyShowRequired.value) {
    result = result.filter((cf) => cf.requiredFields.length > 0);
  }

  return result;
});

/**
 * 平滑滚动到指定 section。
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
 */
function onCategorySelect(category: AmazonCategoryVO) {
  form.productType = category.productTypeOrigin[0] || "";
  form.productTypeUniqueId = "";
}

/**
 * 动态字段输入处理。
 *
 * @param attrName - 字段名
 * @param val - 新的表单值（完整数组，灵星兼容格式）
 */
function onFieldInput(attrName: string, val: unknown[]) {
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
              if (Array.isArray(saved) && saved.length > 0) {
                // 直接使用保存的嵌套数组格式
                templateFormData[field.attrName] = JSON.parse(JSON.stringify(saved));
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
 *
 * @description 直接使用 templateFormData 中的嵌套数组格式作为 amazonData，
 * 与后端 data_json 字段格式完全匹配。
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
    /** 收集动态字段值（直接使用嵌套数组格式）。 */
    const amazonData: Record<string, unknown> = {};
    for (const field of otherFields.value) {
      if (templateFormData[field.attrName]) {
        amazonData[field.attrName] = templateFormData[field.attrName];
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

  /* ── 侧边栏（160px，居中菜单）── */
  &__sidebar {
    flex-shrink: 0;
    width: 160px;
    padding: 12px 0;
    overflow-y: auto;
    background: #fff;
  }

  &__nav-back {
    display: block;
    padding: 10px 0;
    font-size: var(--font-size-sm);
    color: var(--text-tertiary);
    text-align: center;
    cursor: pointer;
    transition: color var(--transition-ui);

    &:hover {
      color: var(--color-primary-600);
    }
  }

  &__nav-item {
    display: block;
    padding: 10px 0;
    text-align: center;
    cursor: pointer;
    transition: all var(--transition-ui);

    &:hover {
      color: var(--color-primary-600);
    }

    &.is-active {
      color: #005bf5;
      background-color: #e5effe;
    }
  }

  /* ── 右侧区域 ── */
  &__right {
    display: flex;
    flex: 1;
    flex-direction: column;
    width: calc(100% - 180px);
    min-height: 0;
  }

  &__content {
    flex: 1;
    height: calc(100% - 72px);
    padding: 12px 12px 0;
    overflow-y: auto;
    scroll-behavior: smooth;
  }

  /* ── section 卡片 ── */
  &__section {
    padding: 20px;
    margin-bottom: 10px;
    background-color: #fff;
    border-radius: 4px;
  }

  &__section-header {
    position: relative;
    display: flex;
    align-items: center;
    height: 22px;
    padding-left: 10px;
    margin-bottom: 20px;
    font-size: 13px;
    font-weight: 700;
    line-height: 22px;
    color: #0b1019;

    &::before {
      position: absolute;
      top: 4px;
      left: 0;
      width: 2px;
      height: 14px;
      content: "";
      background: #005bf5;
    }
  }

  &__input {
    width: 320px;
  }

  &__product-type {
    margin-right: 12px;
    font-size: var(--font-size-sm);
    color: var(--text-primary);
  }

  /* ── 工具栏 ── */
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

  /* ── 双语标签 ── */
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

  /* ── 底部操作栏 ── */
  &__footer {
    position: fixed;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 9;
    display: flex;
    gap: 20px;
    align-items: center;
    justify-content: center;
    padding: 20px 0;
    background: #fff;
    box-shadow: 0 4px 8px rgb(0 0 0 / 8%);

    :deep(.el-button) {
      min-width: 96px;
    }
  }
}
</style>
