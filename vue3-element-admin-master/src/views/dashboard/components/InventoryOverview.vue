<template>
  <el-card shadow="never" class="h-full">
    <template #header>
      <div class="flex justify-between items-center">
        <span class="font-bold text-base flex items-center">
          库存概览
          <el-icon class="ml-1"><ArrowDown /></el-icon>
        </span>
        <el-radio-group v-model="inventoryTab" size="small">
          <el-radio-button value="quantity">数量</el-radio-button>
          <el-radio-button value="value">货值</el-radio-button>
        </el-radio-group>
      </div>
    </template>
    <div class="flex flex-col sm:flex-row h-full">
      <!-- Left: Chart & Key Metrics -->
      <div class="w-full sm:w-5/12 relative">
        <ECharts :options="inventoryChartOptions" height="200px" />
        <div class="mt-2 px-2">
          <div class="flex justify-between items-center mb-2">
            <div class="flex items-center">
              <div class="w-2 h-2 rounded-full bg-blue-500 mr-2"></div>
              <span class="text-sm text-gray-500">在库</span>
            </div>
            <span class="font-bold">----</span>
          </div>
          <div class="flex justify-between items-center">
            <div class="flex items-center">
              <div class="w-2 h-2 rounded-full bg-green-500 mr-2"></div>
              <span class="text-sm text-gray-500">在途</span>
            </div>
            <span class="font-bold">----</span>
          </div>
        </div>
      </div>

      <!-- Right: Detailed Table -->
      <div class="w-full sm:w-7/12 mt-4 sm:mt-0 sm:pl-4">
        <el-table
          :data="inventoryData.tableData"
          size="small"
          border
          :header-cell-style="{ background: '#f5f7fa' }"
        >
          <el-table-column prop="type" label="" width="60" />
          <el-table-column prop="fba" label="FBA仓" align="center" />
          <el-table-column prop="oversea" label="海外仓" align="center" />
          <el-table-column prop="local" label="本地仓" align="center" />
          <el-table-column prop="awd" label="AWD仓" align="center" />
        </el-table>
        <div class="mt-2 text-right text-xs text-gray-400">合计: ----</div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ArrowDown } from "@element-plus/icons-vue";

// Mock Inventory Data
const inventoryTab = ref("quantity"); // 'quantity' | 'value'
const inventoryData = ref({
  pieData: [
    { value: 0, name: "FBA仓" },
    { value: 0, name: "海外仓" },
    { value: 0, name: "本地仓" },
    { value: 0, name: "AWD仓" },
  ],
  tableData: [
    { type: "在库", fba: "-", oversea: "-", local: "-", awd: "-" },
    { type: "在途", fba: "-", oversea: "-", local: "-", awd: "-" },
  ],
});

const inventoryChartOptions = computed(() => ({
  tooltip: { trigger: "item" },
  color: ["#4080FF", "#67C23A", "#E6A23C", "#F56C6C"],
  series: [
    {
      name: "库存分布",
      type: "pie",
      radius: ["50%", "70%"],
      avoidLabelOverlap: false,
      label: { show: false, position: "center" },
      emphasis: { label: { show: true, fontSize: 16, fontWeight: "bold" } },
      labelLine: { show: false },
      data: inventoryData.value.pieData,
    },
  ],
}));
</script>
