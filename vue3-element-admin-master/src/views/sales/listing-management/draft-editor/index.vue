<template>
  <div class="draft-editor">
    <!-- 侧边栏 -->
    <aside class="draft-editor__sidebar">
      <div
        v-for="section in sections"
        :key="section.key"
        class="draft-editor__nav-item"
        :class="{ 'is-active': activeSection === section.key }"
        @click="scrollTo(section.key)"
      >
        {{ section.label }}
      </div>
      <div class="draft-editor__nav-back" @click="router.back()">← 返回草稿箱</div>
    </aside>

    <!-- 内容区 -->
    <main ref="contentRef" class="draft-editor__content">
      <BasicInfoSection :id="'basic'" />
      <PricingSection :id="'pricing'" />
      <ImagesSection :id="'images'" />
      <DescriptionSection :id="'description'" />
      <MoreAttributesSection :id="'more'" />
    </main>

    <!-- 底部操作栏 -->
    <footer class="draft-editor__footer">
      <el-button size="default" @click="router.back()">取消</el-button>
      <el-button size="default">保存</el-button>
      <el-button type="primary" size="default">发布</el-button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, onBeforeUnmount, provide } from "vue";
import { useRouter } from "vue-router";
import BasicInfoSection from "./BasicInfoSection.vue";
import PricingSection from "./PricingSection.vue";
import ImagesSection from "./ImagesSection.vue";
import DescriptionSection from "./DescriptionSection.vue";
import MoreAttributesSection from "./MoreAttributesSection.vue";

defineOptions({ name: "DraftEditor" });

const router = useRouter();

const sections = [
  { key: "basic", label: "基本信息" },
  { key: "pricing", label: "报价" },
  { key: "images", label: "图片" },
  { key: "description", label: "描述" },
  { key: "more", label: "更多属性" },
];

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

const activeSection = ref("basic");
const contentRef = ref<HTMLElement>();
let observer: IntersectionObserver | null = null;

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

  &__sidebar {
    position: sticky;
    top: 0;
    width: 200px;
    height: 100%;
    padding: 24px 0;
    overflow-y: auto;
    background: var(--surface-hover);
    border-right: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  &__nav-item {
    padding: 12px 24px;
    font-size: var(--font-size-base);
    color: var(--text-secondary);
    cursor: pointer;
    border-left: 3px solid transparent;
    transition: all var(--transition-ui);

    &:hover {
      color: var(--text-primary);
    }

    &.is-active {
      font-weight: var(--font-weight-semibold);
      color: var(--color-primary-600);
      background: var(--surface-base);
      border-left-color: var(--color-primary-600);
    }
  }

  &__nav-back {
    margin-top: auto;
    padding: 16px 24px;
    font-size: var(--font-size-sm);
    color: var(--text-tertiary);
    cursor: pointer;

    &:hover {
      color: var(--color-primary-600);
    }
  }

  &__content {
    flex: 1;
    padding: 24px;
    overflow-y: auto;
  }

  &__footer {
    position: sticky;
    bottom: 0;
    z-index: 10;
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    padding: 12px 24px;
    background: var(--surface-base);
    border-top: 1px solid var(--border-base);
  }
}
</style>
