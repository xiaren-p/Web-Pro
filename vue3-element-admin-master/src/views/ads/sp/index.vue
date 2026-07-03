<template>
  <div class="ads-text-container">
    <section class="content-block filter-panel-block">
      <Filters
        :filters="filters"
        :countries="countries"
        :profiles="filteredProfiles"
        :portfolios="portfolios"
        :sku-options="skuOptions"
        :tags-list="tagsList"
        :owners="owners"
        :campaign-statuses="campaignStatuses"
        :service-statuses="serviceStatuses"
        :bidding-types="biddingTypes"
        :remote-search-sku="remoteSearchSku"
        :remote-search-portfolio="remoteSearchPortfolio"
        @update:filters="(v) => Object.assign(filters, v)"
        @search="search"
        @reset="resetFilters"
        @open-templates="openSearchTemplates"
      />
    </section>

    <section class="content-block indicators-panel-block">
      <Indicators :summary="summary" />
    </section>

    <section class="content-block data-table-block">
      <div class="table-controls">
        <div class="left-controls">
          <div class="table-controls__title-group">
            <h2 class="table-controls__title">广告活动列表</h2>
            <span class="table-controls__summary">{{ tableColumns.length }} 个显示字段</span>
          </div>
          <el-dropdown @command="handleNewAdCommand">
            <el-button type="primary" class="primary-action-button">
              新建广告
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="upload">文件上传</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button class="queue-action-button" @click="queueDrawerVisible = true">
            查看队列
          </el-button>
        </div>

        <div class="right-controls">
          <el-checkbox v-model="onlyOverBudget" class="risk-switch">只查看超预算</el-checkbox>
          <el-tooltip content="列配置" placement="top">
            <el-button class="column-config-btn" @click="restoreDefaultColumns">
              <el-icon><Operation /></el-icon>
              列配置
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <AdsTable
        :loading="isLoading"
        :table-data="tableData"
        :page-size="pageSize"
        :current-page="currentPage"
        :total="total"
        :columns="tableColumns"
        :summary="summary"
        :date-range="filters.range"
        @current-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
        @sort-change="handleSortChange"
        @update-budget="onUpdateBudget"
        @update-state="onUpdateState"
        @batch-state="onBatchState"
        @batch-budget="onBatchBudgetOpen"
      />
    </section>

    <ColumnManager
      v-model="columnConfigVisible"
      :columns="activeColumns"
      @save="onColumnConfigSave"
    />

    <AdQueueDrawer v-model:visible="queueDrawerVisible" />
    <AdUploadDialog v-model:visible="uploadDialogVisible" @view-queue="queueDrawerVisible = true" />
    <BatchBudgetDialog
      v-model="batchBudgetDialogVisible"
      :items="batchBudgetItems"
      :currency-icon="batchBudgetCurrencyIcon"
      @confirm="onBatchBudgetConfirm"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 广告活动列表页。
 *
 * @description 薄编排层：组合 useAdCampaignList composable 与 Filters/Indicators/AdsTable 等子组件。
 *              筛选/分页/排序/列表加载/预算调整/批量操作全部在 composable 中。
 */
import { ArrowDown, Operation } from "@element-plus/icons-vue";
import Filters from "./Filters.vue";
import Indicators from "./Indicators.vue";
import AdsTable from "./AdsTable.vue";
import AdQueueDrawer from "./AdQueueDrawer.vue";
import AdUploadDialog from "./AdUploadDialog.vue";
import BatchBudgetDialog from "@/components/BatchBudgetDialog/index.vue";
import ColumnManager from "@/components/ColumnManager/index.vue";
import { useAdCampaignList } from "./composables/useAdCampaignList";

defineOptions({ name: "AdsText" });

const {
  isLoading,
  tableData,
  total,
  pageSize,
  currentPage,
  onlyOverBudget,
  summary,
  queueDrawerVisible,
  uploadDialogVisible,
  filters,
  countries,
  portfolios,
  biddingTypes,
  owners,
  tagsList,
  campaignStatuses,
  serviceStatuses,
  filteredProfiles,
  skuOptions,
  activeColumns,
  tableColumns,
  columnConfigVisible,
  restoreDefaultColumns,
  onColumnConfigSave,
  search,
  resetFilters,
  handlePageChange,
  handlePageSizeChange,
  handleSortChange,
  openSearchTemplates,
  handleNewAdCommand,
  remoteSearchSku,
  remoteSearchPortfolio,
  onUpdateBudget,
  onUpdateState,
  onBatchState,
  onBatchBudgetOpen,
  onBatchBudgetConfirm,
  batchBudgetDialogVisible,
  batchBudgetItems,
  batchBudgetCurrencyIcon,
} = useAdCampaignList();
</script>

<style scoped src="./ads.scss" lang="scss"></style>
