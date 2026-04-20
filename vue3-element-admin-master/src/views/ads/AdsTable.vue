<template>
  <div class="mt-6">
    <el-table v-loading="loading" :data="tableData" stripe height="1000" style="width: 100%">
      <el-table-column type="selection" width="48" fixed="left" />

      <!-- 固定的四个基础业务列 -->
      <el-table-column label="有效" width="80" fixed="left">
        <template #default="{ row }">
          <el-switch v-model="row.state" active-value="enabled" inactive-value="paused" disabled />
        </template>
      </el-table-column>
      <el-table-column label="类型" width="100" fixed="left">
        <template #default="{ row }">
          <div>{{ row.sponsored_type }}</div>
          <div style="font-size: 12px; color: #999">{{ row.targeting_type }}</div>
        </template>
      </el-table-column>
      <el-table-column label="店铺" width="120" fixed="left">
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
        show-overflow-tooltip
      />

      <!-- 动态从列配置里面拉取的列 -->
      <el-table-column
        v-for="col in columns"
        :key="col.value"
        :prop="col.value"
        :label="col.label"
        :fixed="col.fixed"
        min-width="120"
        show-overflow-tooltip
      />

      <el-table-column label="分析" width="160" fixed="right">
        <template #default="{ row }">
          <el-button type="text" size="small" @click="$emit('view-row', row)">查看</el-button>
          <el-button type="text" size="small" @click="$emit('edit-row', row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="mt-4 pager-row">
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

const props = defineProps<{
  tableData: any[];
  pageSize: number;
  currentPage: number;
  total: number;
  columns: any[];
  loading?: boolean;
}>();

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
}
</style>
