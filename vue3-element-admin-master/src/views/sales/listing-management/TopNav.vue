<template>
  <nav class="listing-topnav">
    <div
      v-for="tab in tabs"
      :key="tab.key"
      class="listing-topnav__item"
      :class="tab.key === activeTab ? 'is-active' : ''"
      @click="handleTabClick(tab)"
    >
      <span class="listing-topnav__label">{{ tab.label }}</span>
    </div>
    <div
      class="listing-topnav__indicator"
      :style="{ transform: `translateX(${activeIndex * 100}%)` }"
    />
  </nav>
</template>

<script setup lang="ts">
/**
 * 刊登管理顶部导航栏：五个标签页切换。
 * 当前仅“草稿箱”为激活态，其余标签点击切换至对应占位页面。
 */
import { computed } from "vue";

export type ListingTabKey = "materials" | "drafts" | "queue" | "templates" | "banned";

interface TabItem {
  key: ListingTabKey;
  label: string;
}

const props = defineProps<{ activeTab: ListingTabKey }>();
const emit = defineEmits<{ "update:activeTab": [key: ListingTabKey] }>();

const tabs: TabItem[] = [
  { key: "materials", label: "资料库" },
  { key: "drafts", label: "草稿箱" },
  { key: "queue", label: "刊登队列" },
  { key: "templates", label: "刊登模板" },
  { key: "banned", label: "刊登禁用词" },
];

function handleTabClick(tab: TabItem) {
  emit("update:activeTab", tab.key);
}

const activeIndex = computed(() => tabs.findIndex((t) => t.key === props.activeTab));
</script>

<style scoped lang="scss">
.listing-topnav {
  position: relative;
  display: flex;
  flex-shrink: 0;
  gap: 24px;
  align-items: center;
  height: 48px;
  padding: 0 var(--spacing-4);
  background: var(--surface-base);
  border-bottom: 1px solid var(--border-subtle);

  &__item {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    font-size: var(--font-size-base);
    color: var(--text-secondary);
    cursor: pointer;
    transition: color var(--transition-ui);

    &:hover {
      color: var(--text-primary);
    }

    &.is-active {
      font-weight: var(--font-weight-semibold);
      color: var(--color-primary-600);
    }
  }

  &__label {
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
  }

  &__indicator {
    position: absolute;
    bottom: 0;
    left: var(--spacing-4);
    width: 64px;
    height: 3px;
    background: var(--color-primary-600);
    border-radius: var(--radius-full);
    transition: transform var(--transition-base);
  }
}
</style>
