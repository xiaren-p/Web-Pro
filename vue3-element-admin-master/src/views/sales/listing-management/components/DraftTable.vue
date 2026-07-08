<template>
  <div class="draft-table__wrapper">
    <el-table
      v-loading="false"
      :data="tableData"
      class="draft-table"
      @selection-change="handleSelectionChange"
    >
      <!-- 空状态 -->
      <template #empty>
        <div class="draft-table__empty">
          <p class="draft-table__empty-text">暂无数据</p>
        </div>
      </template>

      <!-- 复选框列 -->
      <el-table-column type="selection" width="48" align="center" />

      <!-- 图片 -->
      <el-table-column prop="image" label="图片" width="60" align="center">
        <template #default>
          <div class="cell-thumb">
            <div class="cell-thumb__placeholder" />
          </div>
        </template>
      </el-table-column>

      <!-- 草稿版本 -->
      <el-table-column prop="draftVersion" label="草稿版本" width="100" />

      <!-- MSKU（加粗） -->
      <el-table-column prop="msku" label="MSKU" width="120">
        <template #default>
          <span class="cell-msku">-</span>
        </template>
      </el-table-column>

      <!-- 变体属性（双行省略） -->
      <el-table-column prop="variantAttr" label="变体属性" width="150">
        <template #default>
          <div class="cell-line-clamp">-</div>
        </template>
      </el-table-column>

      <!-- 标题（双行省略） -->
      <el-table-column prop="title" label="标题" width="200">
        <template #default>
          <div class="cell-line-clamp">-</div>
        </template>
      </el-table-column>

      <!-- 店铺 -->
      <el-table-column prop="shop" label="店铺" width="120" />

      <!-- 国家（小号字体，缩写） -->
      <el-table-column prop="country" label="国家" width="80" align="center">
        <template #default>
          <span class="cell-country">-</span>
        </template>
      </el-table-column>

      <!-- 配送方式 -->
      <el-table-column prop="deliveryMethod" label="配送方式" width="100" />

      <!-- 价格（¥前缀，右对齐） -->
      <el-table-column prop="price" label="价格" width="100" align="right">
        <template #default>
          <span class="cell-price">-</span>
        </template>
      </el-table-column>

      <!-- 库存（<10 红色） -->
      <el-table-column prop="stock" label="库存" width="80" align="center">
        <template #default>
          <span>-</span>
        </template>
      </el-table-column>

      <!-- 销售类型（el-tag） -->
      <el-table-column prop="saleType" label="销售类型" width="100">
        <template #default>
          <span>-</span>
        </template>
      </el-table-column>

      <!-- 必填项完整（✅/❌ 图标） -->
      <el-table-column prop="requiredComplete" label="必填项完整" width="120" align="center">
        <template #default>
          <span>-</span>
        </template>
      </el-table-column>

      <!-- 操作人 -->
      <el-table-column prop="operator" label="操作人" width="100" />

      <!-- 操作时间 -->
      <el-table-column prop="operateTime" label="操作时间" width="160" />

      <!-- 操作（三图标 + tooltip） -->
      <el-table-column prop="actions" label="操作" width="80" align="center" fixed="right">
        <template #default>
          <div class="cell-actions">
            <el-tooltip content="编辑" placement="top">
              <el-button link type="primary" size="small" :icon="Edit" disabled />
            </el-tooltip>
            <el-tooltip content="预览" placement="top">
              <el-button link type="primary" size="small" :icon="View" disabled />
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <el-button link type="danger" size="small" :icon="Delete" disabled />
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
/**
 * 草稿箱数据表格：14 列 + 复选框，含图片占位、MSKU 加粗、多用省略、库存红色警戒、
 * 销售类型标签、必填项图标、操作按钮等自定义列渲染。当前无数据，展示空状态。
 */
import { ref } from "vue";
import { Edit, View, Delete } from "@element-plus/icons-vue";

defineOptions({ name: "DraftTable" });

interface DraftRow {
  id: number;
  image: string;
  draftVersion: string;
  msku: string;
  variantAttr: string;
  title: string;
  shop: string;
  country: string;
  deliveryMethod: string;
  price: number;
  stock: number;
  saleType: string;
  requiredComplete: boolean;
  operator: string;
  operateTime: string;
}

const tableData = ref<DraftRow[]>([]);
const selectedRows = ref<DraftRow[]>([]);

function handleSelectionChange(selection: DraftRow[]) {
  selectedRows.value = selection;
}
</script>

<style scoped lang="scss">
.draft-table__wrapper {
  flex: 1;
  min-height: 0;
  overflow: hidden;

  :deep(.el-table) {
    height: 100%;
  }

  :deep(.el-table::before),
  :deep(.el-table--border::after) {
    display: none;
  }

  :deep(.el-table__empty-block) {
    min-height: unset !important;
    height: 100% !important;
  }
}

.draft-table {
  /* 表头 */
  :deep(.el-table__header-wrapper th.el-table__cell),
  :deep(.el-table__header th) {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold) !important;
    color: var(--text-secondary) !important;
    text-align: center;
    background-color: var(--surface-subtle) !important;
    border-bottom: 1px solid var(--border-base) !important;
    box-shadow: none;
  }

  :deep(.el-table__header th .cell) {
    display: block;
    width: 100%;
  }

  /* 表体 */
  :deep(.el-table .el-table__cell) {
    padding: 12px 0 !important;
    font-size: var(--font-size-sm);
    color: var(--text-primary);
    border-right: none !important;
    border-bottom: 1px solid var(--border-subtle) !important;
  }

  :deep(.el-table .cell) {
    padding-right: 14px;
    padding-left: 14px;
    line-height: 1.5;
  }

  /* 行 hover */
  :deep(.el-table .el-table__row) {
    transition: background-color var(--transition-ui);
  }

  :deep(.el-table .el-table__row:hover > td.el-table__cell) {
    background-color: var(--surface-hover) !important;
  }

  :deep(.el-table .el-table__row:hover > td.el-table__cell:first-child) {
    box-shadow: inset 3px 0 0 var(--color-primary-600);
  }
}

/* 空状态 */
.draft-table__empty {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  align-items: center;
  justify-content: center;

  &-text {
    font-size: var(--font-size-base);
    color: var(--text-secondary);
  }
}

/* 图片占位 */
.cell-thumb {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;

  &__placeholder {
    width: 40px;
    height: 40px;
    background: var(--surface-subtle);
    border: 1px solid var(--border-base);
    border-radius: var(--radius-sm);
  }
}

/* MSKU 加粗 */
.cell-msku {
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

/* 变体属性 / 标题 双行省略 */
.cell-line-clamp {
  display: -webkit-box;
  overflow: hidden;
  text-overflow: ellipsis;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-height: 1.4;
}

/* 国家小号字体 */
.cell-country {
  font-size: var(--font-size-xs);
}

/* 价格右对齐 ¥ */
.cell-price {
  font-variant-numeric: tabular-nums;
}

/* 操作列 */
.cell-actions {
  display: flex;
  gap: 2px;
  align-items: center;
  justify-content: center;

  :deep(.el-button) {
    min-height: unset;
    padding: 4px;
  }
}
</style>
