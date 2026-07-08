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

      <!-- 底部操作栏：横跨侧边栏+内容区下方 -->
      <footer class="draft-editor__footer">
        <el-button size="default" @click="router.back()">取消</el-button>
        <el-button size="default">保存</el-button>
        <el-button type="primary" size="default">发布</el-button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 刊登草稿编辑器主页面。
 *
 * 布局：左侧固定侧边栏（返回 + section 导航）+ 右侧内容区（滚动表单）+ 底部操作栏。
 * 状态管理：通过 provide/inject 将 formData 共享给各 section 子组件。
 * Scroll-spy：IntersectionObserver 监听各 section 可见性，高亮侧边栏对应项。
 *
 * 路由：静态路由 /sales/listing-management/draft-editor（hidden: true）
 */
import { reactive, ref, onMounted, onBeforeUnmount, provide } from "vue";
import { useRouter } from "vue-router";
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

/** 草稿表单数据（通过 provide 共享给子组件） */
const formData = reactive({
  shop: "",
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
  images: [] as File[],
  productDescription: "",
  bulletPoints: ["", "", "", "", ""],
  manufacturer: "",
  operatingSystem: "",
  listPriceCurrency: "",
  listPriceWithTax: "",
  countryOfOrigin: "",
  batteryRequired: "",
  hazardousGoods: "",
});

provide("draftForm", formData);

/** 当前可见的 section key（scroll-spy 驱动） */
const activeSection = ref("basic");
const contentRef = ref<HTMLElement>();
let observer: IntersectionObserver | null = null;

/** 平滑滚动到指定 section */
function scrollTo(key: string) {
  document.getElementById(key)?.scrollIntoView({ behavior: "smooth" });
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
    width: 220px;
    padding: 0;
    overflow-y: auto;
    background: var(--surface-base);
    border-right: 1px solid var(--border-base);
    box-shadow: 2px 0 8px rgb(15 23 42 / 4%);
    flex-shrink: 0;
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
    gap: 12px;
    justify-content: flex-end;
    padding: 14px 32px;
    background: var(--surface-base);
    border-top: 1px solid var(--border-base);
    box-shadow: 0 -2px 8px rgb(15 23 42 / 4%);
    flex-shrink: 0;
  }

  /* ── 子 section 共享样式（穿透到子组件） ── */
  :deep(.draft-section) {
    margin-bottom: 24px;

    &:last-child {
      margin-bottom: 0;
    }

    &__header {
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

    &__bar {
      display: inline-block;
      width: 4px;
      height: 20px;
      background: var(--color-primary-600);
      border-radius: 2px;
    }

    &__body {
      padding: 24px;
      background: var(--surface-base);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow-xs);
    }
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
}
</style>
