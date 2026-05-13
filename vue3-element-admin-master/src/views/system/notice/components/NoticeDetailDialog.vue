<template>
  <el-dialog v-model="visible" :show-close="false" width="50%" append-to-body @close="handleClose">
    <template #header>
      <div class="flex-x-between">
        <span>通知公告详情</span>
        <div class="dialog-toolbar">
          <el-button circle @click="handleClose">
            <template #icon>
              <Close />
            </template>
          </el-button>
        </div>
      </div>
    </template>
    <el-descriptions :column="1">
      <el-descriptions-item label="标题：">
        {{ currentNotice.title }}
      </el-descriptions-item>
      <el-descriptions-item label="发布状态：">
        <el-tag v-if="currentNotice.publishStatus == 0" type="info">未发布</el-tag>
        <el-tag v-else-if="currentNotice.publishStatus == 1" type="success">已发布</el-tag>
        <el-tag v-else-if="currentNotice.publishStatus == -1" type="warning">已撤回</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="发布人：">
        {{ currentNotice.publisherName }}
      </el-descriptions-item>
      <el-descriptions-item label="发布时间：">
        {{ currentNotice.publishTime }}
      </el-descriptions-item>
      <el-descriptions-item label="通知类型：">
        <DictLabel v-model="currentNotice.type" code="notice_type" />
      </el-descriptions-item>
      <el-descriptions-item label="通知等级：">
        <DictLabel v-model="currentNotice.level" code="notice_level" />
      </el-descriptions-item>
      <el-descriptions-item label="目标类型：">
        <el-tag v-if="currentNotice.targetType == 1" type="warning">全体</el-tag>
        <el-tag v-else-if="currentNotice.targetType == 2" type="success">指定</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="公告内容：">
        <div class="notice-content" v-html="currentNotice.content" />
      </el-descriptions-item>
    </el-descriptions>
  </el-dialog>
</template>

<script setup lang="ts">
import { NoticeAPI, type NoticeDetailVO } from "@/api/notice";

const visible = ref(false);
const currentNotice = ref<NoticeDetailVO>({});

async function open(id: string) {
  const noticeDetail = await NoticeAPI.getDetail(id);
  currentNotice.value = noticeDetail;
  visible.value = true;
}

function handleClose() {
  visible.value = false;
}

defineExpose({ open });
</script>
