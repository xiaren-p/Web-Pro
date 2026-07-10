<template>
  <div class="draft-editor">
    <!-- 侧边栏：返回链接 + section 导航 -->
    <aside class="draft-editor__sidebar">
      <div class="draft-editor__nav-back" @click="router.back()">← 返回草稿箱</div>
      <div
        v-for="section in sections"
        :key="section.key"
        class="draft-editor__nav-item"
        :class="{ 'is-active': activeSection === section.key }"
        @click="scrollTo(section.key)"
      >
        {{ section.label }}
      </div>
    </aside>

    <!-- 右侧：内容区 + 底部操作栏 -->
    <div class="draft-editor__right">
      <main ref="contentRef" class="draft-editor__content">
        <BasicInfoSection id="basic" />
        <PricingSection id="pricing" />
        <ImagesSection id="images" />
        <DescriptionSection id="description" />
        <MoreAttributesSection id="more" />
      </main>

      <!-- 底部操作栏：居中显示 -->
      <footer class="draft-editor__footer">
        <el-button size="default" @click="router.back()">取消</el-button>
        <el-button size="default" @click="handleSave">保存</el-button>
        <el-button type="primary" size="default" :disabled="!canPublish" @click="handlePublish">
          发布
        </el-button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 刊登草稿编辑器主页面。
 *
 * 布局：左侧固定侧边栏（返回 + section 导航）+ 右侧内容区（滚动表单）+ 底部操作栏（居中）。
 * 状态管理：通过 provide/inject 将 formData 共享给各 section 子组件。
 * 语言校验：provide currentSiteCode，子组件实时校验站点语言/中文。
 * Scroll-spy：IntersectionObserver 监听各 section 可见性，高亮侧边栏对应项。
 *
 * 路由：静态路由 /sales/listing-management/draft-editor（hidden: true）
 */
import { reactive, ref, computed, onMounted, onBeforeUnmount, provide } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { extractSiteCode } from "@/utils/lang-check";
import BasicInfoSection from "./BasicInfoSection.vue";
import PricingSection from "./PricingSection.vue";
import ImagesSection from "./ImagesSection.vue";
import DescriptionSection from "./DescriptionSection.vue";
import MoreAttributesSection from "./MoreAttributesSection.vue";

defineOptions({ name: "DraftEditor" });

const router = useRouter();

/** section 导航配置 */
const sections = [
  { key: "basic", label: "基本信息" },
  { key: "pricing", label: "报价" },
  { key: "images", label: "图片" },
  { key: "description", label: "描述" },
  { key: "more", label: "更多属性" },
];

/** 创建单语表单字段模板 */
function createFormFields() {
  return {
    shop: "",
    marketplaceId: "",
    listingType: "",
    amazonCategory: "",
    productType: "",
    productName: "",
    productHighlights: "",
    brandName: "",
    packageLength: "",
    packageWidth: "",
    packageHeight: "",
    packageDimensionUnit: "Zentimeter",
    packageWeight: "",
    packageWeightUnit: "Pfund",
    salesType: "",
    deliveryChannel: "",
    msku: "",
    externalProductId: "",
    productCondition: "Neu",
    price: "",
    currency: "EUR",
    promotionPrice: "",
    promotionStartDate: "",
    promotionEndDate: "",
    productDescription: "",
    bulletPoints: ["", "", "", "", ""],
    manufacturer: "",
    operatingSystem: "",
    listPriceCurrency: "",
    listPriceWithTax: "",
    countryOfOrigin: "",
    batteryRequired: "",
    hazardousGoods: "",
  };
}

/** 草稿表单数据（通过 provide 共享给子组件） */
const formData = reactive({
  site: createFormFields(),
  cn: createFormFields(),
  images: [] as File[],
});

/** 当前站点代码（从店铺名称自动推导） */
const currentSiteCode = computed(() => extractSiteCode(formData.site.shop));

/** 语言校验错误记录（字段路径 → 错误信息） */
const langErrors = reactive<Record<string, string>>({});

/** 是否可以发布（无语言校验错误） */
const canPublish = computed(() => Object.values(langErrors).every((msg) => !msg));

provide("draftForm", formData);
provide("currentSiteCode", currentSiteCode);
provide("langErrors", langErrors);

/** 当前可见的 section key（scroll-spy 驱动） */
const activeSection = ref("basic");
const contentRef = ref<HTMLElement>();
let observer: IntersectionObserver | null = null;

/** 平滑滚动到指定 section */
function scrollTo(key: string) {
  document.getElementById(key)?.scrollIntoView({ behavior: "smooth" });
}

/** 保存草稿（占位） */
function handleSave() {
  ElMessage.success("草稿已保存");
}

/** 发布（占位，校验语言错误后才可点击） */
function handlePublish() {
  if (!canPublish.value) {
    ElMessage.warning("存在语言校验错误，请修正后再发布");
    return;
  }
  ElMessage.success("发布成功");
}

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) activeSection.value = e.target.id;
      }
    },
    { root: contentRef.value, threshold: 0.3 }
  );
  sections.forEach((s) => {
    const el = document.getElementById(s.key);
    if (el) observer!.observe(el);
  });
});

onBeforeUnmount(() => observer?.disconnect());
</script>

<style scoped lang="scss">
.draft-editor {
  display: flex;
  height: 100%;
  background: var(--app-bg);

  /* ── 侧边栏 ── */
  &__sidebar {
    flex-shrink: 0;
    width: 220px;
    padding: 0;
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

  /* ── 右侧区域 ── */
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

  /* ── 子 section 共享样式（穿透到子组件） ── */
  :deep(.draft-section) {
    margin-bottom: 24px;
  }

  :deep(.draft-section:last-child) {
    margin-bottom: 0;
  }

  :deep(.draft-section__header) {
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

  :deep(.draft-section__bar) {
    display: inline-block;
    width: 4px;
    height: 20px;
    background: var(--color-primary-600);
    border-radius: 2px;
  }

  :deep(.draft-section__body) {
    padding: 24px;
    background: var(--surface-base);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-xs);
  }

  :deep(.draft-col__header) {
    padding: 8px 12px;
    margin-bottom: 16px;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--text-secondary);
    background: var(--surface-subtle);
    border-radius: var(--radius-sm);
  }

  :deep(.draft-field-row) {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  :deep(.draft-field-hint) {
    margin-top: 4px;
    font-size: var(--font-size-xs);
    color: var(--text-tertiary);
  }

  :deep(.draft-field-unit) {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--text-secondary);
  }

  :deep(.draft-field-input--sm) {
    width: 120px;
  }

  :deep(.draft-field-input--md) {
    width: 200px;
  }

  :deep(.draft-field-input--lg) {
    width: 280px;
  }

  :deep(.lang-error) {
    .el-input__wrapper,
    .el-textarea__inner {
      box-shadow: 0 0 0 1px var(--color-danger-500) inset !important;
    }
  }

  :deep(.lang-error-hint) {
    margin-top: 4px;
    font-size: var(--font-size-xs);
    line-height: 1.4;
    color: var(--color-danger-500);
  }
}
</style>
