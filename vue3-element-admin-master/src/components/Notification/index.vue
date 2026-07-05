<template>
  <el-dropdown trigger="click">
    <el-badge v-if="noticeList.length > 0" :value="noticeList.length" :max="99">
      <div class="i-svg:bell" />
    </el-badge>
    <div v-else class="i-svg:bell" />
    <template #dropdown>
      <div class="p-5">
        <template v-if="noticeList.length > 0">
          <div v-for="(item, index) in noticeList" :key="index" class="w-500px py-3">
            <div class="flex-y-center">
              <DictLabel v-model="item.type" code="notice_type" size="small" />
              <el-text
                size="small"
                class="w-200px cursor-pointer !ml-2 !flex-1"
                truncated
                @click="handleReadNotice(item.id)"
              >
                {{ item.title }}
              </el-text>
              <div class="text-xs text-gray">{{ item.publishTime }}</div>
            </div>
          </div>
          <el-divider />
          <div class="flex-x-between">
            <el-link type="primary" underline="never" @click="handleViewMoreNotice">
              <span class="text-xs">查看更多</span>
              <el-icon class="text-xs"><ArrowRight /></el-icon>
            </el-link>
            <el-link
              v-if="noticeList.length > 0"
              type="primary"
              underline="never"
              @click="handleMarkAllAsRead"
            >
              <span class="text-xs">全部已读</span>
            </el-link>
          </div>
        </template>
        <template v-else>
          <div class="flex-center h-150px w-350px">
            <el-empty :image-size="50" description="暂无消息" />
          </div>
        </template>
      </div>
    </template>
  </el-dropdown>

  <el-dialog
    v-model="noticeDialogVisible"
    :title="noticeDetail?.title ?? '通知详情'"
    width="800px"
    custom-class="notification-detail"
  >
    <div v-if="noticeDetail" class="p-x-20px">
      <div class="flex-y-center mb-16px text-13px text-color-secondary">
        <span class="flex-y-center">
          <el-icon><User /></el-icon>
          {{ noticeDetail.publisherName }}
        </span>
        <span class="ml-2 flex-y-center">
          <el-icon><Timer /></el-icon>
          {{ noticeDetail.publishTime }}
        </span>
      </div>
      <div class="max-h-60vh pt-16px mb-24px overflow-y-auto border-t border-solid border-color">
        <!-- 后端返回的 HTML 内容，由后端负责 XSS 过滤 -->
        <div v-html="noticeDetail.content"></div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 通知组件：WebSocket 实时推送 + 下拉列表，支持查看详情、全部已读、跳转通知页。
 */
import { NoticeAPI, type NoticePageVO, type NoticeDetailVO } from "@/api/notice";
import router from "@/router";
import { useStomp } from "@/composables/websocket/useStomp";

const noticeList = ref<NoticePageVO[]>([]);
const noticeDialogVisible = ref(false);
const noticeDetail = ref<NoticeDetailVO | null>(null);

const { subscribe, unsubscribe, isConnected } = useStomp();

watch(
  () => isConnected.value,
  (connected) => {
    if (connected) {
      subscribe("/user/queue/message", (message: unknown) => {
        console.log("收到通知消息：", message);
        const data = JSON.parse((message as { body: string }).body);
        const id = data.id;
        if (!noticeList.value.some((notice) => notice.id == id)) {
          noticeList.value.unshift({
            id,
            title: data.title as string,
            type: data.type as number,
            publishTime: data.publishTime as string,
          });
          ElNotification({
            title: "您收到一条新的通知消息！",
            message: data.title,
            type: "success",
            position: "bottom-right",
          });
        }
      });
    }
  }
);

/** 获取当前用户的未读通知。 */
function fetchMyNotice() {
  NoticeAPI.getMyNoticePage({ pageNum: 1, pageSize: 5, isRead: 0 }).then((data) => {
    noticeList.value = data.list;
  });
}

/**
 * 阅读通知详情并标记已读。
 *
 * @param id - 通知ID。
 */
function handleReadNotice(id: string) {
  NoticeAPI.getDetail(id).then((data) => {
    noticeDialogVisible.value = true;
    noticeDetail.value = data;
    NoticeAPI.read(id)
      .then(() => {
        const index = noticeList.value.findIndex((notice) => notice.id === id);
        if (index >= 0) noticeList.value.splice(index, 1);
      })
      .catch(() => {
        console.warn("标记通知已读失败:", id);
      });
  });
}

/** 跳转到通知列表页。 */
function handleViewMoreNotice() {
  router.push({ name: "MyNotice" });
}

/** 全部标记已读。 */
function handleMarkAllAsRead() {
  NoticeAPI.readAll().then(() => {
    noticeList.value = [];
  });
}

onMounted(() => {
  fetchMyNotice();
});
onBeforeUnmount(() => {
  unsubscribe("/user/queue/message");
});
</script>

<style lang="scss" scoped></style>
