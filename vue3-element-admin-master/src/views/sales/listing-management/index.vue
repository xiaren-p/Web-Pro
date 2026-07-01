<template>
  <div class="listing-management">
    <TopNav :active-tab="activeTab" @update:active-tab="onTabChange" />
    <div class="listing-management__body">
      <component :is="activeComponent" />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 刊登管理主页面：顶部导航栏 + 动态 tab 内容区。
 * 使用 shallowRef 持有当前 tab 键，通过 <component :is> 动态渲染。
 * 不添加路由，由后台动态路由系统通过 component 字段 "sales/listing-management/index" 解析。
 */
import { shallowRef, markRaw } from "vue";
import TopNav from "./TopNav.vue";
import type { ListingTabKey } from "./TopNav.vue";
import MaterialsPage from "./MaterialsPage.vue";
import DraftsPage from "./DraftsPage.vue";
import PublishQueuePage from "./PublishQueuePage.vue";
import TemplatesPage from "./TemplatesPage.vue";
import BannedWordsPage from "./BannedWordsPage.vue";

defineOptions({ name: "SalesListingManagement" });

const tabMap: Record<ListingTabKey, ReturnType<typeof markRaw>> = {
  materials: markRaw(MaterialsPage),
  drafts: markRaw(DraftsPage),
  queue: markRaw(PublishQueuePage),
  templates: markRaw(TemplatesPage),
  banned: markRaw(BannedWordsPage),
};

const activeTab = shallowRef<ListingTabKey>("drafts");
const activeComponent = shallowRef(tabMap.drafts);

function onTabChange(key: ListingTabKey) {
  activeTab.value = key;
  activeComponent.value = tabMap[key];
}
</script>

<style scoped src="./index.scss" lang="scss"></style>
