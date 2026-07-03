<template>
  <div class="ad-campaign-detail p-6">
    <!-- 页头卡片 -->
    <div class="detail-header-card">
      <div class="breadcrumb-row">
        <span class="breadcrumb-link" @click="goBack">
          <el-icon class="back-icon"><ArrowLeft /></el-icon>
          SP 广告活动
        </span>
        <span class="breadcrumb-sep">/</span>
        <span class="breadcrumb-current">SP 广告活动详情</span>
      </div>

      <div class="title-row">
        <span v-if="campaignInfo?.targeting_type" class="targeting-badge">
          {{ formatTargetingType(campaignInfo.targeting_type) }}
        </span>
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
        <span v-if="campaignInfo?.profile_name" class="store-name">
          <el-icon class="store-icon"><Shop /></el-icon>
          {{ campaignInfo.profile_name }}
        </span>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="detail-tabs">
      <el-tab-pane label="广告组" name="adgroups">
        <div class="tab-indicators-wrapper">
          <Indicators v-if="activeSummary" :summary="activeSummary" />
        </div>
        <AdGroupsPanel
          ref="adGroupsRef"
          :campaign-id="campaignId"
          :profile-id="profileId"
          :inherited-date-range="inheritedDateRange"
          @keyword-bid="onKeywordBid"
          @keyword-state="onKeywordState"
        />
      </el-tab-pane>

      <el-tab-pane label="广告" name="ads">
        <div class="tab-indicators-wrapper">
          <Indicators v-if="activeSummary" :summary="activeSummary" />
        </div>
        <AdsPanel
          ref="adsRef"
          :campaign-id="campaignId"
          :profile-id="profileId"
          :inherited-date-range="inheritedDateRange"
          @keyword-bid="onKeywordBid"
          @keyword-state="onKeywordState"
        />
      </el-tab-pane>

      <el-tab-pane label="投放" name="targeting">
        <div class="tab-indicators-wrapper">
          <Indicators v-if="activeSummary" :summary="activeSummary" />
        </div>
        <template v-if="campaignInfo?.targeting_type?.toUpperCase() === 'AUTO'">
          <AutoTargetingPanel
            ref="autoTargetingRef"
            :campaign-id="campaignId"
            :profile-id="profileId"
            :inherited-date-range="inheritedDateRange"
            @target-bid="onTargetBid"
            @target-state="onTargetState"
          />
        </template>
        <template v-else>
          <div class="targeting-tabs-wrapper">
            <div class="targeting-subtabs">
              <el-radio-group v-model="targetingMode" size="small">
                <el-radio-button value="keyword">关键词投放</el-radio-button>
                <el-radio-button value="product">商品投放</el-radio-button>
              </el-radio-group>
            </div>
            <KeywordPanel
              v-if="targetingMode === 'keyword'"
              ref="keywordRef"
              :campaign-id="campaignId"
              :profile-id="profileId"
              :inherited-date-range="inheritedDateRange"
              @keyword-bid="onKeywordBid"
              @keyword-state="onKeywordState"
            />
            <ProductTargetingPanel
              v-else
              ref="productTargetingRef"
              :campaign-id="campaignId"
              :profile-id="profileId"
              :inherited-date-range="inheritedDateRange"
              @target-bid="onProductTargetBid"
              @target-state="onProductTargetState"
            />
          </div>
        </template>
      </el-tab-pane>

      <el-tab-pane label="否定投放" name="negative">
        <AutoNegativePanel :campaign-id="campaignId" :profile-id="profileId" />
        <NegativeKeywordPanel :campaign-id="campaignId" :profile-id="profileId" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
/**
 * 广告活动详情页。
 *
 * @description 薄编排层：组合 useCampaignDetail composable + 子面板组件。
 *              竞价修改/状态调整/活动加载逻辑全部在 composable 中。
 */
import { computed, ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, VideoPause, CircleClose, Shop } from "@element-plus/icons-vue";
import { useLocalStorage } from "@vueuse/core";
import AdGroupsPanel from "@/views/ads/sp/detail/AdGroupsPanel.vue";
import AdsPanel from "@/views/ads/sp/detail/AdsPanel.vue";
import AutoTargetingPanel from "@/views/ads/sp/detail/AutoTargetingPanel.vue";
import AutoNegativePanel from "@/views/ads/sp/detail/AutoNegativePanel.vue";
import KeywordPanel from "@/views/ads/sp/detail/KeywordPanel.vue";
import NegativeKeywordPanel from "@/views/ads/sp/detail/NegativeKeywordPanel.vue";
import ProductTargetingPanel from "@/views/ads/sp/detail/ProductTargetingPanel.vue";
import Indicators from "@/views/ads/sp/Indicators.vue";
import { useCampaignDetail } from "./composables/useCampaignDetail";

defineOptions({ name: "AdCampaignDetail" });

const route = useRoute();
const router = useRouter();

/** 持久化的激活 Tab。 */
const activeTab = useLocalStorage<string>("ad_detail_active_tab", "adgroups");

/** 路由参数：广告活动 ID。 */
const campaignId = computed<string>(() => String(route.query.campaign_id ?? ""));

/** 路由参数：店铺 Profile ID。 */
const profileId = computed<string>(() => String(route.query.profile_id ?? ""));

/** 父页面传入的日期范围。 */
const inheritedDateRange = computed<string[]>(() => {
  const start = String(route.query.date_start ?? "");
  const end = String(route.query.date_end ?? "");
  return start && end ? [start, end] : [];
});

const {
  campaignInfo,
  loadCampaignInfo,
  formatTargetingType,
  onKeywordBid,
  onKeywordState,
  onTargetBid,
  onTargetState,
  onProductTargetBid,
  onProductTargetState,
} = useCampaignDetail(campaignId, profileId);

/** 子面板组件引用（用于获取 summaryRow）。 */
const adGroupsRef = ref<InstanceType<typeof AdGroupsPanel>>();
const adsRef = ref<InstanceType<typeof AdsPanel>>();
const autoTargetingRef = ref<InstanceType<typeof AutoTargetingPanel>>();
const keywordRef = ref<InstanceType<typeof KeywordPanel>>();
const productTargetingRef = ref<InstanceType<typeof ProductTargetingPanel>>();

/** 手动投放 Tab 切换模式。 */
const targetingMode = ref<"keyword" | "product">("keyword");

/**
 * 当前激活 Tab 对应的汇总指标。
 */
const activeSummary = computed<Record<string, unknown> | null>(() => {
  switch (activeTab.value) {
    case "adgroups":
      return (adGroupsRef.value as any)?.summaryRow ?? null;
    case "ads":
      return (adsRef.value as any)?.summaryRow ?? null;
    case "targeting":
      if (campaignInfo.value?.targeting_type?.toUpperCase() === "AUTO") {
        return (autoTargetingRef.value as any)?.summaryRow ?? null;
      }
      if (targetingMode.value === "keyword") {
        return (keywordRef.value as any)?.summaryRow ?? null;
      }
      return (productTargetingRef.value as any)?.summaryRow ?? null;
    default:
      return null;
  }
});

/** 返回列表页。 */
function goBack(): void {
  router.back();
}

onMounted(() => {
  loadCampaignInfo();
});
</script>

<style scoped lang="scss">
.ad-campaign-detail {
  .detail-header-card {
    padding: var(--spacing-4) var(--spacing-5) var(--spacing-4);
    margin-bottom: 0;
    background: var(--el-bg-color);
    border: 1px solid var(--color-gray-200);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    box-shadow: var(--shadow-sm);
  }

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

  .store-name {
    display: flex;
    flex-shrink: 0;
    gap: 4px;
    align-items: center;
    padding: 2px 10px;
    font-size: 13px;
    color: var(--text-secondary);
    background: var(--surface-subtle);
    border-radius: var(--radius-md);
    .store-icon {
      font-size: 14px;
    }
  }

  .detail-tabs {
    :deep(.el-tabs__header) {
      padding: 0 var(--spacing-1);
      margin-bottom: 0;
      background: var(--el-bg-color);
      border: 1px solid var(--color-gray-200);
      border-top: none;
      border-radius: 0 0 var(--radius-xl) var(--radius-xl);
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

  .tab-indicators-wrapper {
    padding: 18px 4px 10px;
    margin-top: var(--spacing-4);
    margin-bottom: var(--spacing-3);
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid var(--color-gray-200);
    border-radius: var(--radius-xl);
  }

  :deep(.el-tab-pane) {
    width: 100%;
  }
}
</style>
