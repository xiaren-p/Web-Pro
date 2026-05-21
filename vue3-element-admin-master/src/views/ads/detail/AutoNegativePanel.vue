<template>
  <div class="auto-negative-panel">
    <el-tabs v-model="activeSubTab" class="negative-sub-tabs">
      <el-tab-pane label="否定关键词" name="keywords">
        <negative-keyword-panel
          :campaign-id="campaignId"
          :profile-id="profileId"
          :initial-date-range="initialDateRange"
        />
      </el-tab-pane>
      <el-tab-pane label="否定商品" name="products">
        <auto-negative-targeting-panel
          :campaign-id="campaignId"
          :profile-id="profileId"
          :initial-date-range="initialDateRange"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
/**
 * 自动广告否定投放外层容器：包含"否定关键词"与"否定商品"两个子面板。
 * 所属板块：ads / 否定投放（仅自动广告类型展示）。
 */
import { ref } from "vue";

import NegativeKeywordPanel from "@/views/ads/detail/NegativeKeywordPanel.vue";
import AutoNegativeTargetingPanel from "@/views/ads/detail/AutoNegativeTargetingPanel.vue";

const props = defineProps<{
  campaignId: string;
  profileId: string;
  initialDateRange?: string[];
}>();

/** 当前激活的子 Tab（默认否定关键词） */
const activeSubTab = ref<string>("keywords");
</script>

<style scoped lang="scss">
.auto-negative-panel {
  .negative-sub-tabs {
    :deep(.el-tabs__header) {
      margin-bottom: 0;
    }

    :deep(.el-tabs__nav-wrap::after) {
      height: 1px;
    }
  }
}
</style>
