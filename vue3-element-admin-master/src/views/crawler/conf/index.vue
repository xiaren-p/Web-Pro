<template>
  <div class="app-container">
    <el-tabs v-model="activeTab" type="card" @tab-click="handleTabChange">
      <el-tab-pane label="服务器配置" name="server" />
      <el-tab-pane label="卖家精灵账号配置" name="seller" />
    </el-tabs>

    <div style="margin-top: 12px">
      <ServerConfig v-if="activeTab === 'server'" />
      <SellerConfig v-else />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import ServerConfig from "./ServerConfig.vue";
import SellerConfig from "./SellerConfig.vue";

const activeTab = ref<"server" | "seller">("server");

function handleTabChange() {
  // 子组件各自管理数据，切换时仅切换视图
}
</script>

<style scoped>
.app-container {
  padding: 16px;
}
</style>
