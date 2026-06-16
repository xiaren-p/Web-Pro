<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <ListingSearchForm />

    <!-- 占位表格区域 -->
    <el-card shadow="hover" class="data-table">
      <div
        class="data-table__toolbar"
        style="
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 2px;
        "
      >
        <div class="data-table__toolbar--left">
          <el-button
            :disabled="selectedRows.length === 0"
            type="success"
            class="mr-2"
            size="default"
            icon="CollectionTag"
            @click="handleBatchOpen"
          >
            批量设置标签
          </el-button>
          <el-button
            :disabled="selectedRows.length === 0"
            type="warning"
            class="mr-2"
            size="default"
            icon="Files"
            @click="handleBatchAssortOpen"
          >
            批量设置分类
          </el-button>
        </div>
        <div class="data-table__toolbar--right">
          <el-tooltip content="列配置" placement="top">
            <el-button
              text
              icon="Setting"
              style="height: 22px; min-height: 22px; padding: 2px; font-size: 16px"
              @click="columnConfigVisible = true"
            />
          </el-tooltip>
        </div>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="tableData"
        class="data-table__content"
        border
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
                  <div class="thumb-container">
                    <el-image :src="scope.row.image" fit="contain" class="thumb-img" lazy>
                      <template #error>
                        <div class="image-slot">
                          <el-icon><Picture /></el-icon>
                        </div>
                      </template>
                    </el-image>
                  </div>
                </template>
                <div style="text-align: center">
                  <img
                    v-if="scope.row.image"
                    :src="scope.row.image.replace(/_SL\d+_/, '_SL200_')"
                    style="max-width: 200px; max-height: 200px"
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
              <div
                style="
                  display: flex;
                  align-items: center;
                  justify-content: space-between;
                  overflow: hidden;
                "
              >
                <div style="display: flex; flex: 1; flex-wrap: wrap; gap: 4px; margin-right: 4px">
                  <template v-if="getRowTags(scope.row).length > 0">
                    <el-tag
                      v-for="(tag, index) in getRowTags(scope.row)"
                      :key="index"
                      size="small"
                      type="warning"
                      style="border: none"
                    >
                      {{ tag }}
                    </el-tag>
                  </template>
                  <span v-else class="color-#E6A23C text-12px">-</span>
                </div>
                <el-icon
                  style="flex-shrink: 0; color: #409eff; cursor: pointer"
                  @click="handleEditTags(scope.row)"
                >
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

            <!-- 标题 (特殊处理 showOverflowTooltip 参数) -->
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

            <!-- 大类排名 (优化：双列显示) -->
            <template v-else-if="col.prop === 'rank'">
              <div
                v-if="scope.row.rank && scope.row.rank.rank"
                style="
                  display: flex;
                  flex-direction: column;
                  align-items: flex-start;
                  line-height: 1.3;
                "
              >
                <span style="font-weight: bold">
                  {{ scope.row.rank.rank }}
                </span>
                <el-tooltip
                  :content="scope.row.rank.category || ''"
                  placement="top"
                  :show-after="500"
                  :disabled="!scope.row.rank.category"
                >
                  <span class="text-ellipsis" style="width: 100%">
                    {{ scope.row.rank.category }}
                  </span>
                </el-tooltip>
              </div>
              <span v-else>-</span>
            </template>

            <!-- 小类排名 (特殊双列显示 + Tooltip) -->
            <template v-else-if="col.prop === 'smallRank'">
              <div
                v-if="scope.row.smallRank && scope.row.smallRank.rank !== undefined"
                style="
                  display: flex;
                  flex-direction: column;
                  align-items: flex-start;
                  line-height: 1.3;
                "
              >
                <span style="font-weight: bold">
                  {{ scope.row.smallRank.rank }}
                </span>
                <el-tooltip
                  :content="scope.row.smallRank.category || ''"
                  placement="top"
                  :show-after="500"
                  :disabled="!scope.row.smallRank.category"
                >
                  <span class="text-ellipsis" style="width: 100%">
                    {{ scope.row.smallRank.category }}
                  </span>
                </el-tooltip>
              </div>
              <span v-else>-</span>
            </template>

            <!-- 商品编码 (双行显示) -->
            <template v-else-if="col.prop === 'productCode'">
              <div
                style="display: flex; flex-direction: column; line-height: 1.3; text-align: center"
              >
                <span>{{ scope.row.productCode.id }}</span>
                <span v-if="scope.row.productCode.type" style="font-size: 11px; color: #909399">
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
                    <div
                      style="
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: var(--el-color-primary);
                        cursor: pointer;
                      "
                    >
                      <span class="text-ellipsis" style="max-width: 120px; font-size: 13px">
                        [{{
                          getVariants(scope.row.variants)
                            .map((v: any) => v.attr_value)
                            .join(", ")
                        }}]
                      </span>
                      <el-icon
                        style="margin-left: 2px"
                        size="12"
                        color="var(--el-text-color-secondary)"
                      >
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
                        <span style="color: var(--el-text-color-secondary)">
                          {{ row.attr_name }}
                        </span>
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
              <div v-else style="text-align: center">-</div>
            </template>

            <!-- 评分 (复刻样式：星级+分数一行，总数下一行，靠右) -->
            <template v-else-if="col.prop === 'rating'">
              <div
                style="
                  display: flex;
                  flex-direction: column;
                  align-items: flex-end;
                  line-height: 1.2;
                "
              >
                <!-- 第一行：星星 + 评分值 -->
                <div class="flex-y-center" style="justify-content: flex-end">
                  <div style="position: relative; width: 70px; height: 14px; margin-right: 4px">
                    <div style="display: flex; width: 100%; height: 100%">
                      <el-icon v-for="i in 5" :key="'bg-' + i" :size="14" color="#EFF2F7">
                        <StarFilled />
                      </el-icon>
                    </div>
                    <div
                      :style="{
                        width: (scope.row.rating.value / 5) * 100 + '%',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        overflow: 'hidden',
                        whiteSpace: 'nowrap',
                        display: 'flex',
                      }"
                    >
                      <el-icon v-for="i in 5" :key="'fg-' + i" :size="14" color="#F7BA2A">
                        <StarFilled />
                      </el-icon>
                    </div>
                  </div>
                  <span style="font-size: 12px; color: #f7ba2a">{{ scope.row.rating.value }}</span>
                </div>
                <!-- 第二行：总数 -->
                <span style="margin-top: 2px; font-size: 12px; color: #606266">
                  {{ scope.row.rating.count }}
                </span>
              </div>
            </template>

            <!-- 备注 (可编辑) -->
            <template v-else-if="col.prop === 'remarks'">
              <div
                v-loading="scope.row.remarkLoading"
                style="
                  display: flex;
                  align-items: center;
                  justify-content: space-between;
                  padding: 0 4px;
                "
                @dblclick="handleEditRemark(scope.row)"
              >
                <el-tooltip
                  :content="scope.row[col.prop] !== '--' ? scope.row[col.prop] : '双击编辑备注'"
                  placement="top"
                  :show-after="500"
                >
                  <div
                    class="text-ellipsis"
                    style="flex: 1; color: var(--el-text-color-primary); cursor: pointer"
                  >
                    {{ scope.row[col.prop] }}
                  </div>
                </el-tooltip>
                <el-icon
                  style="margin-left: 4px; color: var(--el-color-primary); cursor: pointer"
                  @click="handleEditRemark(scope.row)"
                >
                  <Edit />
                </el-icon>
              </div>
            </template>

            <!-- 利润 (两行显示 毛利率百分比 / 毛利润值) -->
            <template v-else-if="col.prop === 'profit'">
              <div
                style="display: flex; flex-direction: column; line-height: 1.3; text-align: right"
              >
                <span style="font-size: 13px; font-weight: 500">
                  {{ scope.row.profit?.gross_margin_display || "0.00%" }}
                </span>
                <span
                  :style="{
                    color:
                      (scope.row.profit?.gross_profit || 0) < 0
                        ? 'var(--el-color-danger)'
                        : '#909399',
                    fontSize: '12px',
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

      <div class="pagination-container">
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
    </el-card>

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

    <!-- 列配置组件 -->
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
import { Edit, Picture, StarFilled, ArrowDown } from "@element-plus/icons-vue";

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
      // Handle Python lists parsed as string like "[{'a': 1}]" using regex replace before parse if needed,
      // but assuming it's standard JSON array structure here.
      // Wait, python single quotes might be inside:
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

function getRowTags(row: any) {
  if (!row.label) return [];
  // 如果后端直接返回了数组
  if (Array.isArray(row.label)) {
    return row.label;
  }
  // 如果是字符串
  if (typeof row.label === "string") {
    const trimmed = row.label.trim();
    // 可能是标准 JSON 字符串如 '["a","b"]' 或者是 python 单引号字符串 "['a','b']"
    if (trimmed.startsWith("[")) {
      try {
        // 先尝试正常 JSON 解析
        const parsed = JSON.parse(trimmed);
        if (Array.isArray(parsed)) return parsed;
      } catch {
        // 解析失败（比如出现单引号），手动清理
        const content = trimmed.slice(1, -1);
        if (!content.trim()) return [];
        return content
          .split(",")
          .map((s: string) => s.trim().replace(/^['"]|['"]$/g, ""))
          .filter((x: string) => x);
      }
    }
    // 兼容原有的逗号分隔字符串
    return trimmed.split(",").filter((x: string) => x);
  }
  return [];
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

    // Select or deselect everything between based on the target row's state
    for (let i = start; i <= end; i++) {
      tableRef.value?.toggleRowSelection(tableData.value[i], isSelected);
    }
    // Prevent default selection text highlighting
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
          listing_id: row.listing_id,
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

// 默认列配置

const STORAGE_KEY = "SALES_PRODUCT_LISTING_COLUMNS_V5";

// 初始化列配置（合并本地缓存）
const initColumns = () => {
  const cached = localStorage.getItem(STORAGE_KEY);
  if (cached) {
    try {
      const parsed = JSON.parse(cached);
      // 合并策略：保留缓存的顺序和状态，同步最新的元数据(category/label)，并剔除已废弃的列
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
