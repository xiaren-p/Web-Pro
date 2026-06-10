<template>
  <div class="ad-campaign-detail p-6">
    <!-- 页头卡片 -->
    <div class="detail-header-card">
      <!-- 第一行：面包屑导航 -->
      <div class="breadcrumb-row">
        <span class="breadcrumb-link" @click="goBack">
          <el-icon class="back-icon"><ArrowLeft /></el-icon>
          全部广告
        </span>
        <span class="breadcrumb-sep">/</span>
        <span class="breadcrumb-current">广告活动详情</span>
      </div>

      <!-- 第二行：活动名称 + 类型徽标 -->
      <div class="title-row">
        <span v-if="campaignInfo?.targeting_type" class="targeting-badge">
          {{ formatTargetingType(campaignInfo.targeting_type) }}
        </span>
        <!-- 广告活动状态图标 -->
        <span
          v-if="campaignInfo?.state"
          class="campaign-state-icon"
          :class="`state-${campaignInfo.state}`"
        >
          <template v-if="campaignInfo.state === 'enabled'">
            <span class="dot-circle" />
          </template>
          <template v-else-if="campaignInfo.state === 'paused'">
            <el-icon><VideoPause /></el-icon>
          </template>
          <template v-else-if="campaignInfo.state === 'archived'">
            <el-icon><CircleClose /></el-icon>
          </template>
        </span>
        <h1 class="campaign-name">{{ campaignInfo?.name || campaignId }}</h1>
      </div>
    </div>

    <!-- 横向功能导航 Tab -->
    <el-tabs v-model="activeTab" class="detail-tabs">
      <el-tab-pane label="广告组" name="adgroups">
        <AdGroupsPanel
          :campaign-id="campaignId"
          :profile-id="profileId"
          :initial-date-range="inheritedDateRange"
        />
      </el-tab-pane>
      <el-tab-pane label="广告" name="ads">
        <AdsPanel
          :campaign-id="campaignId"
          :profile-id="profileId"
          :initial-date-range="inheritedDateRange"
        />
      </el-tab-pane>
      <el-tab-pane label="投放" name="targeting">
        <template v-if="campaignInfo?.targeting_type?.toUpperCase() === 'AUTO'">
          <AutoTargetingPanel
            :campaign-id="campaignId"
            :profile-id="profileId"
            :initial-date-range="inheritedDateRange"
          />
        </template>
        <template v-else>
          <KeywordPanel
            :campaign-id="campaignId"
            :profile-id="profileId"
            :initial-date-range="inheritedDateRange"
          />
        </template>
      </el-tab-pane>
      <el-tab-pane label="否定投放" name="negative">
        <template v-if="campaignInfo?.targeting_type?.toUpperCase() === 'AUTO'">
          <AutoNegativePanel
            :campaign-id="campaignId"
            :profile-id="profileId"
            :initial-date-range="inheritedDateRange"
          />
        </template>
        <template v-else>
          <NegativeKeywordPanel
            :campaign-id="campaignId"
            :profile-id="profileId"
            :initial-date-range="inheritedDateRange"
          />
        </template>
      </el-tab-pane>
      <el-tab-pane label="用户搜索词" name="search-terms">
        <template v-if="campaignInfo?.targeting_type?.toUpperCase() === 'AUTO'">
          <div class="tab-placeholder">自动 · 用户搜索词（占位）</div>
        </template>
        <template v-else>
          <div class="tab-placeholder">手动 · 用户搜索词（占位）</div>
        </template>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, VideoPause, CircleClose } from "@element-plus/icons-vue";
import { useLocalStorage } from "@vueuse/core";
import { getAdCampaignDetail, type AdCampaignDetailResponse } from "@/api/ads";
import AdGroupsPanel from "@/views/ads/detail/AdGroupsPanel.vue";
import AdsPanel from "@/views/ads/detail/AdsPanel.vue";
import AutoTargetingPanel from "@/views/ads/detail/AutoTargetingPanel.vue";
import AutoNegativePanel from "@/views/ads/detail/AutoNegativePanel.vue";
import KeywordPanel from "@/views/ads/detail/KeywordPanel.vue";
import NegativeKeywordPanel from "@/views/ads/detail/NegativeKeywordPanel.vue";

defineOptions({ name: "AdCampaignDetail" });

const route = useRoute();
const router = useRouter();

/** 当前激活的 Tab 标签（持久化，刷新后恢复上次所在 Tab） */
const activeTab = useLocalStorage<string>("ad_detail_active_tab", "adgroups");

/**
 * 从路由 query 中解析 campaign_id。
 *
 * @returns {string} 广告活动 ID，若不存在则返回空字符串。
 */
const campaignId = computed<string>(() => String(route.query.campaign_id ?? ""));

/**
 * 从路由 query 中解析 profile_id。
 *
 * @returns {string} 店铺 Profile ID，若不存在则返回空字符串。
 */
const profileId = computed<string>(() => String(route.query.profile_id ?? ""));

/**
 * 从路由 query 中解析父页面传入的日期范围，作为子面板的默认时间。
 * 若 date_start / date_end 均存在则构造二元数组，否则返回空数组。
 *
 * @returns {string[]} 格式为 ['YYYY-MM-DD', 'YYYY-MM-DD'] 的数组，或空数组
 */
const inheritedDateRange = computed<string[]>(() => {
  const start = String(route.query.date_start ?? "");
  const end = String(route.query.date_end ?? "");
  return start && end ? [start, end] : [];
});

/** 广告活动基础信息，通过 API 异步加载 */
const campaignInfo = ref<AdCampaignDetailResponse | null>(null);

/**
 * 将投放类型字段值格式化为中文显示。
 *
 * @param {string} val - targeting_type 原始值（AUTO / MANUAL）
 * @returns {string} 中文显示文字；无法识别则原样返回。
 */
function formatTargetingType(val: string): string {
  if (!val) return "";
  const map: Record<string, string> = { AUTO: "自动", MANUAL: "手动" };
  return map[val.toUpperCase()] ?? val;
}

/**
 * 返回广告活动列表页。
 */
function goBack(): void {
  router.back();
}

onMounted(() => {
  getAdCampaignDetail(campaignId.value, profileId.value)
    .then((res) => {
      campaignInfo.value = res;
    })
    .catch(() => {
      // 加载失败时保持展示 campaign_id 作为展示名称
    });
});
</script>

<style scoped lang="scss">
.ad-campaign-detail {
  /* ── 页头卡片 ── */
  .detail-header-card {
    padding: var(--spacing-4) var(--spacing-5) var(--spacing-4);
    margin-bottom: var(--spacing-4);
    background: #ffffff;
    border: 1px solid var(--color-gray-200);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-sm);
  }

  /* 第一行：面包屑 */
  .breadcrumb-row {
    display: flex;
    gap: var(--spacing-2);
    align-items: center;
    margin-bottom: var(--spacing-3);
    font-size: var(--font-size-sm);
  }

  .breadcrumb-link {
    display: inline-flex;
    gap: var(--spacing-1);
    align-items: center;
    padding: 4px 8px;
    font-weight: var(--font-weight-medium);
    color: var(--color-gray-500);
    cursor: pointer;
    border-radius: var(--radius-md);
    transition: all var(--transition-fast);

    &:hover {
      color: var(--color-primary-600);
      background: var(--color-primary-50);
    }
  }

  .back-icon {
    font-size: var(--font-size-xs);
  }

  .breadcrumb-sep {
    font-size: var(--font-size-sm);
    line-height: 1;
    color: var(--color-gray-300);
    user-select: none;
  }

  .breadcrumb-current {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-gray-700);
  }

  /* 第二行：标题 + 徽标 */
  .title-row {
    display: flex;
    gap: var(--spacing-3);
    align-items: center;
  }

  .targeting-badge {
    display: inline-flex;
    flex-shrink: 0;
    gap: 6px;
    align-items: center;
    padding: 3px 12px;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    line-height: 1.5;
    color: var(--color-primary-700);
    letter-spacing: 0.3px;
    background: var(--color-primary-50);
    border: 1px solid var(--color-primary-200);
    border-radius: var(--radius-full);
  }

  /* 状态图标 */
  .campaign-state-icon {
    display: inline-flex;
    flex-shrink: 0;
    align-items: center;
    font-size: var(--font-size-sm);
    line-height: 1;

    &.state-enabled {
      color: var(--color-success-500);

      .el-icon {
        font-size: 16px;
      }
    }

    .dot-circle {
      display: inline-block;
      flex-shrink: 0;
      width: 10px;
      height: 10px;
      background-color: currentcolor;
      border-radius: 50%;
      box-shadow: 0 0 0 3px var(--color-success-100);
    }

    &.state-paused {
      color: var(--color-gray-400);

      .el-icon {
        font-size: 16px;
      }
    }

    &.state-archived {
      color: var(--color-danger-500);

      .el-icon {
        font-size: 16px;
      }
    }
  }

  .campaign-name {
    margin: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    line-height: 1.4;
    color: var(--color-gray-900);
    white-space: nowrap;
  }

  /* ── 导航 Tab ── */
  .detail-tabs {
    :deep(.el-tabs__header) {
      padding: 0 var(--spacing-1);
      margin-bottom: 0;
      background: #ffffff;
      border: 1px solid var(--color-gray-200);
      border-bottom: none;
      border-radius: var(--radius-xl);
      border-bottom-right-radius: 0;
      border-bottom-left-radius: 0;
      box-shadow: var(--shadow-xs);
    }

    :deep(.el-tabs__nav-wrap::after) {
      height: 1px;
      background: var(--color-gray-200);
    }

    :deep(.el-tabs__item) {
      height: 44px;
      padding: 0 18px;
      font-size: var(--font-size-base);
      font-weight: var(--font-weight-medium);
      line-height: 44px;
      color: var(--color-gray-500);
      transition: color var(--transition-fast);

      &:hover {
        color: var(--color-primary-600);
      }

      &.is-active {
        font-weight: var(--font-weight-semibold);
        color: var(--color-primary-600);
      }
    }

    :deep(.el-tabs__active-bar) {
      height: 2px;
      border-radius: 2px;
    }
  }

  .tab-placeholder {
    padding: var(--spacing-8) 0;
    font-size: var(--font-size-base);
    color: var(--color-gray-400);
    text-align: center;
  }

  :deep(.el-tab-pane) {
    width: 100%;
  }
}
</style>
