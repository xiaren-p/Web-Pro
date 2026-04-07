<template>
  <el-card shadow="never" class="h-full">
    <template #header>
      <div class="flex justify-between items-center">
        <span class="font-bold text-base flex items-center">
          评论统计
          <el-icon class="ml-1"><ArrowDown /></el-icon>
        </span>
      </div>
    </template>

    <!-- Review Section -->
    <div class="mb-6">
      <div
        class="flex items-center text-sm font-bold text-gray-700 mb-2 border-l-4 border-blue-500 pl-2"
      >
        review
      </div>
      <div class="bg-gray-50 p-3 rounded">
        <div class="flex justify-between mb-2">
          <div class="text-xs text-gray-500">今日新增</div>
          <div class="font-bold text-lg">{{ reviewData.review.todayAdded }}</div>
        </div>

        <!-- Tiny Bar Chart -->
        <div class="h-8 flex items-end space-x-1 mb-2">
          <div
            v-for="(h, i) in reviewData.review.trend"
            :key="i"
            :style="{ height: h + '%' }"
            class="bg-blue-300 flex-1 rounded-t-sm opacity-80 hover:opacity-100"
          ></div>
        </div>

        <div class="flex justify-between text-xs text-gray-500">
          <span>
            中差评
            <span class="text-red-500 font-bold">{{ reviewData.review.todayNegative }}</span>
          </span>
          <span>删评 {{ reviewData.review.todayDeleted }}</span>
          <span>改评 {{ reviewData.review.todayModified }}</span>
        </div>
      </div>
    </div>

    <!-- Feedback Section -->
    <div>
      <div
        class="flex items-center text-sm font-bold text-gray-700 mb-2 border-l-4 border-orange-500 pl-2"
      >
        feedback
      </div>
      <div class="bg-gray-50 p-3 rounded">
        <div class="flex justify-between mb-2">
          <div class="text-xs text-gray-500">今日新增</div>
          <div class="font-bold text-lg">{{ reviewData.feedback.todayAdded }}</div>
        </div>

        <!-- Tiny Bar Chart -->
        <div class="h-8 flex items-end space-x-1 mb-2">
          <div
            v-for="(h, i) in reviewData.feedback.trend"
            :key="i"
            :style="{ height: h + '%' }"
            class="bg-orange-300 flex-1 rounded-t-sm opacity-80 hover:opacity-100"
          ></div>
        </div>

        <div class="flex justify-between text-xs text-gray-500">
          <span>
            中差评
            <span class="text-gray-800 font-bold">
              {{ reviewData.feedback.todayNegative }}
            </span>
          </span>
          <span>删评 {{ reviewData.feedback.todayDeleted }}</span>
          <span>改评 {{ reviewData.feedback.todayModified }}</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ArrowDown } from "@element-plus/icons-vue";

// Mock Review Data
const reviewData = ref({
  review: {
    todayAdded: 9,
    todayNegative: 3,
    todayDeleted: 0,
    todayModified: 0,
    trend: [10, 20, 30, 40, 100, 20, 43, 41, 6, 25, 13, 12, 26, 13, 17],
  },
  feedback: {
    todayAdded: 1,
    todayNegative: 0,
    todayDeleted: 0,
    todayModified: 0,
    trend: [20, 20, 40, 20, 80, 60, 0, 100, 40, 20, 20, 20, 40, 40, 20],
  },
});
</script>
