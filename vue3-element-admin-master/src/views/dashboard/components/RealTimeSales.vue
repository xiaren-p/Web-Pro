<template>
  <el-card shadow="never">
    <template #header>
      <div class="flex justify-between items-center">
        <span class="font-bold text-base flex items-center">
          实时销量
          <el-icon class="ml-1"><ArrowDown /></el-icon>
        </span>
        <div class="flex items-center space-x-2">
          <span class="text-xs text-gray-500">今日：{{ salesData.date }}</span>
          <el-radio-group v-model="salesData.timeRange" size="small">
            <el-radio-button value="today">今日</el-radio-button>
            <el-radio-button value="yesterday">昨日</el-radio-button>
            <el-radio-button value="recent24h">近24h</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </template>

    <div class="flex justify-between w-full px-2">
      <div
        v-for="(item, index) in salesData.list"
        :key="index"
        class="flex flex-col flex-1 pl-2"
        :class="{ 'border-l border-gray-100': index !== 0 }"
      >
        <div class="text-gray-500 text-xs mb-1 flex items-center">
          {{ item.title }}
          <el-tooltip content="说明" placement="top">
            <el-icon class="ml-1 text-gray-400 cursor-help"><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>
        <div class="text-lg font-bold mb-1 flex items-center">
          {{ item.value }}
          <el-icon class="ml-1 text-gray-300 text-xs"><ArrowDown /></el-icon>
        </div>
        <div class="text-xs text-gray-400 flex items-center scale-90 origin-left">
          <span class="mr-1 border px-0.5 rounded bg-gray-50">{{ item.compareLabel }}</span>
          <span>{{ item.compareValue }}</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ArrowDown, QuestionFilled } from "@element-plus/icons-vue";

// Mock Sales Data
const salesData = ref({
  date: "2026-01-12 23:48",
  timezone: "UTC-08:00",
  timeRange: "today",
  list: [
    { title: "销量", value: "***", compareLabel: "昨", compareValue: "***" },
    { title: "销售额", value: "$***", compareLabel: "昨", compareValue: "$***" },
    { title: "订单量", value: "***", compareLabel: "昨", compareValue: "***" },
    { title: "平均售价", value: "$***", compareLabel: "昨", compareValue: "$***" },
    { title: "取消订单数", value: "***", compareLabel: "昨", compareValue: "***" },
  ],
});
</script>
