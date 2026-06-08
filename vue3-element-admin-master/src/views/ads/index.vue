<template>
  <div class="ads-text-container p-6">
    <section class="content-block">
      <Filters
        :filters="filters"
        :countries="countries"
        :profiles="profiles"
        :ads-types="adsTypes"
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

    <!-- Toolbar removed here; controls consolidated into table-controls above AdsTable -->

    <!-- 指标统计（暂不展示） -->
    <section v-if="false" class="content-block">
      <Indicators />
    </section>

    <section class="content-block data-table-block">
      <div class="table-controls">
        <div class="left-controls">
          <!-- 新建广告：下拉选择操作类型 -->
          <el-dropdown @command="handleNewAdCommand">
            <el-button type="primary">
              新建广告
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="upload">文件上传</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- 查看队列 -->
          <el-button style="margin-left: 8px" @click="queueDrawerVisible = true">
            查看队列
          </el-button>
        </div>

        <div class="right-controls">
          <el-checkbox v-model="onlyOverBudget" style="margin-right: 8px">
            只查看超预算的
          </el-checkbox>
          <el-tooltip content="列配置" placement="top">
            <el-button
              text
              style="height: 22px; min-height: 22px; padding: 4px; font-size: 16px; color: #606266"
              @click="restoreDefaultColumns"
            >
              <el-icon><Operation /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <AdsTable
        :loading="loading"
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
      />
    </section>

    <ColumnManager
      v-model="columnConfigVisible"
      :columns="activeColumns"
      @save="onColumnConfigSave"
    />

    <!-- 广告上传队列抽屉 -->
    <AdQueueDrawer v-model:visible="queueDrawerVisible" />
    <!-- 新建广告上传对话框 -->
    <AdUploadDialog v-model:visible="uploadDialogVisible" @view-queue="queueDrawerVisible = true" />
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted, watch } from "vue";
import { ArrowDown, Operation } from "@element-plus/icons-vue";
import Filters from "./Filters.vue";
import Indicators from "./Indicators.vue";
import AdsTable from "./AdsTable.vue";
import AdQueueDrawer from "./AdQueueDrawer.vue";
import AdUploadDialog from "./AdUploadDialog.vue";
import ColumnManager from "@/components/ColumnManager/index.vue";
import { ElMessage } from "element-plus";
import { getAdCampaigns, getAdOptions, getAdPortfolioOptions } from "@/api/ads";

defineOptions({ name: "AdsText" });

// ── 广告上传队列 ──────────────────────────────────────────────────────────────
const queueDrawerVisible = ref(false);
const uploadDialogVisible = ref(false);
/**
 * 处理"新建广告"下拉命令：打开上传对话框。
 *
 * @param {string} command - 下拉项命令值，当前仅支持 "upload"
 */
function handleNewAdCommand(command: string): void {
  if (command === "upload") {
    uploadDialogVisible.value = true;
  }
}

// ── 广告列表 ──────────────────────────────────────────────────────────────────
const onlyOverBudget = ref(false);

// 切换超预算筛选时自动刷新表格
watch(onlyOverBudget, () => {
  currentPage.value = 1;
  loadTableData();
});

const countries = ref<{ value: string; label: string }[]>([]);
const profiles = ref<{ value: string; label: string }[]>([]);
const portfolios = ref<{ value: string; label: string }[]>([]);
const biddingTypes = ref<{ value: string; label: string }[]>([]);
const summary = ref<Record<string, unknown> | null>(null);

onMounted(() => {
  getAdOptions().then((res: any) => {
    countries.value = res.countries || [];
    profiles.value = res.profiles || [];
    biddingTypes.value = res.bidding_types || [];
  });

  remoteSearchPortfolio("");
});

const adsTypes = [{ value: "sp", label: "SP" }];

const tagsList = [
  { value: "unset", label: "未添加标签" },
  { value: "promo", label: "促销" },
  { value: "new", label: "新品" },
  { value: "clearance", label: "清仓" },
];

const owners = [
  { value: "it--1", label: "it--1" },
  { value: "罗奕明", label: "罗奕明" },
  { value: "彭承豪", label: "彭承豪" },
  { value: "李湧龙", label: "李湧龙" },
  { value: "孔颖娴", label: "孔颖娴" },
  { value: "肖娈", label: "肖娈" },
  { value: "pinx", label: "pinx" },
  { value: "刘浩珠", label: "刘浩珠" },
  { value: "陈慧瑩", label: "陈慧瑩" },
];

const campaignStatuses = [
  { value: "enabled", label: "已启用" },
  { value: "paused", label: "已暂停" },
  { value: "archived", label: "已归档" },
];

const serviceStatuses = [
  { value: "CAMPAIGN_STATUS_ENABLED", label: "投放中" },
  { value: "CAMPAIGN_PAUSED", label: "广告活动已暂停" },
  { value: "CAMPAIGN_ARCHIVED", label: "广告活动已归档" },
  { value: "CAMPAIGN_INCOMPLETE", label: "不完整" },
  { value: "CAMPAIGN_OUT_OF_BUDGET", label: "超预算" },
  { value: "ADVERTISER_PAYMENT_FAILURE", label: "广告账号付款失败" },
  { value: "LANDING_PAGE_NOT_AVAILABLE", label: "着陆页失效" },
  { value: "OTHER", label: "未知" },
];

const allSkus = [
  {
    value: "C-ZY-MZ03-BG",
    label: "C-ZY-MZ03-BG",
    title: "HEOXIN Baby Kinder Schalmütze (示例)",
    code: "B0DNDM458S",
    img: "https://images-cn.ssl-images-amazon.cn/images/I/51zo6Dtu3vL._SL75_.jpg",
    parent: "B0PARENT001",
  },
  {
    value: "C-ZY-MZ04-2PCS-S",
    label: "C-ZY-MZ04-2PCS-S",
    title: "HEOXIN Gorro de Bebé (示例)",
    code: "B0DNDLSQTX",
    img: "https://images-cn.ssl-images-amazon.cn/images/I/51PyS4uMXWL._SL75_.jpg",
    parent: "B0PARENT002",
  },
  {
    value: "K-HLS-BD001",
    label: "K-HLS-BD001",
    title: "KONFEN CPAP Nasenpolster (示例)",
    code: "B0GK1CCDY8",
    img: "https://images-cn.ssl-images-amazon.cn/images/I/31Zq3GnOUVL._SS60_.jpg",
    parent: "B0PARENT001",
  },
];

const skuOptions = ref(allSkus.slice());

const filters = reactive({
  countries: [] as string[],
  profiles: [] as string[],
  range: [] as string[],
  adsTypes: [] as string[],
  portfolios: [] as string[],
  asinSearchType: "sku",
  skus: [] as string[],
  biddingType: "",
  tags: [] as string[],
  owners: [] as string[],
  campaignName: "",
  campaignStatus: [] as string[],
  serviceStatus: [] as string[],
});

const columnConfigVisible = ref(false);

const defaultColumns = [
  // 设置
  { label: "服务状态", prop: "service_status", visible: true, category: "设置" },
  { label: "竞价策略", prop: "bidding_type", visible: true, category: "设置" },
  { label: "广告组合", prop: "portfolio_name", visible: true, category: "设置" },
  { label: "预算", prop: "budget", visible: true, category: "设置" },
  { label: "开始日期", prop: "startDate", visible: true, category: "设置" },
  { label: "标签", prop: "tags", visible: true, category: "设置" },
  // 转化
  { label: "IS", prop: "is", visible: true, category: "转化" },
  { label: "广告销售额", prop: "adsSales", visible: true, category: "转化" },
  { label: "广告销售额%", prop: "adsSalesPercent", visible: true, category: "转化" },
  { label: "直接销售额", prop: "directSales", visible: true, category: "转化" },
  { label: "广告订单", prop: "adsOrders", visible: true, category: "转化" },
  { label: "直接订单", prop: "directOrders", visible: true, category: "转化" },
  { label: "ACoS", prop: "acos", visible: true, category: "转化" },
  { label: "ROAS", prop: "roas", visible: true, category: "转化" },
  { label: "CVR", prop: "cvr", visible: true, category: "转化" },
  { label: "广告笔单价", prop: "adsOrderPrice", visible: true, category: "转化" },
  { label: "广告销量", prop: "adsVolume", visible: true, category: "转化" },
  // 业绩
  { label: "曝光量", prop: "impressions", visible: true, category: "业绩" },
  { label: "曝光%", prop: "impressionsPercent", visible: true, category: "业绩" },
  { label: "点击", prop: "clicks", visible: true, category: "业绩" },
  { label: "点击%", prop: "clicksPercent", visible: true, category: "业绩" },
  { label: "CTR", prop: "ctr", visible: true, category: "业绩" },
  { label: "CPC", prop: "cpc", visible: true, category: "业绩" },
  { label: "花费", prop: "spends", visible: true, category: "业绩" },
  { label: "花费%", prop: "spendsPercent", visible: true, category: "业绩" },
  { label: "CPA", prop: "cpa", visible: true, category: "业绩" },
];

const activeColumns = ref(defaultColumns);
const tableColumns = computed(() => activeColumns.value.filter((col) => col.visible));

function restoreDefaultColumns() {
  columnConfigVisible.value = true;
}

function onColumnConfigSave(columns: any[]) {
  activeColumns.value = columns;
  ElMessage.success("列配置已保存");
}

function remoteSearchSku(query: string) {
  if (!query) {
    skuOptions.value = allSkus.slice();
    return;
  }
  const q = query.toLowerCase();
  skuOptions.value = allSkus.filter((s) => (s.title + s.code + s.value).toLowerCase().includes(q));
}

function remoteSearchPortfolio(query: string = "") {
  getAdPortfolioOptions({ keyword: query }).then((res: any) => {
    portfolios.value = [{ value: "-1", label: "未设置广告组合" }, ...(res.portfolios || [])];
  });
}

function search() {
  currentPage.value = 1;
  loadTableData();
}

function resetFilters() {
  filters.countries = [];
  filters.profiles = [];
  filters.range = [];
  filters.adsTypes = [];
  filters.portfolios = [];
  filters.asinSearchType = "sku";
  filters.skus = [];
  filters.biddingType = "";
  filters.tags = [];
  filters.owners = [];
  filters.campaignName = "";
  filters.campaignStatus = [];
  filters.serviceStatus = [];
  currentPage.value = 1;
  loadTableData();
}

const tableData = ref([] as any[]);
const total = ref(0);
const pageSize = ref(25);
const currentPage = ref(1);

const loading = ref(false);
const sortParams = reactive({
  prop: "",
  order: "",
});

async function loadTableData() {
  loading.value = true;
  try {
    const params: any = {
      pageNum: currentPage.value,
      pageSize: pageSize.value,
      name: filters.campaignName,
      state: filters.campaignStatus.join(","),
      service_status: filters.serviceStatus.join(","),
      // 勾选“只查看超预算的”时，强制覆盖 service_status 为超预算状态
      ...(onlyOverBudget.value ? { service_status: "CAMPAIGN_OUT_OF_BUDGET" } : {}),
      sponsored_type: filters.adsTypes.join(","),
      portfolio_id: filters.portfolios.join(","),
      bidding_type: filters.biddingType,
      profiles: filters.profiles.join(","),
      countries: filters.countries.join(","),
      date_start: filters.range?.[0] || "",
      date_end: filters.range?.[1] || "",
    };

    if (sortParams.prop && sortParams.order) {
      params.sort_prop = sortParams.prop;
      params.sort_order = sortParams.order === "ascending" ? "asc" : "desc";
    }

    // 如果有组合或者其他可以在这里继续加

    const res = await getAdCampaigns(params);

    // 直接使用后端纯净的真实字段！前端列配置已对齐
    tableData.value = res.list || [];
    total.value = res.total || 0;
    summary.value = res.summary ?? null;
  } catch (error) {
    console.error(error);
    ElMessage.error("获取广告列表数据失败");
  } finally {
    loading.value = false;
  }
}

function handlePageChange(page: number) {
  currentPage.value = page;
  loadTableData();
}
function handlePageSizeChange(size: number) {
  pageSize.value = size;
  currentPage.value = 1;
  loadTableData();
}

function handleSortChange({ prop, order }: { prop: string; order: string }) {
  sortParams.prop = prop || "";
  sortParams.order = order || "";
  currentPage.value = 1;
  loadTableData();
}

function openSearchTemplates() {
  ElMessage.info("打开筛选模板（占位）");
}

loadTableData();
</script>

<style scoped src="./ads.scss" lang="scss"></style>
