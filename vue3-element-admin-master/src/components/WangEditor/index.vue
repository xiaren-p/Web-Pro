<template>
  <div style="z-index: 999; border: 1px solid var(--el-border-color)">
    <Toolbar
      :editor="editorRef"
      mode="simple"
      :default-config="toolbarConfig"
      style="border-bottom: 1px solid var(--el-border-color)"
    />
    <Editor
      v-model="modelValue"
      :style="{ height: height, overflowY: 'hidden' }"
      :default-config="editorConfig"
      mode="simple"
      @on-created="handleCreated"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 基于 wangEditor-next 的富文本编辑器组件。
 * 版权所有 (c) 2021-present 有来开源组织 (MIT)
 * 项目地址：https://gitee.com/youlaiorg/vue3-element-admin
 */
import "@wangeditor-next/editor/dist/css/style.css";
import { Toolbar, Editor } from "@wangeditor-next/editor-for-vue";
import { IToolbarConfig, IEditorConfig, IDomEditor } from "@wangeditor-next/editor";
import { UploadAPI } from "@/api/upload";

type InsertFnType = (_url: string, _alt: string, _href: string) => void;

defineProps<{ height?: string }>();

const modelValue = defineModel<string>("modelValue");

const editorRef = shallowRef<IDomEditor>();

const toolbarConfig = ref<Partial<IToolbarConfig>>({});

const editorConfig = ref<Partial<IEditorConfig>>({
  placeholder: "请输入内容...",
  MENU_CONF: {
    uploadImage: {
      async customUpload(file: File, insertFn: InsertFnType) {
        const maxSizeMB = 2;
        if (file.size > maxSizeMB * 1024 * 1024) {
          ElMessage.error(`图片过大，不能超过 ${maxSizeMB}MB`);
          return;
        }
        try {
          const res = await UploadAPI.uploadImage(file);
          const url = res?.url;
          if (!url) throw new Error("上传失败");
          insertFn(url, file.name, url);
        } catch (err: unknown) {
          ElMessage.error(err instanceof Error ? err.message : "图片上传失败");
        }
      },
      // wangeditor v5 类型系统复杂，MENU_CONF.uploadImage 类型不兼容 Partial<IEditorConfig>，需 any 绕过
    } as any,
  },
});

/** 记录 editor 实例。 */
function handleCreated(editor: IDomEditor) {
  editorRef.value = editor;
}

onBeforeUnmount(() => {
  editorRef.value?.destroy();
});
</script>
