<template>
  <el-card class="search-form-card" shadow="hover">
    <el-form ref="formRef" :model="queryParams" inline>
      <el-form-item label="标签名称">
        <el-input
          v-model="queryParams.tagName"
          placeholder="请输入标签名称"
          clearable
          @keyup.enter="handleSearch"
        />
      </el-form-item>
      <el-form-item label="标签类型">
        <el-select
          v-model="queryParams.type"
          placeholder="请选择标签类型"
          clearable
          style="width: 200px"
        >
          <el-option
            v-for="item in tagTypeOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select
          v-model="queryParams.status"
          placeholder="请选择状态"
          clearable
          style="width: 140px"
        >
          <el-option
            v-for="item in tagStatusOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="创建人">
        <el-input
          v-model="queryParams.createByName"
          placeholder="请输入创建人"
          clearable
          @keyup.enter="handleSearch"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
        <el-button :icon="Refresh" @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
/**
 * Listing 标签管理搜索表单组件。
 */
import { reactive, ref } from "vue";
import { Search, Refresh } from "@element-plus/icons-vue";
import { tagTypeOptions, tagStatusOptions } from "../constants";

const emit = defineEmits(["search", "reset"]);

const formRef = ref();

const queryParams = reactive({
  tagName: "",
  type: "",
  status: "",
  createByName: "",
});

function handleSearch() {
  emit("search", { ...queryParams });
}

function handleReset() {
  queryParams.tagName = "";
  queryParams.type = "";
  queryParams.status = "";
  queryParams.createByName = "";
  emit("reset", { ...queryParams });
}
</script>

<style scoped lang="scss">
.search-form-card {
  margin-bottom: 16px;

  :deep(.el-card__body) {
    padding: 16px 20px;
  }

  :deep(.el-form-item) {
    margin-right: 16px;
    margin-bottom: 0;
  }
}
</style>
