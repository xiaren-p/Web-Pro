<template>
  <div class="rule-strategy-page">
    <!-- 标题栏 -->
    <div class="page-title">
      <div class="title-left">
        <el-icon size="20">
          <Setting />
        </el-icon>
        <h2 class="title-text">SP 广告规则策略</h2>
      </div>
      <div class="title-right">
        <span class="stat">
          <strong>{{ ruleGroups.length }}</strong>
          规则组
        </span>
        <span class="stat-divider">|</span>
        <span class="stat">
          <strong>{{ ruleGroups.reduce((s, g) => s + g.rules.length, 0) }}</strong>
          生效规则
        </span>
        <span class="stat-divider">|</span>
        <span class="stat">
          <strong>{{ draftRules.length }}</strong>
          草稿
        </span>
      </div>
    </div>

    <!-- Tab -->
    <el-tabs v-model="activeTab" class="rule-tabs">
      <el-tab-pane label="自动规则" name="auto">
        <AutoRulePanel
          :rules="draftRules"
          :rule-groups="ruleGroups"
          @update:rule-groups="ruleGroups = $event"
        />
      </el-tab-pane>
      <el-tab-pane label="草稿箱" name="draft">
        <DraftBoxPanel :rules="draftRules" @update:rules="draftRules = $event" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
/**
 * SP 广告规则策略主页面。
 *
 * 所属板块：tools / 广告规则策略。
 */
import type { AdRule, AdRuleGroup } from "@/views/tools/rule-strategy/types";

import { ref, onMounted } from "vue";
import { Setting } from "@element-plus/icons-vue";

import DraftBoxPanel from "@/views/tools/rule-strategy/DraftBoxPanel.vue";
import AutoRulePanel from "@/views/tools/rule-strategy/AutoRulePanel.vue";
import { fetchRuleList, fetchGroupList } from "@/api/ads/rule-strategy";

defineOptions({ name: "RuleStrategy" });

const activeTab = ref("auto");
const draftRules = ref<AdRule[]>([]);
const ruleGroups = ref<AdRuleGroup[]>([]);

async function loadRuleData(): Promise<void> {
  try {
    const [ruleRes, groupRes] = await Promise.all([
      fetchRuleList({ pageSize: 500 }),
      fetchGroupList({ pageSize: 200 }),
    ]);
    draftRules.value = ruleRes.list ?? [];
    ruleGroups.value = groupRes.list ?? [];
  } catch {
    /* 接口未就绪 */
  }
}

onMounted(loadRuleData);
</script>

<style scoped lang="scss">
.rule-strategy-page {
  padding: 0;
}

.page-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 14px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.title-left {
  display: flex;
  gap: 8px;
  align-items: center;
  color: var(--el-color-primary);
}

.title-text {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.title-right {
  display: flex;
  gap: 14px;
  align-items: center;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.stat strong {
  margin-right: 2px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.stat-divider {
  color: var(--el-border-color);
}

.rule-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 16px;
  }

  :deep(.el-tabs__nav-wrap::after) {
    height: 1px;
  }
}
</style>
