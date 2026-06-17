<template>
  <div class="listing-page">
    <!-- 搜索区域 -->
    <div class="listing-page__filters content-block">
      <ListingSearchForm />
    </div>

    <!-- 表格区域 -->
    <div class="listing-page__table content-block content-block--flush">
      <!-- 工具栏 -->
      <div class="listing-toolbar">
        <div class="listing-toolbar__left">
          <el-button
            :disabled="selectedRows.length === 0"
            type="success"
            size="default"
            icon="CollectionTag"
            @click="handleBatchOpen"
          >
            批量设置标签
          </el-button>
          <el-button
            :disabled="selectedRows.length === 0"
            type="warning"
            size="default"
            icon="Files"
            @click="handleBatchAssortOpen"
          >
            批量设置分类
          </el-button>
        </div>
        <div class="listing-toolbar__right">
          <el-tooltip content="列配置" placement="top">
            <button class="col-config-btn" type="button" @click="columnConfigVisible = true">
              <el-icon><Setting /></el-icon>
            </button>
          </el-tooltip>
        </div>
      </div>

      <!-- 表格本体 -->
      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="tableData"
        class="listing-table"
        height="750px"
        @sort-change="handleSortChange"
        @selection-change="handleSelectionChange"
        @select="handleSelect"
      >
        <el-table-column type="selection" width="50" fixed="left" align="center" />
        <el-table-column v-for="col in tableColumns" :key="col.prop" v-bind="col">
          <template #default="scope">
            <!-- 图片 -->
            <template v-if="col.prop === 'image'">
              <el-popover placement="right" :width="220" trigger="hover" :show-after="500">
                <template #reference>
                  <div class="cell-thumb">
                    <el-image :src="scope.row.image" fit="contain" class="cell-thumb__img" lazy>
                      <template #error>
                        <div class="cell-thumb__error">
                          <el-icon><Picture /></el-icon>
                        </div>
                      </template>
                    </el-image>
                  </div>
                </template>
                <div class="cell-thumb__preview">
                  <img
                    v-if="scope.row.image"
                    :src="scope.row.image.replace(/_SL\d+_/, '_SL200_')"
                  />
                </div>
              </el-popover>
            </template>

            <!-- MSKU -->
            <template v-else-if="col.prop === 'msku'">
              <div class="cell-text-container" @dblclick="handleCopy(scope.row.msku)">
                <el-tooltip
                  :content="scope.row.msku || '-'"
                  placement="top"
                  :show-after="500"
                  :disabled="!(scope.row.msku && scope.row.msku.length > 10)"
                >
                  <div class="text-ellipsis">{{ scope.row.msku || "-" }}</div>
                </el-tooltip>
                <el-tooltip
                  :content="scope.row.fnsku || '-'"
                  placement="top"
                  :show-after="500"
                  :disabled="!(scope.row.fnsku && scope.row.fnsku.length > 10)"
                >
                  <div class="color-#999 text-12px text-ellipsis">
                    {{ scope.row.fnsku || "-" }}
                  </div>
                </el-tooltip>
              </div>
            </template>

            <!-- 品名/SKU -->
            <template v-else-if="col.prop === 'skuName'">
              <div class="cell-text-container">
                <el-tooltip
                  :content="scope.row.skuName?.split('/')[0] || '-'"
                  placement="top"
                  :show-after="500"
                  :disabled="
                    !(
                      scope.row.skuName?.split('/')[0] &&
                      scope.row.skuName.split('/')[0].length > 10
                    )
                  "
                >
                  <div
                    class="text-ellipsis"
                    @dblclick="handleCopy(scope.row.skuName?.split('/')[0] || '')"
                  >
                    {{ scope.row.skuName?.split("/")[0] || "-" }}
                  </div>
                </el-tooltip>
                <el-tooltip
                  :content="scope.row.skuName?.split('/')[1] || '-'"
                  placement="top"
                  :show-after="500"
                  :disabled="
                    !(
                      scope.row.skuName?.split('/')[1] &&
                      scope.row.skuName.split('/')[1].length > 10
                    )
                  "
                >
                  <div
                    class="color-#999 text-12px text-ellipsis"
                    @dblclick="handleCopy(scope.row.skuName?.split('/')[1] || '')"
                  >
                    {{ scope.row.skuName?.split("/")[1] || "-" }}
                  </div>
                </el-tooltip>
              </div>
            </template>

            <!-- 标签 -->
            <template v-else-if="col.prop === 'label'">
              <div class="cell-tags">
                <div class="cell-tags__list">
                  <template v-if="getRowTags(scope.row).length > 0">
                    <el-tag
                      v-for="tag in getRowTags(scope.row)"
                      :key="tag.globalTagId || tag.tagName"
                      size="small"
                      :color="tag.color || '#409eff'"
                      effect="plain"
                      :disable-transitions="false"
                    >
                      {{ tag.tagName }}
                    </el-tag>
                  </template>
                  <span v-else class="cell-tags__empty">-</span>
                </div>
                <el-icon class="cell-tags__edit" @click="handleEditTags(scope.row)">
                  <Edit />
                </el-icon>
              </div>
            </template>

            <!-- ASIN -->
            <template v-else-if="col.prop === 'asin'">
              <span @dblclick="handleCopy(scope.row.asin)">{{ scope.row.asin }}</span>
            </template>

            <!-- 父ASIN -->
            <template v-else-if="col.prop === 'parentAsin'">
              <span @dblclick="handleCopy(scope.row.parentAsin)">{{ scope.row.parentAsin }}</span>
            </template>

            <!-- 状态 -->
            <template v-else-if="col.prop === 'status'">
              <el-tag v-if="scope.row.status === 'on'" type="success">在售</el-tag>
              <el-tag v-else-if="scope.row.status === 'off'" type="info">停售</el-tag>
              <el-tag v-else-if="scope.row.status === 'draft'" type="warning">草稿</el-tag>
              <el-tag v-else-if="scope.row.status === 'deleted'" type="danger">已删除</el-tag>
            </template>

            <!-- 标题 -->
            <template v-else-if="col.prop === 'title'">
              <el-tooltip
                :content="scope.row.title"
                placement="top"
                :show-after="500"
                :disabled="!scope.row.title"
              >
                <div class="text-ellipsis" @dblclick="handleCopy(scope.row.title)">
                  {{ scope.row.title }}
                </div>
              </el-tooltip>
            </template>

            <!-- 大类排名 -->
            <template v-else-if="col.prop === 'rank'">
              <div v-if="scope.row.rank && scope.row.rank.rank" class="cell-rank-stack">
                <span class="cell-rank-stack__value">{{ scope.row.rank.rank }}</span>
                <el-tooltip
                  :content="scope.row.rank.category || ''"
                  placement="top"
                  :show-after="500"
                  :disabled="!scope.row.rank.category"
                >
                  <span class="cell-rank-stack__category">{{ scope.row.rank.category }}</span>
                </el-tooltip>
              </div>
              <span v-else>-</span>
            </template>

            <!-- 小类排名 -->
            <template v-else-if="col.prop === 'smallRank'">
              <div
                v-if="scope.row.smallRank && scope.row.smallRank.rank !== undefined"
                class="cell-rank-stack"
              >
                <span class="cell-rank-stack__value">{{ scope.row.smallRank.rank }}</span>
                <el-tooltip
                  :content="scope.row.smallRank.category || ''"
                  placement="top"
                  :show-after="500"
                  :disabled="!scope.row.smallRank.category"
                >
                  <span class="cell-rank-stack__category">
                    {{ scope.row.smallRank.category }}
                  </span>
                </el-tooltip>
              </div>
              <span v-else>-</span>
            </template>

            <!-- 商品编码 -->
            <template v-else-if="col.prop === 'productCode'">
              <div class="cell-product-code">
                <span class="cell-product-code__id">{{ scope.row.productCode.id }}</span>
                <span v-if="scope.row.productCode.type" class="cell-product-code__type">
                  {{ scope.row.productCode.type }}
                </span>
              </div>
            </template>

            <!-- 变体属性 -->
            <template v-else-if="col.prop === 'variants'">
              <template v-if="getVariants(scope.row.variants).length > 0">
                <el-popover
                  placement="bottom"
                  :width="200"
                  trigger="hover"
                  :show-after="200"
                  popper-style="padding: 0; min-width: unset;"
                >
                  <template #reference>
                    <div class="cell-variants">
                      <span class="cell-variants__text">
                        [{{
                          getVariants(scope.row.variants)
                            .map((v: any) => v.attr_value)
                            .join(", ")
                        }}]
                      </span>
                      <el-icon class="cell-variants__icon" :size="12">
                        <ArrowDown />
                      </el-icon>
                    </div>
                  </template>
                  <el-table
                    :data="getVariants(scope.row.variants)"
                    :show-header="false"
                    border
                    size="small"
                    style="width: 100%"
                  >
                    <el-table-column prop="attr_name" width="80" align="center">
                      <template #default="{ row }">
                        <span class="cell-variants__attr-name">{{ row.attr_name }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="attr_value" align="left">
                      <template #default="{ row }">
                        <span>{{ row.attr_value }}</span>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-popover>
              </template>
              <div v-else class="cell-variants__empty">-</div>
            </template>

            <!-- 评分 -->
            <template v-else-if="col.prop === 'rating'">
              <div class="cell-rating">
                <div class="cell-rating__row">
                  <div class="cell-rating__bar">
                    <div class="cell-rating__bar-bg">
                      <el-icon v-for="i in 5" :key="'bg-' + i" :size="14">
                        <StarFilled />
                      </el-icon>
                    </div>
                    <div
                      class="cell-rating__bar-fg"
                      :style="{ width: (scope.row.rating.value / 5) * 100 + '%' }"
                    >
                      <el-icon v-for="i in 5" :key="'fg-' + i" :size="14">
                        <StarFilled />
                      </el-icon>
                    </div>
                  </div>
                  <span class="cell-rating__value">{{ scope.row.rating.value }}</span>
                </div>
                <span class="cell-rating__count">{{ scope.row.rating.count }}</span>
              </div>
            </template>

            <!-- 备注（可编辑） -->
            <template v-else-if="col.prop === 'remarks'">
              <div
                v-loading="scope.row.remarkLoading"
                class="cell-remark"
                @dblclick="handleEditRemark(scope.row)"
              >
                <el-tooltip
                  :content="scope.row[col.prop] !== '--' ? scope.row[col.prop] : '双击编辑备注'"
                  placement="top"
                  :show-after="500"
                >
                  <div class="cell-remark__text">{{ scope.row[col.prop] }}</div>
                </el-tooltip>
                <el-icon class="cell-remark__edit" @click="handleEditRemark(scope.row)">
                  <Edit />
                </el-icon>
              </div>
            </template>

            <!-- 利润（双行） -->
            <template v-else-if="col.prop === 'profit'">
              <div class="cell-profit">
                <span class="cell-profit__rate">
                  {{ scope.row.profit?.gross_margin_display || "0.00%" }}
                </span>
                <span
                  class="cell-profit__value"
                  :class="{
                    'cell-profit__value--negative': (scope.row.profit?.gross_profit || 0) < 0,
                  }"
                >
                  {{ scope.row.profit?.gross_profit_display || "" }}
                </span>
              </div>
            </template>

            <!-- 默认展示 -->
            <span v-else>{{ scope.row[col.prop] }}</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="listing-pager">
        <el-pagination
          size="small"
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          :current-page="pageNum"
          :page-size="pageSize"
          :page-sizes="[50, 100, 200]"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <BatchTagDialog
      ref="batchTagDialogRef"
      v-model:visible="batchTagDialogVisible"
      :selected-rows="selectedRows"
      @success="handleQuery"
    />

    <EditTagDialog
      v-model:visible="tagDialogVisible"
      :row="currentEditTagRow"
      @success="handleQuery"
    />

    <BatchAssortDialog
      v-model:visible="batchAssortDialogVisible"
      :selected-rows="selectedRows"
      :category-options="categoryTypeOptions"
      @success="handleQuery"
    />

    <!-- 列配置抽屉 -->
    <ColumnManager
      v-model="columnConfigVisible"
      :columns="columns"
      @save="handleConfigSave"
      @reset="handleConfigReset"
    />
  </div>
</template>

<script setup lang="ts">
import { provide, ref, computed, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { SalesProductListingAPI, type ListingItemVO } from "@/api/sales/listing";
import useClipboard from "vue-clipboard3";
import { useListingTable } from "./useListingTable";
import ListingSearchForm from "./components/ListingSearchForm.vue";
import ColumnManager from "@/components/ColumnManager/index.vue";
import BatchTagDialog from "./components/BatchTagDialog.vue";
import EditTagDialog from "./components/EditTagDialog.vue";
import BatchAssortDialog from "./components/BatchAssortDialog.vue";
import { defaultColumns } from "./constants";
import { Edit, Picture, StarFilled, ArrowDown, Setting } from "@element-plus/icons-vue";

defineOptions({ name: "SalesProductListing" });

const listingHooks = useListingTable();
provide("listingHooks", listingHooks);
const { toClipboard } = useClipboard();

const {
  loading,
  fallback,
  categoryTypeOptions,
  tableData,
  pageNum,
  pageSize,
  total,
  handleQuery,
  handleSortChange,
  handleSizeChange,
  handleCurrentChange,
} = listingHooks;

const columnConfigVisible = ref(false);

// 批量操作相关
const selectedRows = ref<ListingItemVO[]>([]);
const batchTagDialogVisible = ref(false);
const batchTagDialogRef = ref();

// 批量分类相关
const batchAssortDialogVisible = ref(false);

const tagDialogVisible = ref(false);
const currentEditTagRow = ref<any>(null);

function getVariants(val: any) {
  if (!val || val === "--") return [];
  if (Array.isArray(val)) return val;
  if (typeof val === "string") {
    try {
      const trimmed = val.trim();
      if (trimmed.startsWith("[")) {
        const jsonStr = trimmed.replace(/'/g, '"');
        const parsed = JSON.parse(jsonStr);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch {
      return [];
    }
  }
  return [];
}

interface TagItem {
  globalTagId: string;
  tagName: string;
  color: string;
}

function getRowTags(row: any): TagItem[] {
  if (!row.label || !Array.isArray(row.label)) return [];
  return row.label.filter((t: any) => t && t.tagName);
}

function handleSelectionChange(selection: ListingItemVO[]) {
  selectedRows.value = selection;
}

const isShiftDown = ref(false);
function handleKeyDown(e: KeyboardEvent) {
  if (e.key === "Shift") isShiftDown.value = true;
}
function handleKeyUp(e: KeyboardEvent) {
  if (e.key === "Shift") isShiftDown.value = false;
}

onMounted(() => {
  window.addEventListener("keydown", handleKeyDown);
  window.addEventListener("keyup", handleKeyUp);
});
onUnmounted(() => {
  window.removeEventListener("keydown", handleKeyDown);
  window.removeEventListener("keyup", handleKeyUp);
});

const tableRef = ref();
let lastSelectedIndex = -1;

function handleSelect(selection: any[], row: any) {
  const currentIndex = tableData.value.findIndex((item) => item === row);
  const isSelected = selection.some((item) => item === row);

  if (isShiftDown.value && lastSelectedIndex !== -1 && lastSelectedIndex !== currentIndex) {
    const start = Math.min(lastSelectedIndex, currentIndex);
    const end = Math.max(lastSelectedIndex, currentIndex);

    for (let i = start; i <= end; i++) {
      tableRef.value?.toggleRowSelection(tableData.value[i], isSelected);
    }
    window.getSelection()?.removeAllRanges();
  }

  lastSelectedIndex = currentIndex;
}

function handleBatchOpen() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning("请先勾选商品");
    return;
  }
  batchTagDialogRef.value?.init?.();
  batchTagDialogVisible.value = true;
}

function handleBatchAssortOpen() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning("请先勾选商品");
    return;
  }
  batchAssortDialogVisible.value = true;
}

function handleEditTags(row: ListingItemVO) {
  currentEditTagRow.value = row;
  tagDialogVisible.value = true;
}

function handleEditRemark(row: any) {
  ElMessageBox.prompt("请输入备注内容", "编辑备注", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    inputValue: row.remarks !== "--" ? row.remarks : "",
    inputType: "textarea",
    inputPlaceholder: "输入备注...",
  })
    .then(async ({ value }) => {
      row.remarkLoading = true;
      try {
        await SalesProductListingAPI.upsertRemark({
          listing_id: row.id,
          remark: value,
        });
        ElMessage.success("备注保存成功");
        row.remarks = fallback(value);
      } catch {
        ElMessage.error("备注保存失败");
      } finally {
        row.remarkLoading = false;
      }
    })
    .catch(() => {
      // 取消操作
    });
}

// 复制功能
const handleCopy = async (text: string) => {
  if (!text) return;
  try {
    await toClipboard(text);
    ElMessage.success("复制成功");
  } catch {
    ElMessage.error("复制失败");
  }
};

const STORAGE_KEY = "SALES_PRODUCT_LISTING_COLUMNS_V5";

// 初始化列配置（合并本地缓存）
const initColumns = () => {
  const cached = localStorage.getItem(STORAGE_KEY);
  if (cached) {
    try {
      const parsed = JSON.parse(cached);
      const defaultMap = new Map(defaultColumns.map((c) => [c.prop, c]));
      const cachedProps = new Set();

      const merged = parsed
        .map((c: any) => {
          const def = defaultMap.get(c.prop);
          if (def) {
            cachedProps.add(c.prop);
            return { ...c, category: def.category, label: def.label };
          }
          return null;
        })
        .filter(Boolean);

      const newCols = defaultColumns.filter((c) => !cachedProps.has(c.prop));
      return [...merged, ...newCols];
    } catch (e) {
      console.error("读取列配置失败", e);
    }
  }
  return JSON.parse(JSON.stringify(defaultColumns));
};

const columns = ref(initColumns());

// 仅获取可见列，用于表格渲染
const tableColumns = computed(() => columns.value.filter((c: any) => c.visible));

function handleConfigSave(newColumns: any[]) {
  columns.value = newColumns;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(newColumns));
  ElMessage.success("配置已保存");
}
function handleConfigReset() {
  columns.value = JSON.parse(JSON.stringify(defaultColumns));
  localStorage.removeItem(STORAGE_KEY);
  ElMessage.success("已恢复默认配置");
}
</script>

<style scoped src="./index.scss" lang="scss"></style>
<style src="./index-global.scss" lang="scss"></style>
