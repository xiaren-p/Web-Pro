<template>
  <div class="data-table-container">
    <el-table
      v-loading="loading"
      class="data-table__content"
      :data="tableData"
      border
      height="calc(100vh - 280px)"
      style="width: 100%"
    >
      <el-table-column type="selection" width="48" fixed="left" align="center" />

      <!-- 固定的基础业务列 -->
      <el-table-column label="有效" width="80" fixed="left" align="center">
        <template #default="{ row }">
          <el-switch v-model="row.state" active-value="enabled" inactive-value="paused" disabled />
        </template>
      </el-table-column>
      <el-table-column label="类型" width="100" fixed="left" align="center">
        <template #default="{ row }">
          <div>{{ row.sponsored_type }}</div>
          <div style="font-size: 12px; color: #999">{{ row.targeting_type }}</div>
        </template>
      </el-table-column>
      <el-table-column label="店铺" width="120" fixed="left" align="center">
        <template #default="{ row }">
          <div>{{ row.store_name }}</div>
          <div style="font-size: 12px; color: #999">{{ row.targeting_type }}</div>
        </template>
      </el-table-column>
      <el-table-column
        prop="name"
        label="广告活动"
        min-width="150"
        fixed="left"
        align="center"
        show-overflow-tooltip
      />

      <!-- 动态从列配置里面拉取的列 -->
      <el-table-column
        v-for="col in columns"
        :key="col.prop"
        :prop="col.prop"
        :label="col.label"
        :fixed="col.fixed"
        min-width="120"
        align="center"
        show-overflow-tooltip
      />

      <el-table-column label="操作" width="120" fixed="right" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="$emit('view-row', row)">
            查看
          </el-button>
          <el-button type="primary" link size="small" @click="$emit('edit-row', row)">
            编辑
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager-row">
      <div>
        <el-select
          v-model="localPageSize"
          placeholder="每页"
          size="small"
          style="width: 120px"
          @change="onPageSizeChange"
        >
          <el-option label="25条/页" :value="25" />
          <el-option label="50条/页" :value="50" />
          <el-option label="100条/页" :value="100" />
        </el-select>
      </div>
      <el-pagination
        background
        :current-page="currentPage"
        :page-size="localPageSize"
        :total="total"
        layout="prev, pager, next, jumper"
        @current-change="$emit('current-change', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    tableData: any[];
    pageSize: number;
    currentPage: number;
    total: number;
    columns: any[];
    loading?: boolean;
  }>(),
  {
    loading: false,
  }
);

const emit = defineEmits(["current-change", "view-row", "edit-row", "page-size-change"]);

const localPageSize = ref(props.pageSize || 25);

watch(
  () => props.pageSize,
  (v) => {
    localPageSize.value = v;
  }
);

function onPageSizeChange(v: number) {
  emit("page-size-change", v);
}
</script>

<style scoped>
.pager-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background-color: #fff;
  border-radius: 0 0 8px 8px;
  border-top: none;
}

.data-table__content {
  border-left: none;
  border-right: none;
  border-top: none;
}

/* 表头：浅灰色背景，对齐 listing 不生硬 */
:deep(.el-table__header th) {
  background-color: #f7f8fb !important;
  color: #3f4551 !important;
  font-weight: 600 !important;
  font-size: 13px;
  border-bottom: 1px solid #ebeef5;
  text-align: center;
}

:deep(.el-table__header th .cell) {
  width: 100%;
  display: block;
}

/* 表格内容：干净字体 */
:deep(.el-table .el-table__cell) {
  padding: 8px 0 !important;
  font-size: 13px;
  color: #4b5263;
}

/* 单元格 hover */
:deep(.el-table .el-table__row) {
  transition: background-color 0.2s ease;
}
:deep(.el-table .el-table__row:hover > td.el-table__cell) {
  background-color: #f5f7fc !important;
}
</style>
