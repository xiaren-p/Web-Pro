<template>
  <div class="ads-panel ads-detail-panel">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-date-picker
        v-model="filters.range"
        size="small"
        class="filter-item date-picker"
        type="daterange"
        start-placeholder="开始"
        end-placeholder="结束"
        range-separator=" - "
        value-format="YYYY-MM-DD"
        style="width: 218px"
        unlink-panels
      />
      <el-select
        v-model="filters.state"
        size="small"
        class="filter-item w-110"
        placeholder="全部状态"
        clearable
      >
        <el-option label="已启用" value="enabled" />
        <el-option label="已暂停" value="paused" />
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-select
        v-model="filters.productTag"
        size="small"
        class="filter-item w-120"
        placeholder="商品标签"
        clearable
      >
        <el-option label="全部标签" value="" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        size="small"
        class="filter-item keyword-input"
        placeholder="请输入ASIN或MSKU"
        clearable
      />

      <!-- 筛选模板 / 查询 / 重置 -->
      <el-button size="small" :icon="Filter" class="btn-template">筛选模板</el-button>
      <el-button type="primary" size="small" @click="onSearch">查询</el-button>
      <el-button size="small" @click="onReset">重置</el-button>

      <!-- 占位：把列配置按鈔推到最右 -->
      <span style="flex: 1" />

      <!-- 列配置图标按鈔（右侧固定） -->
      <el-tooltip content="列配置" placement="top">
        <el-button
          text
          style="height: 32px; min-height: 32px; padding: 4px 9px; font-size: 16px; color: #606266"
          @click="columnConfigVisible = true"
        >
          <el-icon><Operation /></el-icon>
        </el-button>
      </el-tooltip>
    </div>

    <!-- 表格 -->
    <div class="data-table-container">
      <el-table
        v-loading="loading"
        class="data-table__content"
        :data="displayData"
        border
        :row-class-name="rowClassName"
        height="calc(100vh - 380px)"
        style="width: 100%"
        @selection-change="onSelectionChange"
        @header-dragend="onHeaderDragEnd"
      >
        <!-- 固定左侧：勾选列 -->
        <el-table-column
          type="selection"
          width="42"
          fixed="left"
          align="center"
          :resizable="false"
          :selectable="(row: any) => !row._isSummary"
        />

        <!-- 固定左：有效 -->
        <el-table-column label="有效" width="68" fixed="left" align="center" :resizable="false">
          <template #default="{ row }">
            <el-switch
              v-if="!row._isSummary"
              v-model="row.state"
              active-value="enabled"
              inactive-value="paused"
              disabled
            />
          </template>
        </el-table-column>

        <!-- 固定左：图片 -->
        <el-table-column label="图片" width="68" fixed="left" align="center" :resizable="false">
          <template #default="{ row }">
            <el-tooltip
              v-if="row.image_url"
              placement="right"
              effect="light"
              :show-after="150"
              :hide-after="0"
              popper-class="product-thumb-popper"
            >
              <template #content>
                <img
                  :src="toPreviewUrl(row.image_url)"
                  style="width: 160px; height: 160px; object-fit: cover; border-radius: 4px"
                  alt="商品图片"
                />
              </template>
              <img :src="row.image_url" class="product-thumb" alt="商品图片" />
            </el-tooltip>
            <span v-else-if="!row._isSummary" class="thumb-placeholder" />
          </template>
        </el-table-column>

        <!-- 固定左：ASIN（标题悬浮 tooltip，ASIN/价格/星级一行展示） -->
        <el-table-column label="ASIN" width="300" :min-width="300" fixed="left" align="left">
          <template #default="{ row }">
            <span v-if="row._isSummary" class="summary-label">汇总</span>
            <el-tooltip
              v-else
              placement="top"
              :show-after="400"
              :disabled="!productMeta.titleVisible || !isLikelyOverflow(row.title, 258, 1)"
            >
              <template #content>
                <div style="display: flex; align-items: flex-start; gap: 6px; max-width: 260px">
                  <span style="word-break: break-word">{{ row.title }}</span>
                  <el-icon
                    style="
                      flex-shrink: 0;
                      margin-top: 2px;
                      cursor: pointer;
                      color: rgba(255, 255, 255, 0.8);
                    "
                    @click.stop="copyText(row.title)"
                  >
                    <CopyDocument />
                  </el-icon>
                </div>
              </template>
              <div class="asin-cell">
                <!-- 第一行：标题（单行截断，hover 时出现复制图标） -->
                <div v-if="productMeta.titleVisible" class="asin-title-row">
                  <span class="asin-title">{{ row.title || "-" }}</span>
                  <el-icon class="copy-icon" @click.stop="copyText(row.title)">
                    <CopyDocument />
                  </el-icon>
                </div>
                <!-- 第二行：ASIN / 价格 / 星级 -->
                <div class="asin-row">
                  <span class="asin-text">{{ row.asin || "-" }}</span>
                  <el-icon class="copy-icon" @click.stop="copyText(row.asin)">
                    <CopyDocument />
                  </el-icon>
                  <span v-if="productMeta.priceVisible && row.price != null" class="asin-price">
                    {{ currencyIcon }}{{ row.price }}
                  </span>
                  <span v-if="productMeta.ratingVisible && row.rating != null" class="asin-rating">
                    {{ row.rating }}星
                    <template v-if="productMeta.reviewsVisible">({{ row.reviews ?? 0 }})</template>
                  </span>
                </div>
              </div>
            </el-tooltip>
          </template>
        </el-table-column>

        <!-- 固定左：MSKU（可排序，两行截断，悬浮复制） -->
        <el-table-column label="MSKU" width="90" :min-width="90" fixed="left" align="left" sortable>
          <template #default="{ row }">
            <div v-if="row._isSummary" />
            <el-tooltip
              v-else
              :content="row.msku ?? ''"
              placement="top"
              :show-after="400"
              :disabled="!isLikelyOverflow(row.msku, 72)"
            >
              <div class="msku-cell">
                <span class="msku-text">{{ row.msku || "-" }}</span>
                <el-icon class="copy-icon" @click.stop="copyText(row.msku)">
                  <CopyDocument />
                </el-icon>
              </div>
            </el-tooltip>
          </template>
        </el-table-column>

        <!-- 动态列（由 ColumnManager 控制） -->
        <el-table-column
          v-for="col in visibleColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :min-width="(col as any).minWidth || 120"
          align="center"
          :sortable="(col as any).sortable ?? false"
          :show-overflow-tooltip="
            !['service_status', 'campaign_name', 'adgroup_name'].includes(col.prop)
          "
        >
          <template #default="{ row }">
            <template v-if="col.prop === 'service_status'">
              <span
                v-if="!row._isSummary"
                class="status-badge"
                :class="`status-${row.service_status_type || 'default'}`"
              >
                {{ row.service_status_label || row.service_status || "-" }}
              </span>
            </template>
            <template v-else-if="col.prop === 'campaign_name' || col.prop === 'adgroup_name'">
              <div v-if="row._isSummary" />
              <el-tooltip
                v-else
                :content="String(row[col.prop] ?? '')"
                placement="top"
                :show-after="400"
                :disabled="!isLikelyOverflow(String(row[col.prop] ?? ''), 176)"
              >
                <div class="msku-cell">
                  <span
                    class="campaign-state-icon"
                    :class="`state-${col.prop === 'campaign_name' ? row.campaign_state || 'unknown' : row.adgroup_state || 'unknown'}`"
                  >
                    <template
                      v-if="
                        (col.prop === 'campaign_name' ? row.campaign_state : row.adgroup_state) ===
                        'enabled'
                      "
                    >
                      <span class="dot-circle" />
                    </template>
                    <template
                      v-else-if="
                        (col.prop === 'campaign_name' ? row.campaign_state : row.adgroup_state) ===
                        'paused'
                      "
                    >
                      <el-icon><VideoPause /></el-icon>
                    </template>
                    <template
                      v-else-if="
                        (col.prop === 'campaign_name' ? row.campaign_state : row.adgroup_state) ===
                        'archived'
                      "
                    >
                      <el-icon><CircleClose /></el-icon>
                    </template>
                  </span>
                  <span class="msku-text msku-text--dark">{{ row[col.prop] ?? "-" }}</span>
                  <el-icon class="copy-icon" @click.stop="copyText(String(row[col.prop] ?? ''))">
                    <CopyDocument />
                  </el-icon>
                </div>
              </el-tooltip>
            </template>
            <template v-else>
              <span>{{ row[col.prop] ?? "-" }}</span>
            </template>
          </template>
        </el-table-column>

        <!-- 固定右：分析 -->
        <el-table-column label="分析" width="80" fixed="right" align="center" :resizable="false">
          <template #default="{ row }">
            <el-button v-if="row.ad_id" type="primary" link size="small">分析</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页栏 -->
      <div class="pager-row">
        <span class="total-count">共 {{ total.toLocaleString() }} 条</span>
        <el-select
          v-model="pageSize"
          placeholder="每页"
          style="width: 100px"
          @change="onPageSizeChange"
        >
          <el-option label="25条/页" :value="25" />
          <el-option label="50条/页" :value="50" />
          <el-option label="100条/页" :value="100" />
          <el-option label="250条/页" :value="250" />
        </el-select>
        <el-pagination
          background
          :current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next, jumper"
          @current-change="onPageChange"
        />
      </div>
    </div>

    <!-- 通用列配置抽屉 -->
    <ColumnManager
      v-model="columnConfigVisible"
      :columns="activeColumns"
      @save="onColumnConfigSave"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 广告投放（Product Ad）列表面板：展示当前广告活动（可选过滤到某一广告组）
 * 下的所有广告投放及聚合指标。
 * 所属板块：ads 详情页。
 */
import type { AdsResponse } from "@/api/ads";

import { computed, onMounted, ref, watch } from "vue";
import { useLocalStorage } from "@vueuse/core";
import { CopyDocument, Filter, Operation, VideoPause, CircleClose } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

import { getAds } from "@/api/ads";
import ColumnManager from "@/components/ColumnManager/index.vue";

defineOptions({ name: "AdsPanel" });

/**
 * 父页面透传的广告活动 ID、店铺 Profile ID 及可选的广告组 ID。
 *
 * @prop {string} [campaignId] - 广告活动 ID（必填，缺失时不发请求）
 * @prop {string} [profileId] - 店铺 Profile ID（必填，缺失时不发请求）
 * @prop {string} [adGroupId] - 广告组 ID（可选，不传则展示整个广告活动的投放）
 * @prop {string[]} [initialDateRange] - 格式 ['YYYY-MM-DD', 'YYYY-MM-DD'] 或空数组
 */
const props = defineProps<{
  campaignId?: string;
  profileId?: string;
  adGroupId?: string;
  initialDateRange?: string[];
}>();

/** 列可见性持久化（只存 prop → visible 映射，列定义结构始终以代码为准） */
const _savedColVis = useLocalStorage<Record<string, boolean>>("ads_panel_col_vis", {});

/** 筛选条件持久化（不含日期范围，日期由父组件 props 注入） */
const _savedFilters = useLocalStorage("ads_panel_filters", {
  state: "",
  keyword: "",
  productTag: "",
});

/** 筛选条件，range 以父页面传入日期初始化 */
const filters = ref({
  range: (props.initialDateRange?.length === 2 ? [...props.initialDateRange] : []) as string[],
  state: _savedFilters.value.state,
  productTag: _savedFilters.value.productTag,
  keyword: _savedFilters.value.keyword,
});

/** 列配置抽屉显示状态（持久化，刷新后保持上次开关状态） */
const columnConfigVisible = useLocalStorage<boolean>("ads_panel_drawer", false);

/** 数据加载状态 */
const loading = ref(false);

/** 分页状态（pageSize 持久化） */
const total = ref(0);
const currentPage = ref(1);
const pageSize = useLocalStorage<number>("ads_panel_page_size", 25);

/** 表格数据（后端返回的广告投放列表） */
const tableData = ref<any[]>([]);

/** 汇总行数据（后端返回的 summary，挂载 _isSummary 标志后置顶） */
const summaryRow = ref<Record<string, unknown> | null>(null);

/** 货币符号（从接口响应中获取） */
const currencyIcon = ref<string>("$");

/** 当前勾选的行数据 */
const selectedRows = ref<any[]>([]);

/**
 * 列定义（含 category，供 ColumnManager 分组展示）。
 * visible 由 ColumnManager @save 回调更新。
 */
const activeColumns = ref([
  // 设置
  { prop: "service_status", label: "服务状态", visible: true, category: "设置" },
  { prop: "portfolio_name", label: "广告组合", visible: true, category: "设置" },
  {
    prop: "campaign_name",
    label: "广告活动",
    visible: true,
    category: "设置",
    minWidth: 200,
    sortable: true,
  },
  {
    prop: "adgroup_name",
    label: "广告组",
    visible: true,
    category: "设置",
    minWidth: 200,
    sortable: true,
  },
  { prop: "targeting", label: "投放", visible: false, category: "设置" },
  { prop: "created_at", label: "创建时间", visible: false, category: "设置" },
  // LISTING
  // Listing（合并展示在商品列单元格内，由列配置独立控制可见性）
  { prop: "stock", label: "可售库存", visible: true, category: "LISTING" },
  { prop: "title", label: "标题", visible: true, category: "LISTING" },
  { prop: "price", label: "价格", visible: true, category: "LISTING" },
  { prop: "rating", label: "星级", visible: true, category: "LISTING" },
  { prop: "reviews", label: "评分数", visible: true, category: "LISTING" },
  // 转化
  { prop: "adsSales", label: "广告销售额", visible: true, category: "转化" },
  { prop: "adsSalesPercent", label: "广告销售额%", visible: true, category: "转化" },
  { prop: "directSales", label: "直接销售额", visible: false, category: "转化" },
  { prop: "acos", label: "ACoS", visible: true, category: "转化" },
  { prop: "roas", label: "ROAS", visible: true, category: "转化" },
  { prop: "adsOrders", label: "广告订单", visible: true, category: "转化" },
  { prop: "directOrders", label: "直接订单", visible: false, category: "转化" },
  { prop: "cvr", label: "CVR", visible: false, category: "转化" },
  { prop: "adsOrderPrice", label: "广告笔单价", visible: false, category: "转化" },
  { prop: "adsVolume", label: "广告销量", visible: false, category: "转化" },
  // 业绩
  { prop: "impressions", label: "曝光量", visible: true, category: "业绩" },
  { prop: "impressionsPercent", label: "曝光%", visible: false, category: "业绩" },
  { prop: "clicks", label: "点击", visible: true, category: "业绩" },
  { prop: "clicksPercent", label: "点击%", visible: false, category: "业绩" },
  { prop: "ctr", label: "CTR", visible: true, category: "业绩" },
  { prop: "cpc", label: "CPC", visible: true, category: "业绩" },
  { prop: "spends", label: "花费", visible: true, category: "业绩" },
  { prop: "spendsPercent", label: "花费%", visible: false, category: "业绩" },
  { prop: "cpa", label: "CPA", visible: false, category: "业绩" },
]);

// 用存储的可见性覆盖默认定义（仅覆盖有记录的列，新列保留代码默认值）
activeColumns.value.forEach((col) => {
  if (_savedColVis.value[col.prop] !== undefined) {
    col.visible = _savedColVis.value[col.prop];
  }
});

/** 合并显示在商品列单元格内的字段 prop 集合，不单独渲染为独立表格列 */
const MERGED_PRODUCT_PROPS = new Set(["title", "price", "rating", "reviews"]);

/**
 * 从所有列中过滤出 visible=true 且非商品合并字段的列，用于动态渲染表格列。
 *
 * @returns {当前需要展示的列定义数组}
 */
const visibleColumns = computed(() =>
  activeColumns.value.filter((c) => c.visible && !MERGED_PRODUCT_PROPS.has(c.prop))
);

/**
 * 商品列子字段可见性映射，合并展示在商品单元格内，由 ColumnManager 独立控制。
 */
const productMeta = computed(() => ({
  titleVisible: activeColumns.value.find((c) => c.prop === "title")?.visible ?? true,
  priceVisible: activeColumns.value.find((c) => c.prop === "price")?.visible ?? true,
  ratingVisible: activeColumns.value.find((c) => c.prop === "rating")?.visible ?? true,
  reviewsVisible: activeColumns.value.find((c) => c.prop === "reviews")?.visible ?? true,
}));

/**
 * 表格展示数据 = 汇总行（置顶）+ 分页数据列表。
 *
 * @returns {any[]} 拼接后的表格数据数组
 */
const displayData = computed<any[]>(() => {
  if (!summaryRow.value) return tableData.value;
  return [{ ...summaryRow.value, _isSummary: true }, ...tableData.value];
});

/**
 * 表格行自定义类名，为汇总行附加样式类。
 *
 * @param {{ row: any }} 下构 - el-table 传入的行上下文
 * @returns {string} CSS 类名
 */
function rowClassName({ row }: { row: any }): string {
  return row._isSummary ? "is-summary-row" : "";
}

/**
 * ColumnManager 保存回调，用新列配置替换 activeColumns。
 *
 * @param {typeof activeColumns.value} columns - 用户配置后的完整列数组
 */
function onColumnConfigSave(columns: typeof activeColumns.value): void {
  activeColumns.value = columns;
  _savedColVis.value = Object.fromEntries(columns.map((c) => [c.prop, c.visible]));
  ElMessage.success("列配置已保存");
}

// 筛选条件变化时自动持久化（不含日期范围）
watch(
  [() => filters.value.state, () => filters.value.keyword, () => filters.value.productTag],
  () => {
    _savedFilters.value = {
      state: filters.value.state,
      keyword: filters.value.keyword,
      productTag: filters.value.productTag,
    };
  }
);

/**
 * 触发搜索，重置到第一页后加载数据。
 */
function onSearch(): void {
  currentPage.value = 1;
  fetchData();
}

/**
 * 重置所有筛选条件并重新加载。
 */
function onReset(): void {
  filters.value.range = [];
  filters.value.state = "";
  filters.value.productTag = "";
  filters.value.keyword = "";
  _savedFilters.value = { state: "", keyword: "", productTag: "" };
  currentPage.value = 1;
  fetchData();
}

/**
 * 页码变更时触发。
 *
 * @param {number} page - 新页码
 */
function onPageChange(page: number): void {
  currentPage.value = page;
  fetchData();
}

/**
 * 每页条数变更时触发。
 *
 * @param {number} size - 新的每页条数
 */
function onPageSizeChange(size: number): void {
  pageSize.value = size;
  currentPage.value = 1;
  fetchData();
}

/**
 * 将亚马逊商品图片 URL 的尺寸标识替换为 400px，用于悬浮预览大图。
 * 支持常见格式：_SL36_、_SS600_、_SX300_ 等任意 [大写字母]+[数字] 组合。
 *
 * @param {string} url - 原始图片 URL
 * @returns {string} 替换尺寸后的高清图 URL
 */
function toPreviewUrl(url: string): string {
  return url.replace(/(_[A-Z]+)\d+_/, '$1400_');
}

/**
 * 加载广告投放列表数据，调用后端 /ads/ads 接口。
 * campaign_id / profile_id 由父页面通过 props 传入。
 */
function fetchData(): void {
  if (!props.campaignId || !props.profileId) return;

  loading.value = true;
  getAds({
    campaign_id: props.campaignId,
    profile_id: props.profileId,
    ad_group_id: props.adGroupId || undefined,
    date_start: filters.value.range?.[0] || undefined,
    date_end: filters.value.range?.[1] || undefined,
    state: filters.value.state || undefined,
    keyword: filters.value.keyword || undefined,
    pageNum: currentPage.value,
    pageSize: pageSize.value,
  })
    .then((res: AdsResponse) => {
      tableData.value = res.list ?? [];
      total.value = res.total ?? 0;
      summaryRow.value = (res.summary as Record<string, unknown>) ?? null;
      currencyIcon.value = res.currency_icon ?? "$";
    })
    .catch(() => {
      ElMessage.error("广告投放数据加载失败");
    })
    .finally(() => {
      loading.value = false;
    });
}

/**
 * 勾选变更回调，同步已选行列表。
 *
 * @param {any[]} rows - 当前所有已勾选的行数据
 */
function onSelectionChange(rows: any[]): void {
  selectedRows.value = rows;
}

/**
 * 列宽拖拽结束回调，强制列宽不低于各列的最小宽度。
 *
 * @param {number} newWidth - 拖拽后的新宽度
 * @param {number} _oldWidth - 拖拽前的旧宽度
 * @param {any} column - Element Plus 内部列对象（含 minWidth 属性）
 */
function onHeaderDragEnd(newWidth: number, _oldWidth: number, column: any): void {
  const minW = column.minWidth ? Number(column.minWidth) : 80;
  if (newWidth < minW) {
    column.width = minW;
    column.realWidth = minW;
  }
}

/**
 * 复制文本到剪贴板，成功后提示用户。
 *
 * @param {string | undefined} text - 要复制的文本内容
 */
/**
 * 粗估文本是否会溢出指定显示宽度，用于按需启用 tooltip。
 * 以 9px/字符为均值（中文 ≈12px，英文 ≈7px），超出 maxLines 行则认为溢出。
 *
 * @param {string | null | undefined} text - 显示文本
 * @param {number} displayWidth - 可用文本宽度（px，已扣除 padding / 图标占用）
 * @param {number} maxLines - 最大行数，默认 2
 * @returns {boolean} 可能溢出返回 true
 */
function isLikelyOverflow(
  text: string | null | undefined,
  displayWidth: number,
  maxLines = 2
): boolean {
  if (!text) return false;
  const charsPerLine = Math.max(1, Math.floor(displayWidth / 9));
  return text.length > charsPerLine * maxLines;
}

async function copyText(text: string | undefined): Promise<void> {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制");
  } catch {
    ElMessage.error("复制失败");
  }
}

onMounted(() => {
  fetchData();
});
</script>

<style scoped lang="scss">
/* 图片放大 tooltip：白底、无内边距，让大图紧贴气泡边缘 */
:global(.product-thumb-popper.el-popper.is-light) {
  padding: 4px !important;
  background: #fff !important;
  border: 1px solid #e4e7ed !important;
}

/* 通用筛选栏、表格、徽标、分页样式 → src/styles/ads-panel.scss → .ads-detail-panel */

/* keyword-input 宽度（广告投放面板专属：200px） */
.keyword-input {
  flex: 0 0 200px;
  width: 200px;
}

/* 单元格行高：广告投放面板 5px 上下留白（含图片缩略图） */
:deep(.el-table .el-table__cell) {
  padding: 5px 0 !important;
}

/* 商品图片缩略图 */
.product-thumb {
  display: block;
  width: 44px;
  height: 44px;
  margin: 0 auto;
  object-fit: cover;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}

.thumb-placeholder {
  display: block;
  width: 44px;
  height: 44px;
  margin: 0 auto;
  background: #f4f4f5;
  border-radius: 4px;
}

/* ASIN 单元格：第一行标题，第二行ASIN/价格/星级，标题悬浮 tooltip 显示完整内容 */
.asin-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 2px 0;
}

.asin-title-row {
  display: flex;
  align-items: center;
  gap: 4px;
  overflow: hidden;
}

.asin-title {
  flex: 1;
  overflow: hidden;
  font-size: 12px;
  color: #303133;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.asin-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  white-space: nowrap;
}

.asin-text {
  color: #409eff;
  white-space: nowrap;
}

.asin-price {
  color: #606266;
  white-space: nowrap;
}

.asin-rating {
  color: #f5a623;
  white-space: nowrap;
}

/* 复制图标 hover 触发（asin-cell 专属，通用规则见 ads-panel.scss） */
.asin-cell:hover .copy-icon {
  display: inline-flex;
}
</style>
