<template>
  <div class="rule-strategy-page">
    <!-- 标题栏 -->
    <div class="page-title-bar">
      <div class="title-left">
        <el-icon class="title-icon" size="22"><Setting /></el-icon>
        <span class="title-text">SP 广告规则策略</span>
      </div>
      <span class="title-sub">管理广告自动规则与草稿箱</span>
    </div>

    <!-- 操作入口卡片 -->
    <div class="entry-row">
      <div class="entry-card" @click="(autoRuleDrawerRef as any)?.open()">
        <div class="entry-icon entry-icon--rule">
          <el-icon size="28"><Setting /></el-icon>
        </div>
        <div class="entry-info">
          <span class="entry-title">自动规则</span>
          <span class="entry-desc">
            创建规则组，按顺序执行组内规则。命中规则后自动调整竞价，无需手动干预。
          </span>
          <div class="entry-meta">
            <span class="entry-meta-item">
              <el-icon size="14"><Folder /></el-icon>
              {{ ruleGroups.length }} 个规则组
            </span>
            <span class="entry-meta-divider">·</span>
            <span class="entry-meta-item">
              <el-icon size="14"><Check /></el-icon>
              {{ ruleGroups.reduce((s, g) => s + g.rules.length, 0) }} 条生效规则
            </span>
          </div>
        </div>
        <el-icon class="entry-arrow" size="18"><ArrowRight /></el-icon>
      </div>

      <div class="entry-card" @click="(draftDrawerRef as any)?.open()">
        <div class="entry-icon entry-icon--draft">
          <el-icon size="28"><Document /></el-icon>
        </div>
        <div class="entry-info">
          <span class="entry-title">草稿箱</span>
          <span class="entry-desc">
            创建和编辑广告自动规则草稿，完成后可将规则添加到自动规则组中运行。
          </span>
          <div class="entry-meta">
            <span class="entry-meta-item">
              <el-icon size="14"><Edit /></el-icon>
              {{ draftRules.length }} 条草稿规则
            </span>
          </div>
        </div>
        <el-icon class="entry-arrow" size="18"><ArrowRight /></el-icon>
      </div>
    </div>

    <!-- 草稿箱抽屉 -->
    <DraftBoxDrawer ref="draftDrawerRef" :rules="draftRules" @update:rules="draftRules = $event" />

    <!-- 自动规则抽屉 -->
    <AutoRuleDrawer
      ref="autoRuleDrawerRef"
      :rules="draftRules"
      :rule-groups="ruleGroups"
      @update:rule-groups="ruleGroups = $event"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * SP 广告规则策略主页面：
 * 左侧卡片入口分别打开「自动规则」与「草稿箱」两个抽屉。
 * 规则数据暂存前端，后端接口就绪后对接 API 即可。
 *
 * 所属板块：tools / 广告规则策略。
 */
import type { AdRule, AdRuleGroup } from "@/views/tools/rule-strategy/types";

import { ref } from "vue";
import { Setting, Document, ArrowRight, Folder, Check, Edit } from "@element-plus/icons-vue";

import DraftBoxDrawer from "@/views/tools/rule-strategy/DraftBoxDrawer.vue";
import AutoRuleDrawer from "@/views/tools/rule-strategy/AutoRuleDrawer.vue";

defineOptions({ name: "RuleStrategy" });

// ── 数据状态（前端暂存，后端就绪后对接 API）──
const draftRules = ref<AdRule[]>([]);
const ruleGroups = ref<AdRuleGroup[]>([]);

// ── 子组件引用 ──
const draftDrawerRef = ref<any>(null);
const autoRuleDrawerRef = ref<any>(null);
</script>

<style scoped lang="scss">
.rule-strategy-page {
  max-width: 960px;
  padding: 28px 32px;
}

// ── 标题栏 ──
.page-title-bar {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 28px;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  color: #409eff;
}

.title-text {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
  letter-spacing: 0.02em;
}

.title-sub {
  font-size: 13px;
  color: #9ca3af;
}

// ── 入口卡片 ──
.entry-row {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.entry-card {
  display: flex;
  gap: 18px;
  flex: 1 1 400px;
  min-width: 360px;
  padding: 24px 20px;
  cursor: pointer;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  align-items: center;
  transition:
    box-shadow 0.2s,
    border-color 0.2s,
    transform 0.15s;

  &:hover {
    border-color: #c6ddfc;
    box-shadow: 0 4px 20px rgba(64, 158, 255, 0.08);
    transform: translateY(-2px);

    .entry-arrow {
      opacity: 1;
      transform: translateX(0);
    }
  }
}

.entry-icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 14px;

  &--rule {
    color: #409eff;
    background: linear-gradient(135deg, #ecf5ff 0%, #d4e5fc 100%);
  }

  &--draft {
    color: #e6a23c;
    background: linear-gradient(135deg, #fdf6ec 0%, #faecd8 100%);
  }
}

.entry-info {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
}

.entry-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.entry-desc {
  font-size: 13px;
  line-height: 1.6;
  color: #6b7280;
}

.entry-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 12px;
  color: #9ca3af;
}

.entry-meta-item {
  display: flex;
  align-items: center;
  gap: 3px;
}

.entry-meta-divider {
  user-select: none;
}

.entry-arrow {
  flex-shrink: 0;
  color: #c0c4cc;
  opacity: 0;
  transform: translateX(-8px);
  transition:
    opacity 0.2s,
    transform 0.2s;
}
</style>
