<template>
  <el-card shadow="never">
    <template #header>
      <div class="flex justify-between items-center">
        <span class="font-bold text-base flex items-center">
          实时广告
          <el-icon class="ml-1"><ArrowDown /></el-icon>
        </span>
        <div class="text-xs text-gray-500 flex items-center space-x-1">
          <span>
            统计日期:
            <span class="font-bold text-gray-700">{{ adsData.statDate }}</span>
          </span>
          <el-icon class="text-gray-400"><InfoFilled /></el-icon>
          <span>
            更新于
            <span class="text-gray-700">{{ adsData.updateTime }}</span>
          </span>
          <el-icon class="ml-1 cursor-pointer text-gray-400"><Setting /></el-icon>
        </div>
      </div>
    </template>

    <div class="flex justify-between w-full px-2">
      <div
        v-for="(item, index) in adsData.list"
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
        <div class="text-lg font-bold mb-1 text-gray-800">
          {{ item.value }}
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
import { ArrowDown, QuestionFilled, InfoFilled, Setting } from "@element-plus/icons-vue";

// Mock Ads Data
const adsData = ref({
  statDate: "01-12",
  updateTime: "01-13 15:48",
  list: [
    { title: "广告花费", value: "$***", compareLabel: "昨", compareValue: "$***" },
    { title: "广告销售额", value: "$***", compareLabel: "昨", compareValue: "$***" },
    { title: "广告订单量", value: "***", compareLabel: "昨", compareValue: "***" },
    { title: "ACOS", value: "***", compareLabel: "昨", compareValue: "***" },
    { title: "ACoAS", value: "***", compareLabel: "昨", compareValue: "***" },
  ],
});
</script>
