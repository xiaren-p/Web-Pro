<template>
  <div>
    <el-upload
      v-model:file-list="fileList"
      :style="props.style"
      :before-upload="handleBeforeUpload"
      :http-request="handleUpload"
      :on-success="handleSuccess"
      :on-error="handleError"
      :on-exceed="handleExceed"
      :accept="props.accept"
      :limit="props.limit"
      multiple
    >
      <el-button type="primary" :disabled="fileList.length >= props.limit">
        {{ props.uploadBtnText }}
      </el-button>
      <template #file="{ file }">
        <template v-if="file.status === 'success'">
          <div class="el-upload-list__item-info">
            <a class="el-upload-list__item-name" @click="handleDownload(file)">
              <el-icon><Document /></el-icon>
              <span class="el-upload-list__item-file-name">{{ file.name }}</span>
              <span class="el-icon--close" @click.stop="handleRemove">
                <el-icon><Close /></el-icon>
              </span>
            </a>
          </div>
        </template>
        <template v-else>
          <div class="el-upload-list__item-info">
            <el-progress style="display: inline-flex" :percentage="file.percentage" />
          </div>
        </template>
      </template>
    </el-upload>
  </div>
</template>

<script setup lang="ts">
/**
 * 文件上传组件（已下线：上传/删除/下载功能均返回错误提示）。
 */
import {
  UploadRawFile,
  UploadUserFile,
  UploadFile,
  UploadFiles,
  UploadRequestOptions,
} from "element-plus";

type FileInfo = { name: string; url: string };

interface Props {
  name?: string;
  limit?: number;
  maxFileSize?: number;
  accept?: string;
  uploadBtnText?: string;
  style?: Record<string, string>;
  data?: Record<string, unknown>;
}

const props = withDefaults(defineProps<Props>(), {
  name: "file",
  limit: 10,
  maxFileSize: 10,
  accept: "*",
  uploadBtnText: "上传文件",
  style: () => ({ width: "300px" }),
  data: () => ({}),
});

/** @deprecated 删除文件功能已下线。 */
function handleRemove() {
  ElMessage.error("删除文件功能已下线");
}

const modelValue = defineModel<FileInfo[]>("modelValue", { required: true, default: () => [] });

const fileList = ref([] as UploadFile[]);

watch(
  modelValue,
  (value) => {
    fileList.value = value.map((item) => {
      const name = item.name ? item.name : item.url?.substring(item.url.lastIndexOf("/") + 1);
      return { name, url: item.url, status: "success", uid: getUid() } as UploadFile;
    });
  },
  { immediate: true }
);

/**
 * 上传前校验文件大小。
 *
 * @param file - 待上传文件。
 * @returns 是否通过校验。
 */
function handleBeforeUpload(file: UploadRawFile) {
  if (file.size > props.maxFileSize * 1024 * 1024) {
    ElMessage.warning("上传文件不能大于" + props.maxFileSize + "M");
    return false;
  }
  return true;
}

/**
 * 上传文件。
 *
 * @deprecated 文件上传功能已下线。
 */
function handleUpload(options: UploadRequestOptions) {
  return new Promise((_resolve, reject) => {
    const simulate = setInterval(() => {
      const uid = options.file.uid;
      const fileItem = fileList.value.find((f) => f.uid === uid);
      if (fileItem) fileItem.percentage = Math.min(99, (fileItem.percentage || 0) + 10);
    }, 200);
    ElMessage.error("文件上传功能已下线");
    clearInterval(simulate);
    reject(new Error("File module decommissioned"));
  });
}

/** 上传文件超出限制。 */
function handleExceed() {
  ElMessage.warning(`最多只能上传${props.limit}个文件`);
}

/** 上传成功回调。 */
function handleSuccess(response: unknown, uploadFile: UploadFile, files: UploadFiles) {
  ElMessage.success("上传成功");
  if (files.every((file: UploadFile) => file.status === "success" || file.status === "fail")) {
    const fileInfos = [] as FileInfo[];
    files.forEach((file: UploadFile) => {
      if (file.status === "success") {
        const res = file.response as FileInfo;
        if (res) fileInfos.push({ name: res.name, url: res.url });
      } else {
        fileList.value.splice(
          fileList.value.findIndex((e) => e.uid === file.uid),
          1
        );
      }
    });
    if (fileInfos.length > 0) modelValue.value = [...modelValue.value, ...fileInfos];
  }
}

/** 上传失败回调。 */
function handleError(error: unknown) {
  console.error(error);
  ElMessage.error("上传失败");
}

/** 下载文件。 */
function handleDownload(file: UploadUserFile) {
  if (file.url) ElMessage.error("下载文件功能已下线");
}

/** 获取不重复 ID。 */
function getUid(): number {
  return (Date.now() << 13) | Math.floor(Math.random() * 8192);
}
</script>

<style lang="scss" scoped>
.el-upload-list__item .el-icon--close {
  position: absolute;
  top: 50%;
  right: 5px;
  color: var(--el-text-color-regular);
  cursor: pointer;
  opacity: 0.75;
  transform: translateY(-50%);
  transition: opacity var(--el-transition-duration);
}
:deep(.el-upload-list) {
  margin: 0;
}
:deep(.el-upload-list__item) {
  margin: 0;
}
</style>
