<template>
  <div class="dashboard-container">
    <DashboardHeader />

    <el-row :gutter="10" class="mt-5">
      <!-- Real-time Sales -->
      <el-col :xs="24" :lg="12">
        <RealTimeSales />
      </el-col>

      <!-- Real-time Ads -->
      <el-col :xs="24" :lg="12">
        <RealTimeAds />
      </el-col>
    </el-row>

    <el-row :gutter="10" class="mt-5">
      <!-- Inventory Overview -->
      <el-col :xs="24" :lg="12">
        <InventoryOverview />
      </el-col>

      <!-- Store Performance -->
      <el-col :xs="24" :lg="6">
        <StorePerformance />
      </el-col>

      <!-- Review Statistics -->
      <el-col :xs="24" :lg="6">
        <ReviewStatistics />
      </el-col>
    </el-row>

    <el-row :gutter="10" class="mt-5">
      <!-- Replenishment Recommendation -->
      <el-col :xs="24" :lg="12">
        <ReplenishmentRecommendation />
      </el-col>

      <!-- Settlement Profit -->
      <el-col :xs="24" :lg="12">
        <SettlementProfit />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import DashboardHeader from "./components/DashboardHeader.vue";
import RealTimeSales from "./components/RealTimeSales.vue";
import RealTimeAds from "./components/RealTimeAds.vue";
import InventoryOverview from "./components/InventoryOverview.vue";
import StorePerformance from "./components/StorePerformance.vue";
import ReviewStatistics from "./components/ReviewStatistics.vue";
import ReplenishmentRecommendation from "./components/ReplenishmentRecommendation.vue";
import SettlementProfit from "./components/SettlementProfit.vue";

defineOptions({
  name: "Dashboard",
  inheritAttrs: false,
});
</script>

<style lang="scss" scoped>
.dashboard-container {
  position: relative;
  padding: 24px;
}
</style>
