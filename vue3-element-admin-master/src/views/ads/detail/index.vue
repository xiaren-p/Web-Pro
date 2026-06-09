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
    padding: 14px 20px 16px;
    margin-bottom: 16px;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
  }

  /* 第一行：面包屑 */
  .breadcrumb-row {
    display: flex;
    gap: 6px;
    align-items: center;
    margin-bottom: 10px;
    font-size: 13px;
  }

  .breadcrumb-link {
    display: inline-flex;
    gap: 3px;
    align-items: center;
    font-weight: 400;
    color: #909399;
    cursor: pointer;
    transition: color 0.2s;

    &:hover {
      color: #409eff;
    }
  }

  .back-icon {
    font-size: 12px;
  }

  .breadcrumb-sep {
    font-size: 14px;
    line-height: 1;
    color: #dcdfe6;
    user-select: none;
  }

  .breadcrumb-current {
    font-size: 13px;
    color: #606266;
  }

  /* 第二行：标题 + 徽标 */
  .title-row {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .targeting-badge {
    display: inline-block;
    flex-shrink: 0;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
    line-height: 20px;
    color: #409eff;
    letter-spacing: 0.5px;
    background: #ecf5ff;
    border: 1px solid #b3d8ff;
    border-radius: 4px;
  }

  /* 状态图标 */
  .campaign-state-icon {
    display: inline-flex;
    flex-shrink: 0;
    align-items: center;
    font-size: 13px;
    line-height: 1;

    &.state-enabled {
      color: #22c55e;

      .el-icon {
        font-size: 15px;
      }
    }

    .dot-circle {
      display: inline-block;
      flex-shrink: 0;
      width: 10px;
      height: 10px;
      background-color: currentcolor;
      border-radius: 50%;
    }

    &.state-paused {
      color: #9ca3af;

      .el-icon {
        font-size: 15px;
      }
    }

    &.state-archived {
      color: #ef4444;

      .el-icon {
        font-size: 15px;
      }
    }
  }

  .campaign-name {
    margin: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 15px;
    font-weight: 600;
    line-height: 1.3;
    color: #1f2937;
    white-space: nowrap;
  }

  /* ── 导航 Tab ── */
  .detail-tabs {
    :deep(.el-tabs__header) {
      padding: 0 4px;
      margin-bottom: 0;
      background: #fff;
      border-radius: 8px 8px 0 0;
    }

    :deep(.el-tabs__nav-wrap::after) {
      height: 1px;
      background: #e5e7eb;
    }

    :deep(.el-tabs__item) {
      height: 44px;
      padding: 0 18px;
      font-size: 14px;
      font-weight: 500;
      line-height: 44px;
      color: #6b7280;
      transition: color 0.2s;

      &:hover {
        color: #409eff;
      }

      &.is-active {
        font-weight: 600;
        color: #409eff;
      }
    }

    :deep(.el-tabs__active-bar) {
      height: 2px;
      border-radius: 2px;
    }
  }

  .tab-placeholder {
    padding: 32px 0;
    font-size: 14px;
    color: #c0c4cc;
    text-align: center;
  }

  :deep(.el-tab-pane) {
    width: 100%;
  }
}
</style>
