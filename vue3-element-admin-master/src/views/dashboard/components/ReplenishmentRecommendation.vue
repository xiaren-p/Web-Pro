<template>
  <el-card shadow="never" class="h-full">
    <template #header>
      <div class="flex justify-between items-center flex-wrap gap-2">
        <span class="font-bold text-base flex items-center">
          补货建议
          <el-icon class="ml-1"><ArrowDown /></el-icon>
        </span>
        <div class="flex items-center">
          <el-checkbox v-model="onlyMyFocus" label="仅看我关注" size="small" class="mr-2" />
          <el-radio-group v-model="replenishmentType" size="small">
            <el-radio-button value="1">ASIN</el-radio-button>
            <el-radio-button value="4">父ASIN</el-radio-button>
            <el-radio-button value="2">MSKU</el-radio-button>
            <el-radio-button value="3">SKU</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </template>

    <el-table
      :data="replenishmentData"
      border
      size="small"
      :header-cell-style="{ background: '#f5f7fa' }"
    >
      <el-table-column label="紧急程度/补货类型" prop="type" min-width="140">
        <template #default="scope">
          <div class="font-bold text-gray-700">{{ scope.row.type }}</div>
        </template>
      </el-table-column>
      <el-table-column label="正常" prop="normal" align="center">
        <template #header>
          <div class="flex items-center justify-center">
            正常
            <el-icon class="ml-1 text-gray-400"><QuestionFilled /></el-icon>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="加急" prop="urgent" align="center">
        <template #header>
          <div class="flex items-center justify-center">
            加急
            <el-icon class="ml-1 text-gray-400"><QuestionFilled /></el-icon>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="断货风险" prop="risk" align="center">
        <template #header>
          <div class="flex items-center justify-center">
            断货风险
            <el-icon class="ml-1 text-gray-400"><QuestionFilled /></el-icon>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div class="mt-2 flex border-t pt-2 bg-gray-50 px-2 text-sm">
      <div class="w-[140px] font-bold text-center">总计</div>
      <div class="flex-1 text-center">0</div>
      <div class="flex-1 text-center">0</div>
      <div class="flex-1 text-center">0</div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ArrowDown, QuestionFilled } from "@element-plus/icons-vue";

// Mock Replenishment Data
const replenishmentType = ref("1"); // 1:ASIN, 4:Parent, 2:MSKU, 3:SKU
const onlyMyFocus = ref(false);
const replenishmentData = ref([
  { type: "需采购", normal: 0, urgent: 0, risk: 0 },
  { type: "需本地发货", normal: 0, urgent: 0, risk: 0 },
  { type: "需海外仓发货", normal: 0, urgent: 0, risk: 0 },
]);
</script>
