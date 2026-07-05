<template>
  <div>
    <el-upload
      v-model:file-list="fileList"
      class="multi-upload"
      action="#"
      :limit="limit"
      :before-upload="handleBeforeUpload"
      :http-request="handleUpload"
      :on-success="handleSuccess"
      :on-error="handleError"
      :on-exceed="handleExceed"
      :on-preview="handlePreviewImage"
      list-type="picture-card"
      :accept="accept"
    >
      <el-icon><Plus /></el-icon>
    </el-upload>
    <el-dialog v-model="isPreviewVisible" @close="handlePreviewClose">
      <img :src="modelValue[previewImageIndex]" style="width: 100%" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * 多图片上传组件（已下线：上传功能返回错误提示）。支持 v-model 绑定图片 URL 数组。
 */
import { UploadRawFile, UploadRequestOptions, UploadUserFile } from "element-plus";

type FileInfo = { url: string; name?: string };

interface Props {
  data?: Record<string, unknown>;
  name?: string;
  limit?: number;
  maxFileSize?: number;
  accept?: string;
}

const props = withDefaults(defineProps<Props>(), {
  data: () => ({}),
  name: "file",
  limit: 10,
  maxFileSize: 10,
  accept: "image/*",
});

const isPreviewVisible = ref(false);
const previewImageIndex = ref(0);

const modelValue = defineModel<string[]>("modelValue", { default: () => [] });
const fileList = ref<UploadUserFile[]>([]);

/** 删除指定图片。 */
function handleRemove(imageUrl: string) {
  const index = modelValue.value.indexOf(imageUrl);
  if (index !== -1) {
    modelValue.value.splice(index, 1);
    fileList.value.splice(index, 1);
  }
}

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

/** 上传文件。 */
function handleUpload(options: UploadRequestOptions) {
  return new Promise((_resolve, reject) => {
    ElMessage.error("图片上传功能已下线");
    reject(new Error("File module decommissioned"));
  });
}

/** 上传超出限制。 */
function handleExceed() {
  ElMessage.warning("最多只能上传" + props.limit + "张图片");
}

/** 上传成功回调。 */
function handleSuccess(fileInfo: FileInfo, uploadFile: UploadUserFile) {
  ElMessage.success("上传成功");
  const index = fileList.value.findIndex((file) => file.uid === uploadFile.uid);
  if (index !== -1) {
    fileList.value[index].url = fileInfo.url;
    fileList.value[index].status = "success";
    modelValue.value[index] = fileInfo.url;
  }
}

/** 上传失败回调。 */
function handleError(error: unknown) {
  console.log("handleError");
  ElMessage.error("上传失败: " + (error as Error).message);
}

/** 预览图片。 */
function handlePreviewImage(imageUrl: string) {
  previewImageIndex.value = modelValue.value.findIndex((url) => url === imageUrl);
  isPreviewVisible.value = true;
}

/** 关闭预览。 */
function handlePreviewClose() {
  isPreviewVisible.value = false;
}

onMounted(() => {
  fileList.value = modelValue.value.map((url) => ({ url }) as UploadUserFile);
});
</script>

<style lang="scss" scoped></style>
