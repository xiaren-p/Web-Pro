<template>
  <el-card shadow="never" class="h-full">
    <template #header>
      <div class="flex justify-between items-center flex-wrap gap-2">
        <span class="font-bold text-base flex items-center">
          结算利润
          <el-icon class="ml-1"><ArrowDown /></el-icon>
        </span>
        <div class="flex items-center gap-2">
          <el-radio-group v-model="profitRange" size="small">
            <el-radio-button value="0">昨日</el-radio-button>
            <el-radio-button value="1">前7天</el-radio-button>
            <el-radio-button value="2">前30天</el-radio-button>
            <el-radio-button value="3">自定义</el-radio-button>
          </el-radio-group>
          <el-date-picker
            v-if="profitRange === '3'"
            v-model="profitDateRange"
            type="daterange"
            range-separator="-"
            start-placeholder="Start"
            end-placeholder="End"
            size="small"
            style="width: 200px"
          />
          <div class="flex border rounded ml-2">
            <div class="px-2 py-1 cursor-pointer bg-blue-50 text-blue-500">
              <el-icon><DataLine /></el-icon>
            </div>
            <div class="px-2 py-1 cursor-pointer border-l hover:bg-gray-50">
              <el-icon><Menu /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div class="flex flex-col h-full">
      <!-- Metrics -->
      <div class="flex gap-4 mb-4">
        <div class="flex-1 bg-gray-50 p-3 rounded">
          <div class="text-xs text-gray-500 mb-1">平台收入</div>
          <div class="font-bold">{{ profitData.income }}</div>
        </div>
        <div class="flex-1 bg-gray-50 p-3 rounded">
          <div class="text-xs text-gray-500 mb-1">平台支出</div>
          <div class="font-bold text-red-500">{{ profitData.expense }}</div>
        </div>
        <div class="flex-1 bg-gray-50 p-3 rounded">
          <div class="text-xs text-gray-500 mb-1">毛利润</div>
          <div class="font-bold text-green-600">{{ profitData.profit }}</div>
        </div>
        <div class="flex-1 bg-gray-50 p-3 rounded">
          <div class="text-xs text-gray-500 mb-1">毛利率</div>
          <div class="font-bold text-green-600">{{ profitData.margin }}</div>
        </div>
      </div>

      <!-- Charts -->
      <div class="flex-1 flex gap-4 min-h-[200px]">
        <div class="flex-1 relative border rounded p-2">
          <ECharts :options="profitBarOptions" width="100%" height="100%" />
        </div>
        <div class="w-1/3 relative border rounded p-2">
          <ECharts :options="profitPieOptions" width="100%" height="100%" />
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ArrowDown, DataLine, Menu } from "@element-plus/icons-vue";

// Mock Settlement Profit Data
const profitRange = ref("0"); // 0:Yesterday, 1:7Days, 2:30Days, 3:Custom
const profitDateRange = ref([]);
const profitData = ref({
  income: "$ ------",
  expense: "$ ------",
  profit: "$ ------",
  margin: "------",
  barData: [
    { date: "01-01", value: 0 },
    { date: "01-02", value: 0 },
    { date: "01-03", value: 0 },
    { date: "01-04", value: 0 },
    { date: "01-05", value: 0 },
    { date: "01-06", value: 0 },
    { date: "01-07", value: 0 },
  ],
  pieData: [
    { name: "广告", value: 0 },
    { name: "采购", value: 0 },
    { name: "物流", value: 0 },
    { name: "佣金", value: 0 },
  ],
});

// Settlement Chart Options
const profitBarOptions = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { top: "10%", bottom: "20%", left: "10%", right: "5%" },
  xAxis: {
    type: "category",
    data: profitData.value.barData.map((i) => i.date),
    axisLabel: { fontSize: 10 },
  },
  yAxis: { type: "value", axisLabel: { fontSize: 10 } },
  series: [
    {
      type: "bar",
      data: profitData.value.barData.map((i) => i.value),
      color: "#4080FF",
      barWidth: "40%",
    },
  ],
}));

const profitPieOptions = computed(() => ({
  tooltip: { trigger: "item" },
  series: [
    {
      type: "pie",
      radius: ["40%", "70%"],
      center: ["50%", "50%"],
      data: profitData.value.pieData,
      label: { show: false },
    },
  ],
}));
</script>
