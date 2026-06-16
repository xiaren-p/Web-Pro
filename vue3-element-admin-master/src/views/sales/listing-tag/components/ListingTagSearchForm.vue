<template>
  <div class="search-form">
    <el-form ref="formRef" :model="queryParams" inline>
      <el-form-item label="标签名称" class="filter-item">
        <el-input
          v-model="queryParams.tagName"
          placeholder="请输入标签名称"
          clearable
          @keyup.enter="handleSearch"
        />
      </el-form-item>
      <el-form-item label="标签类型" class="filter-item">
        <el-select
          v-model="queryParams.type"
          placeholder="选择标签类型"
          clearable
          filterable
          allow-create
          style="width: 180px"
        >
          <el-option v-for="item in typeOptions" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态" class="filter-item">
        <el-select
          v-model="queryParams.status"
          placeholder="选择状态"
          clearable
          style="width: 130px"
        >
          <el-option
            v-for="item in tagStatusOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="创建人" class="filter-item">
        <el-input
          v-model="queryParams.createByName"
          placeholder="请输入创建人"
          clearable
          @keyup.enter="handleSearch"
        />
      </el-form-item>
      <el-form-item class="filter-item">
        <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
        <el-button :icon="Refresh" @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { Search, Refresh } from "@element-plus/icons-vue";
import { tagStatusOptions } from "@/views/sales/listing-tag/constants";

defineProps<{
  typeOptions: string[];
}>();

const emit = defineEmits(["search", "reset"]);

const formRef = ref();

const queryParams = reactive({
  tagName: "",
  type: "",
  status: "",
  createByName: "",
});

const handleSearch = () => {
  emit("search", { ...queryParams });
};

const handleReset = () => {
  queryParams.tagName = "";
  queryParams.type = "";
  queryParams.status = "";
  queryParams.createByName = "";
  emit("reset", { ...queryParams });
};
</script>

<style scoped lang="scss">
.search-form {
  :deep(.el-form) {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 0;
  }

  :deep(.el-form-item) {
    margin-right: 20px;
    margin-bottom: 0;

    .el-form-item__label {
      font-weight: 600;
      color: #475569;
    }
  }

  :deep(.el-button) {
    font-weight: 600;
  }
}
</style>
