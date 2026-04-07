<template>
  <el-card shadow="never" class="h-full">
    <template #header>
      <div class="flex justify-between items-center">
        <span class="font-bold text-base flex items-center">
          店铺绩效
          <el-icon class="ml-1"><ArrowDown /></el-icon>
        </span>
        <span class="text-xs text-gray-500">2026-01-12</span>
      </div>
    </template>

    <div class="overflow-y-auto" style="max-height: 280px">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-gray-500 border-b border-gray-100">
            <th class="text-left py-2 font-normal">异常店铺数</th>
            <th class="text-right py-2 font-normal">目标值</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(item, index) in performanceData"
            :key="index"
            class="border-b border-gray-50 last:border-0 hover:bg-gray-50"
          >
            <td class="py-2">
              <div class="text-gray-700">{{ item.metric }}</div>
            </td>
            <td class="py-2 text-right">
              <span :class="getStatusClass(item.status)" class="mr-2">{{ item.value }}</span>
              <span class="text-xs text-gray-400">{{ item.target }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ArrowDown } from "@element-plus/icons-vue";

// Mock Performance Data
const performanceData = ref([
  { metric: "FBA订单缺陷率", value: "0", target: "< 1%", status: "success" },
  { metric: "FBM订单缺陷率", value: "0", target: "< 1%", status: "success" },
  { metric: "发票缺陷率", value: "1", target: "< 5%", status: "danger" },
  { metric: "政策合规性", value: "28", target: "< 0", status: "danger" },
  { metric: "迟发率", value: "0", target: "< 4%", status: "success" },
  { metric: "预配送取消率", value: "0", target: "< 2.5%", status: "success" },
  { metric: "有效追踪率", value: "0", target: "> 95%", status: "success" },
]);

const getStatusClass = (status: string) => {
  if (status === "danger") return "text-red-500 font-bold";
  if (status === "warning") return "text-yellow-500 font-bold";
  return "text-gray-800";
};
</script>
