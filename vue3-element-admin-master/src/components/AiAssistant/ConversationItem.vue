<template>
  <div
    class="conversation-item"
    :class="{ 'is-active': active }"
    @click="$emit('select', conversation.id)"
  >
    <el-icon v-if="conversation.is_pinned" class="conversation-item__pin"><Top /></el-icon>
    <span
      v-if="conversation.app_icon"
      class="conversation-item__app-icon"
      :title="conversation.app_name || ''"
    >
      {{ conversation.app_icon }}
    </span>
    <span class="conversation-item__title">{{ conversation.title || "新对话" }}</span>

    <el-dropdown
      trigger="click"
      placement="bottom-end"
      class="conversation-item__menu"
      @click.stop
      @command="handleCommand"
    >
      <el-button :icon="More" circle text size="small" @click.stop />
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item :icon="conversation.is_pinned ? Bottom : Top" command="pin">
            {{ conversation.is_pinned ? "取消置顶" : "置顶" }}
          </el-dropdown-item>
          <el-dropdown-item :icon="EditPen" command="rename">重命名</el-dropdown-item>
          <el-dropdown-item :icon="Download" command="export">导出 Markdown</el-dropdown-item>

          <el-dropdown
            v-if="groups.length > 0 || conversation.group_id"
            placement="left-start"
            trigger="hover"
          >
            <el-dropdown-item :icon="FolderOpened">
              移到分组
              <el-icon class="conversation-item__arrow"><ArrowRight /></el-icon>
            </el-dropdown-item>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-if="conversation.group_id"
                  @click="$emit('move', conversation, null)"
                >
                  <el-icon><Remove /></el-icon>
                  <span>移出分组</span>
                </el-dropdown-item>
                <el-dropdown-item
                  v-for="group in groups"
                  :key="group.id"
                  :disabled="group.id === conversation.group_id"
                  @click="$emit('move', conversation, group.id)"
                >
                  <el-icon><Folder /></el-icon>
                  <span>{{ group.name }}</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <el-dropdown-item :icon="Delete" command="delete" divided>
            <span style="color: var(--el-color-danger)">删除</span>
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
/**
 * 单条会话列表项。
 *
 * 职责：
 *   - 展示标题、置顶图标、hover/active 时的"..."操作菜单
 *   - 把所有副作用通过事件抛给父组件 ChatPanel，本组件零业务逻辑
 *
 * 所属板块：aiAssistant。
 */

import {
  ArrowRight,
  Bottom,
  Delete,
  Download,
  EditPen,
  Folder,
  FolderOpened,
  More,
  Remove,
  Top,
} from "@element-plus/icons-vue";
import type { AiConversation, AiConversationGroup } from "@/types/aiAssistant/planSchema";

const props = defineProps<{
  conversation: AiConversation;
  groups: AiConversationGroup[];
  active: boolean;
}>();

const emit = defineEmits<{
  (e: "select", id: string): void;
  (e: "rename", conversation: AiConversation): void;
  (e: "delete", id: string): void;
  (e: "pin", conversation: AiConversation): void;
  (e: "move", conversation: AiConversation, groupId: string | null): void;
  (e: "export", conversation: AiConversation): void;
}>();

/**
 * 处理 "..." 下拉菜单命令分发。
 *
 * @param command - 菜单 command 字符串
 */
function handleCommand(command: string): void {
  if (command === "rename") emit("rename", props.conversation);
  else if (command === "delete") emit("delete", props.conversation.id);
  else if (command === "pin") emit("pin", props.conversation);
  else if (command === "export") emit("export", props.conversation);
}
</script>

<style scoped lang="scss">
.conversation-item {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 8px 10px;
  margin: 1px 0;
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.15s;

  &__pin {
    flex-shrink: 0;
    font-size: 14px;
    color: var(--el-color-warning);
  }

  &__app-icon {
    flex-shrink: 0;
    font-size: 14px;
    line-height: 1;
  }

  &__title {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 13.5px;
    line-height: 1.4;
    color: var(--el-text-color-primary);
    white-space: nowrap;
  }

  &__menu {
    visibility: hidden;
    flex-shrink: 0;
  }

  &__arrow {
    margin-left: auto;
    font-size: 12px;
  }

  &:hover {
    background: var(--el-fill-color);

    .conversation-item__menu {
      visibility: visible;
    }
  }

  &.is-active {
    background: var(--el-color-primary-light-9);

    .conversation-item__title {
      font-weight: 500;
      color: var(--el-color-primary);
    }

    .conversation-item__menu {
      visibility: visible;
    }
  }
}
</style>
