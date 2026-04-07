<template>
  <el-dialog v-model="visible" title="同步队列" width="800px">
    <div class="queue-search" style="margin-bottom: 15px">
      <el-input
        v-model="queryParams.imageGroup"
        placeholder="搜索图片组"
        clearable
        style="width: 200px; margin-right: 10px"
        @keyup.enter="handleQueueQuery"
      />
      <el-button type="primary" icon="search" @click="handleQueueQuery">搜索</el-button>
    </div>

    <el-table v-loading="loading" :data="list" border>
      <el-table-column type="index" label="序号" width="60" align="center" />
      <el-table-column property="imageGroup" label="图片组" />
      <el-table-column property="cloudPath" label="路径" show-overflow-tooltip />
    </el-table>

    <div class="pagination-container">
      <el-pagination
        v-model:current-page="queryParams.pageNum"
        v-model:page-size="queryParams.pageSize"
        layout="total, prev, pager, next"
        :total="total"
        @current-change="handleQueueQuery"
      />
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { ImageUploadAPI } from "@/backend";
import { ElMessage } from "element-plus";

const visible = ref(false);
const loading = ref(false);
const list = ref<any[]>([]);
const total = ref(0);

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  imageGroup: "",
});

function open() {
  visible.value = true;
  queryParams.pageNum = 1;
  queryParams.imageGroup = "";
  handleQueueQuery();
}

function handleQueueQuery() {
  loading.value = true;
  ImageUploadAPI.getQueue()
    .then((res: any) => {
      // Backend returns the list directly (wrapped in drf_ok, unwrapped by request interceptor)
      const rawList = Array.isArray(res) ? res : [];

      // Map fields: sku -> imageGroup, local_path -> cloudPath
      let allData = rawList.map((item: any) => ({
        ...item,
        imageGroup: item.sku,
        cloudPath: item.local_path,
      }));

      // Client-side filtering
      if (queryParams.imageGroup) {
        const keyword = queryParams.imageGroup.trim().toLowerCase();
        allData = allData.filter(
          (item: any) => item.imageGroup && String(item.imageGroup).toLowerCase().includes(keyword)
        );
      }

      total.value = allData.length;

      // Client-side pagination
      const { pageNum, pageSize } = queryParams;
      const start = (pageNum - 1) * pageSize;
      list.value = allData.slice(start, start + pageSize);
    })
    .catch((err) => {
      console.error("Fetch queue error:", err);
      list.value = [];
      total.value = 0;
      ElMessage.error("获取同步队列失败");
    })
    .finally(() => {
      loading.value = false;
    });
}

defineExpose({ open });
</script>

<style scoped>
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 15px;
}
</style>
