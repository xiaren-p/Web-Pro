<template>
  <el-upload
    action="#"
    :limit="1"
    :style="style"
    :before-upload="handleBeforeUpload"
    :http-request="handleUpload"
    :on-success="onSuccess"
    :on-error="onError"
    :show-file-list="false"
    :accept="accept"
  >
    <template #trigger>
      <img v-if="modelValue" class="single-upload__image" :src="modelValue" :style="style" />
      <el-icon v-else :style="style"><Plus /></el-icon>
    </template>
    <template #file>
      <div>
        <img v-if="modelValue" class="single-upload__image" :src="modelValue" :style="style" />
        <span class="single-upload__delete-btn" @click="handleDelete"><Close /></span>
      </div>
    </template>
  </el-upload>
</template>

<script setup lang="ts">
/**
 * 单图片上传组件：支持 v-model 绑定图片 URL，含格式校验和大小限制。
 */
import { UploadRawFile, UploadRequestOptions } from "element-plus";
import { UploadAPI } from "@/api/upload";

type FileInfo = { url: string; name?: string };

interface Props {
  data?: Record<string, unknown>;
  name?: string;
  maxFileSize?: number;
  accept?: string;
  style?: Record<string, string>;
}

const props = withDefaults(defineProps<Props>(), {
  data: () => ({}),
  name: "file",
  maxFileSize: 10,
  accept: "image/*",
  style: () => ({ width: "150px", height: "150px" }),
});

const modelValue = defineModel<string>("modelValue", { default: "" });

/**
 * 上传前校验文件格式和大小。
 *
 * @param file - 待上传文件。
 * @returns 是否通过校验。
 */
function handleBeforeUpload(file: UploadRawFile) {
  const acceptTypes = props.accept.split(",").map((type) => type.trim());
  const isValidType = acceptTypes.some((type) => {
    if (type === "image/*") return file.type.startsWith("image/");
    if (type.startsWith(".")) return file.name.toLowerCase().endsWith(type);
    return file.type === type;
  });
  if (!isValidType) {
    ElMessage.warning(`上传文件的格式不正确，仅支持：${props.accept}`);
    return false;
  }
  if (file.size > props.maxFileSize * 1024 * 1024) {
    ElMessage.warning("上传图片不能大于" + props.maxFileSize + "M");
    return false;
  }
  return true;
}

/**
 * 上传图片。
 *
 * @param options - Element Plus 上传选项。
 */
async function handleUpload(options: UploadRequestOptions) {
  const file = options.file as File;
  try {
    const res = await UploadAPI.uploadImage(file);
    const fileInfo: FileInfo = { url: res.url, name: res.name };
    options.onSuccess?.(fileInfo as unknown as Record<string, unknown>);
    return fileInfo;
  } catch (err: unknown) {
    options.onError?.(err as Error);
    throw err;
  }
}

/** 预览图片（占位）。 */
function handlePreview() {
  console.log("预览图片,停止冒泡");
}

/** 删除图片。 */
function handleDelete() {
  modelValue.value = "";
}

/**
 * 上传成功回调。
 *
 * @param fileInfo - 上传结果。
 */
function onSuccess(fileInfo: FileInfo) {
  ElMessage.success("上传成功");
  modelValue.value = fileInfo.url;
}

/**
 * 上传失败回调。
 *
 * @param error - 错误对象。
 */
function onError(error: unknown) {
  console.log("onError");
  ElMessage.error("上传失败: " + (error as Error).message);
}
</script>

<style scoped lang="scss">
:deep(.el-upload--picture-card) {
  position: relative;
  width: v-bind("props.style.width ?? '150px'");
  height: v-bind("props.style.height ?? '150px'");
}
.single-upload {
  &__image {
    border-radius: 6px;
  }
  &__delete-btn {
    position: absolute;
    top: 1px;
    right: 1px;
    font-size: 16px;
    color: var(--color-warning-500);
    cursor: pointer;
    background: var(--surface-base);
    border-radius: 100%;
    :hover {
      color: var(--color-danger-500);
    }
  }
}
</style>
