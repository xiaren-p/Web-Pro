<template>
  <div class="app-container">
    <!-- 标题行 -->
    <div class="page-header">
      <div class="page-header__left">
        <div class="page-header__icon-wrapper">
          <el-icon :size="22"><Setting /></el-icon>
        </div>
        <h2 class="page-header__title">SP 广告规则策略</h2>
        <span class="page-header__divider">|</span>
      </div>
      <div class="page-header__stat">
        <div class="stat-item">
          <span class="stat-value">{{ ruleGroups.length }}</span>
          <span class="stat-label">规则组</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ ruleGroups.reduce((s, g) => s + g.rules.length, 0) }}</span>
          <span class="stat-label">生效规则</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ draftRules.length }}</span>
          <span class="stat-label">草稿</span>
        </div>
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
  justify-content: space-between;
  padding: 20px 24px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.25);

  &__left {
    display: flex;
    gap: 14px;
    align-items: center;
  }

  &__icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    background: rgba(255, 255, 255, 0.18);
    border-radius: 10px;
    backdrop-filter: blur(8px);

    .el-icon {
      color: #fff;
    }
  }

  &__title {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.3px;
  }

  &__divider {
    font-weight: 300;
    color: rgba(255, 255, 255, 0.35);
  }

  &__stat {
    display: flex;
    gap: 18px;
    align-items: center;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.9);

    .stat-item {
      display: flex;
      gap: 6px;
      align-items: center;

      .stat-value {
        font-size: 16px;
        font-weight: 700;
        color: #fff;
      }

      .stat-label {
        opacity: 0.85;
      }
    }
  }
}

:deep(.el-tabs) {
  padding: 0 24px;
  background: var(--el-bg-color);
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);

  .el-tabs__header {
    padding: 0 24px;
    margin: 0 -24px 20px;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  .el-tabs__nav-wrap::after {
    display: none;
  }

  .el-tabs__item {
    height: 56px;
    font-size: 14px;
    font-weight: 500;
    line-height: 56px;
    color: var(--el-text-color-secondary);
    transition: all 0.25s ease;

    &:hover {
      color: var(--el-color-primary);
    }

    &.is-active {
      font-weight: 600;
      color: var(--el-color-primary);
    }
  }

  .el-tabs__active-bar {
    height: 3px;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    border-radius: 3px 3px 0 0;
  }
}
</style>
