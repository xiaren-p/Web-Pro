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
      <el-table-column label="状态" width="100" align="center">
        <template #default="scope">
          <el-tag v-if="scope.row.status === 'pending'" type="warning">待同步</el-tag>
          <el-tag v-else-if="scope.row.status === 'success'" type="success">同步成功</el-tag>
          <el-tag v-else-if="scope.row.status === 'failed'" type="danger">同步失败</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
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
/**
 * 同步队列弹窗：展示内部图片同步队列记录，支持按图片组搜索与后端分页。
 * 所属板块：listing / imageupload。
 */
import { ref, reactive } from "vue";
import { ImageUploadAPI } from "@/api/imageUpload";
import type { ImageSyncQueueVO } from "@/api/imageUpload";
import { ElMessage } from "element-plus";

const visible = ref(false);
const loading = ref(false);
const list = ref<ImageSyncQueueVO[]>([]);
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

/** 查询同步队列（后端分页 + imageGroup 过滤）。 */
function handleQueueQuery() {
  loading.value = true;
  ImageUploadAPI.getQueue(queryParams)
    .then((data) => {
      list.value = data.list;
      total.value = data.total;
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
