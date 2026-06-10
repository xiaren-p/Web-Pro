<template>
  <div class="app-container">
    <!-- 标题行 -->
    <div class="page-header">
      <div class="page-header__left">
        <el-icon size="18" color="var(--el-color-primary)"><Setting /></el-icon>
        <h2 class="page-header__title">SP 广告规则策略</h2>
        <span class="page-header__divider">|</span>
        <span class="page-header__stat">
          {{ ruleGroups.length }} 规则组 ·
          {{ ruleGroups.reduce((s, g) => s + g.rules.length, 0) }} 生效规则 ·
          {{ draftRules.length }} 草稿
        </span>
      </div>
    </div>

    <!-- Tab -->
    <el-tabs v-model="activeTab">
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
.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;

  &__left {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  &__title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  &__divider {
    color: var(--el-border-color);
  }

  &__stat {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}
</style>
