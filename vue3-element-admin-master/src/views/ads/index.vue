<template>
  <div class="ads-text-container p-6">
    <section class="content-block">
      <Filters
        :filters="filters"
        :countries="countries"
        :profiles="profiles"
        :ads-types="adsTypes"
        :target-types="targetTypes"
        :portfolios="portfolios"
        :sku-options="skuOptions"
        :tags-list="tagsList"
        :owners="owners"
        :campaign-statuses="campaignStatuses"
        :service-statuses="serviceStatuses"
        :remote-search-sku="remoteSearchSku"
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
          <!-- 预留左侧操作区可以放批量操作按钮等 -->
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
        @current-change="handlePageChange"
        @view-row="viewRow"
        @edit-row="editRow"
        @page-size-change="handlePageSizeChange"
      />
    </section>

    <ColumnManager
      v-model="columnConfigVisible"
      :columns="activeColumns"
      @save="onColumnConfigSave"
    />
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from "vue";
import { Operation } from "@element-plus/icons-vue";
import Filters from "./Filters.vue";
import Indicators from "./Indicators.vue";
import AdsTable from "./AdsTable.vue";
import ColumnManager from "@/components/ColumnManager/index.vue";
import { ElMessage } from "element-plus";
import { getAdCampaigns } from "@/api/ads";

defineOptions({ name: "AdsText" });

const onlyOverBudget = ref(false);

const countries = [
  { value: "UK", label: "英国" },
  { value: "FR", label: "法国" },
  { value: "IT", label: "意大利" },
  { value: "ES", label: "西班牙" },
  { value: "DE", label: "德国" },
  { value: "NL", label: "荷兰" },
  { value: "SE", label: "瑞典" },
  { value: "PL", label: "波兰" },
  { value: "BE", label: "比利时" },
];

const profiles = [
  { value: "hanlis-DE", label: "hanlis-DE" },
  { value: "hanlis-ES", label: "hanlis-ES" },
  { value: "hanlis-FR", label: "hanlis-FR" },
  { value: "hanlis-IT", label: "hanlis-IT" },
  { value: "hanlis-NL", label: "hanlis-NL" },
  { value: "hanlis-PL", label: "hanlis-PL" },
  { value: "hanlis-SE", label: "hanlis-SE" },
  { value: "hanlis-UK", label: "hanlis-UK" },
  { value: "pinx-BE", label: "pinx-BE" },
  { value: "pinx-DE", label: "pinx-DE" },
  { value: "pinx-ES", label: "pinx-ES" },
  { value: "pinx-FR", label: "pinx-FR" },
  { value: "pinx-IT", label: "pinx-IT" },
  { value: "pinx-NL", label: "pinx-NL" },
  { value: "pinx-PL", label: "pinx-PL" },
  { value: "pinx-SE", label: "pinx-SE" },
  { value: "pinx-UK", label: "pinx-UK" },
  { value: "RR-BE", label: "RR-BE" },
  { value: "RR-DE", label: "RR-DE" },
  { value: "RR-ES", label: "RR-ES" },
  { value: "RR-FR", label: "RR-FR" },
  { value: "RR-IT", label: "RR-IT" },
  { value: "RR-NL", label: "RR-NL" },
  { value: "RR-PL", label: "RR-PL" },
  { value: "RR-SE", label: "RR-SE" },
  { value: "RR-UK", label: "RR-UK" },
  { value: "ZY-BE", label: "ZY-BE" },
  { value: "ZY-DE", label: "ZY-DE" },
  { value: "ZY-ES", label: "ZY-ES" },
  { value: "ZY-FR", label: "ZY-FR" },
  { value: "ZY-IT", label: "ZY-IT" },
  { value: "ZY-NL", label: "ZY-NL" },
  { value: "ZY-PL", label: "ZY-PL" },
  { value: "ZY-SE", label: "ZY-SE" },
  { value: "ZY-UK", label: "ZY-UK" },
];

const adsTypes = [
  { value: "sp", label: "SP" },
  { value: "sb", label: "SB" },
  { value: "商品集", label: "商品集" },
  { value: "品牌旗舰店焦点", label: "品牌旗舰店焦点" },
  { value: "sbv", label: "SBV" },
  { value: "单个商品", label: "单个商品" },
  { value: "定向到品牌旗舰店", label: "定向到品牌旗舰店" },
  { value: "sd", label: "SD" },
];

const targetTypes = [
  { value: "sp,auto", label: "自动" },
  { value: "sp,keyword", label: "关键词投放" },
  { value: "sp,target", label: "商品投放" },
  { value: "sp,both", label: "关键词和商品投放并存" },
  { value: "sb,keyword", label: "SB-关键词" },
  { value: "sb,target", label: "SB-商品投放" },
  { value: "sbv,keyword", label: "SBV-关键词" },
  { value: "sbv,target", label: "SBV-商品投放" },
  { value: "sb2,keyword", label: "SB2-关键词" },
  { value: "sb2,target", label: "SB2-商品投放" },
  { value: "sb2,both", label: "SB2-关键词和商品并存" },
  { value: "sd,target", label: "SD-商品投放" },
  { value: "sd,audience", label: "SD-商品&受众" },
  { value: "sd,other", label: "SD-再营销" },
];

const portfolios = [
  { value: "-1", label: "未设置广告组合" },
  { value: "78719854694782", label: "01.14 选品" },
  { value: "270312778162221", label: "1.14 选品" },
  { value: "173732966030275", label: "1.14 选品(FR)" },
];

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
  { value: "ENABLED", label: "已启用" },
  { value: "CAMPAIGN_PAUSED", label: "已暂停" },
  { value: "CAMPAIGN_ARCHIVED", label: "已归档" },
  { value: "CAMPAIGN_OUT_OF_BUDGET", label: "超预算" },
  { value: "PENDING_REVIEW", label: "待审核" },
  { value: "ENDED", label: "已结束" },
  { value: "REJECTED", label: "已拒绝" },
];

const serviceStatuses = [
  { value: "SERVICE_OK", label: "正常" },
  { value: "LANDING_PAGE_NOT_AVAILABLE", label: "着陆页失效" },
  { value: "ADVERTISER_PAYMENT_FAILURE", label: "付款失败" },
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
  targetTypes: [] as string[],
  portfolios: [] as string[],
  asinSearchType: "sku",
  skus: [] as string[],
  budgetType: "",
  biddingType: "",
  costType: "",
  siteRestrictions: "",
  adsStrategy: "",
  tags: [] as string[],
  owners: [] as string[],
  campaignName: "",
  campaignStatus: [] as string[],
  serviceStatus: [] as string[],
});

const columnConfigVisible = ref(false);

const defaultColumns = [
  { label: "服务状态", prop: "serviceStatus", visible: true, category: "基础状态" },
  { label: "广告组合", prop: "portfolio", visible: true, category: "基础状态" },
  { label: "竞价策略", prop: "biddingStrategy", visible: true, category: "基础状态" },
  { label: "预算", prop: "budget", visible: true, category: "基础状态" },
  { label: "超预算时间", prop: "overBudgetTime", visible: true, category: "基础状态" },
  { label: "开始日期", prop: "startDate", visible: true, category: "基础状态" },
  { label: "标签", prop: "tags", visible: true, category: "基础状态" },
  { label: "IS", prop: "is", visible: true, category: "销售指标" },
  { label: "广告销售额", prop: "adsSales", visible: true, category: "销售指标" },
  { label: "广告销售额%", prop: "adsSalesPercent", visible: true, category: "销售指标" },
  { label: "直接销售额", prop: "directSales", visible: true, category: "销售指标" },
  { label: "ACoS", prop: "acos", visible: true, category: "核心数据" },
  { label: "ROAS", prop: "roas", visible: true, category: "核心数据" },
  { label: "广告订单", prop: "adsOrders", visible: true, category: "核心数据" },
  { label: "直接订单", prop: "directOrders", visible: true, category: "核心数据" },
  { label: "CVR", prop: "cvr", visible: true, category: "转化数据" },
  { label: "广告笔单价", prop: "adsOrderPrice", visible: true, category: "转化数据" },
  { label: "广告销量", prop: "adsVolume", visible: true, category: "转化数据" },
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

function search() {
  currentPage.value = 1;
  loadTableData();
}

function resetFilters() {
  filters.countries = [];
  filters.profiles = [];
  filters.range = [];
  filters.adsTypes = [];
  filters.targetTypes = [];
  filters.portfolios = [];
  filters.asinSearchType = "sku";
  filters.skus = [];
  filters.budgetType = "";
  filters.biddingType = "";
  filters.costType = "";
  filters.siteRestrictions = "";
  filters.adsStrategy = "";
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
async function loadTableData() {
  loading.value = true;
  try {
    const params: any = {
      pageNum: currentPage.value,
      pageSize: pageSize.value,
      name: filters.campaignName,
      state: filters.campaignStatus.join(","),
      service_status: filters.serviceStatus.join(","),
      sponsored_type: filters.adsTypes.join(","),
      targeting_type: filters.targetTypes.join(","),
      portfolio_name: filters.portfolios.join(","),
      bidding_type: filters.biddingType,
    };

    // 如果有组合或者其他可以在这里继续加

    const res = await getAdCampaigns(params);

    // 直接使用后端纯净的真实字段！前端列配置已对齐
    tableData.value = res.data?.list || [];
    total.value = res.data?.total || 0;
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
function viewRow(row: any) {
  ElMessage.info(`查看 ${row.title}`);
}
function editRow(row: any) {
  ElMessage.info(`编辑 ${row.title}`);
}
function openSearchTemplates() {
  ElMessage.info("打开筛选模板（占位）");
}

loadTableData();
</script>

<style scoped src="./ads.scss" lang="scss"></style>
