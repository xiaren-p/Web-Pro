<template>
  <div class="search-form">
    <el-form ref="formRef" :model="queryParams" inline>
      <el-form-item label="标签名称" class="filter-item">
        <el-input
          v-model="queryParams.tagName"
          size="small"
          placeholder="请输入标签名称"
          clearable
          style="width: 180px"
          @keyup.enter="handleSearch"
        />
      </el-form-item>
      <el-form-item label="标签类型" class="filter-item">
        <FsSelect
          v-model="queryParams.type"
          size="small"
          class="filter-select w-180"
          :options="typeOptionItems"
          multiple
          placeholder="选择标签类型"
        />
      </el-form-item>
      <el-form-item label="状态" class="filter-item">
        <FsSelect
          v-model="queryParams.status"
          size="small"
          class="filter-select w-140"
          :options="tagStatusOptions"
          multiple
          placeholder="选择状态"
        />
      </el-form-item>
      <el-form-item label="创建人" class="filter-item">
        <el-input
          v-model="queryParams.createByName"
          size="small"
          placeholder="请输入创建人"
          clearable
          style="width: 160px"
          @keyup.enter="handleSearch"
        />
      </el-form-item>
      <el-form-item class="filter-item">
        <el-button type="primary" size="small" :icon="Search" @click="handleSearch">搜索</el-button>
        <el-button size="small" :icon="Refresh" @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from "vue";
import { Search, Refresh } from "@element-plus/icons-vue";
import { tagStatusOptions } from "@/views/sales/listing-tag/constants";
import FsSelect from "@/components/FsSelect.vue";

const props = defineProps<{
  typeOptions: string[];
}>();

const typeOptionItems = computed(() => props.typeOptions.map((v) => ({ label: v, value: v })));

const emit = defineEmits(["search", "reset"]);

const formRef = ref();

const queryParams = reactive({
  tagName: "",
  type: [] as string[],
  status: [] as string[],
  createByName: "",
});

const handleSearch = () => {
  emit("search", { ...queryParams });
};

const handleReset = () => {
  queryParams.tagName = "";
  queryParams.type = [];
  queryParams.status = [];
  queryParams.createByName = "";
  emit("reset", { ...queryParams });
};
</script>

<style scoped lang="scss">
.search-form {
  :deep(.el-form) {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 0;
  }

  :deep(.el-form-item) {
    margin-right: 16px;
    margin-bottom: 0;

    .el-form-item__label {
      font-weight: 600;
      color: #475569;
    }
  }
}

.w-180 {
  width: 180px;
}

.w-140 {
  width: 140px;
}
</style>
