<template>
  <div class="profile-container">
    <!-- 错误态 -->
    <el-result v-if="loadError" icon="warning" title="加载失败" :sub-title="loadError">
      <template #extra>
        <el-button type="primary" @click="loadUserProfile">重试</el-button>
      </template>
    </el-result>

    <!-- 加载态 -->
    <el-skeleton v-else-if="isLoading" :rows="8" animated />

    <!-- 内容态 -->
    <el-row v-else :gutter="20">
      <!-- 左侧个人信息卡片 -->
      <el-col :span="8">
        <el-card class="user-card">
          <div class="user-info">
            <div class="avatar-wrapper" :class="{ 'is-uploading': isUploading }">
              <el-avatar :src="resolveAvatarSrc(userStore.userInfo.avatar ?? '')" :size="100" />
              <div class="avatar-overlay">
                <el-tooltip content="上传图片" placement="top" :show-after="400">
                  <el-icon class="overlay-icon" @click="triggerFileUpload"><Camera /></el-icon>
                </el-tooltip>
                <div class="overlay-divider" />
                <el-tooltip content="选择预设" placement="top" :show-after="400">
                  <el-icon class="overlay-icon" @click="presetDialogVisible = true">
                    <Picture />
                  </el-icon>
                </el-tooltip>
              </div>
              <input
                ref="fileInput"
                type="file"
                style="display: none"
                accept=".jpg,.jpeg,.png,.webp"
                @change="handleFileChange"
              />
            </div>
            <div class="user-name">
              <span class="nickname">{{ userProfile.nickname }}</span>
              <el-icon class="edit-icon" @click="handleOpenDialog(DialogType.ACCOUNT)">
                <Edit />
              </el-icon>
            </div>
            <div class="user-role">{{ userProfile.positionName }}</div>
          </div>
          <el-divider />
          <div class="user-stats">
            <div class="stat-item">
              <div class="stat-value">0</div>
              <div class="stat-label">待办</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">0</div>
              <div class="stat-label">消息</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">0</div>
              <div class="stat-label">通知</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧信息卡片 -->
      <el-col :span="16">
        <el-card class="info-card">
          <template #header>
            <div class="card-header">
              <span>账号信息</span>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户名">
              {{ userProfile.username }}
              <el-icon v-if="userProfile.gender === 1" class="gender-icon male">
                <Male />
              </el-icon>
              <el-icon v-else class="gender-icon female">
                <Female />
              </el-icon>
            </el-descriptions-item>
            <el-descriptions-item label="手机号码">
              {{ userProfile.mobile || "未绑定" }}
              <el-button
                v-if="userProfile.mobile"
                type="primary"
                link
                @click="() => handleOpenDialog(DialogType.MOBILE)"
              >
                更换
              </el-button>
              <el-button
                v-else
                type="primary"
                link
                @click="() => handleOpenDialog(DialogType.MOBILE)"
              >
                绑定
              </el-button>
            </el-descriptions-item>
            <el-descriptions-item label="邮箱">
              {{ userProfile.email || "未绑定" }}
              <el-button
                v-if="userProfile.email"
                type="primary"
                link
                @click="() => handleOpenDialog(DialogType.EMAIL)"
              >
                更换
              </el-button>
              <el-button
                v-else
                type="primary"
                link
                @click="() => handleOpenDialog(DialogType.EMAIL)"
              >
                绑定
              </el-button>
            </el-descriptions-item>
            <el-descriptions-item label="部门">
              {{ userProfile.deptName }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ userProfile.createTime }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card class="security-card">
          <template #header>
            <div class="card-header">
              <span>安全设置</span>
            </div>
          </template>
          <div class="security-item">
            <div class="security-info">
              <div class="security-title">账户密码</div>
              <div class="security-desc">定期修改密码有助于保护账户安全</div>
            </div>
            <el-button type="primary" link @click="() => handleOpenDialog(DialogType.PASSWORD)">
              修改
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" :width="500">
      <!-- 账号资料 -->
      <el-form
        v-if="dialogType === DialogType.ACCOUNT"
        ref="userProfileFormRef"
        :model="userProfileForm"
        :label-width="100"
      >
        <el-form-item label="昵称">
          <el-input v-model="userProfileForm.nickname" />
        </el-form-item>
        <el-form-item label="性别">
          <Dict v-model="userProfileForm.gender" code="gender" />
        </el-form-item>
      </el-form>

      <!-- 修改密码 -->
      <el-form
        v-if="dialogType === DialogType.PASSWORD"
        ref="passwordChangeFormRef"
        :model="passwordChangeForm"
        :rules="passwordChangeRules"
        :label-width="100"
      >
        <el-form-item label="原密码" prop="oldPassword">
          <el-input v-model="passwordChangeForm.oldPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="passwordChangeForm.newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="passwordChangeForm.confirmPassword" type="password" show-password />
        </el-form-item>
      </el-form>

      <!-- 绑定手机 -->
      <el-form
        v-else-if="dialogType === DialogType.MOBILE"
        ref="mobileBindingFormRef"
        :model="mobileUpdateForm"
        :rules="mobileBindingRules"
        :label-width="100"
      >
        <el-form-item label="手机号码" prop="mobile">
          <el-input v-model="mobileUpdateForm.mobile" style="width: 250px" />
        </el-form-item>
      </el-form>

      <!-- 绑定邮箱 -->
      <el-form
        v-else-if="dialogType === DialogType.EMAIL"
        ref="emailBindingFormRef"
        :model="emailUpdateForm"
        :rules="emailBindingRules"
        :label-width="100"
      >
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="emailUpdateForm.email" style="width: 250px" />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 头像裁剪弹窗 -->
    <AvatarCropper
      v-model="cropperVisible"
      :src-url="cropperSrcUrl"
      @confirm="handleCropConfirm"
      @cancel="handleCropCancel"
    />

    <!-- 预设头像选择弹窗 -->
    <el-dialog v-model="presetDialogVisible" title="选择预设头像" :width="480">
      <div class="preset-grid">
        <div
          v-for="preset in allPresets"
          :key="preset.id"
          class="preset-item"
          :class="{ active: userProfile.avatar === preset.id, selecting: isSelectingPreset }"
          @click="handleSelectPreset(preset.id)"
        >
          <el-avatar :src="preset.dataUri" :size="72" />
          <span v-if="userProfile.avatar === preset.id" class="preset-check">OK</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="presetDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * 个人资料页。
 *
 * @description 薄编排层：组合 useProfile composable + 头像上传/裁剪 + 预设选择。
 *              资料加载、表单提交、校验规则全部在 composable 中。
 */
import { ref, onMounted } from "vue";
import { ElLoading, ElMessage } from "element-plus";
import { Camera, Edit, Male, Female, Picture } from "@element-plus/icons-vue";
import { UserAPI } from "@/api/user";
import AvatarCropper from "@/components/AvatarCropper/index.vue";
import { resolveAvatarSrc, getAllPresets } from "@/utils/avatarPresets";
import { useProfile, DialogType } from "./composables/useProfile";

const {
  userProfile,
  isLoading,
  loadError,
  dialogVisible,
  dialogTitle,
  dialogType,
  userProfileForm,
  passwordChangeForm,
  mobileUpdateForm,
  emailUpdateForm,
  passwordChangeRules,
  mobileBindingRules,
  emailBindingRules,
  userStore,
  preloadFromStore,
  loadUserProfile,
  handleOpenDialog,
  handleSubmit,
} = useProfile();

/** 取消弹窗并重置对应表单。 */
function handleCancel() {
  dialogVisible.value = false;
  switch (dialogType.value) {
    case DialogType.ACCOUNT:
      userProfileFormRef.value?.resetFields();
      break;
    case DialogType.PASSWORD:
      passwordChangeFormRef.value?.resetFields();
      break;
    case DialogType.MOBILE:
      mobileBindingFormRef.value?.resetFields();
      break;
    case DialogType.EMAIL:
      emailBindingFormRef.value?.resetFields();
      break;
  }
}

const userProfileFormRef = ref();
const passwordChangeFormRef = ref();
const mobileBindingFormRef = ref();
const emailBindingFormRef = ref();

// ====== 头像上传 ======

const fileInput = ref<HTMLInputElement | null>(null);
const isUploading = ref(false);

const cropperVisible = ref(false);
const cropperSrcUrl = ref("");
let cropperObjectUrl = "";

/** 触发文件选择器。 */
function triggerFileUpload() {
  if (isUploading.value) return;
  fileInput.value?.click();
}

/**
 * 文件选择后打开裁剪弹窗。
 *
 * @description 前端白名单校验：仅允许 JPG / PNG / WEBP，最大 5MB。
 * @param e - input[type=file] change 事件。
 */
function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  const allowed = ["image/jpeg", "image/png", "image/webp"];
  if (!allowed.includes(file.type)) {
    ElMessage.error("仅支持 JPG、PNG、WEBP 格式图片");
    input.value = "";
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error("图片大小不能超过 5MB");
    input.value = "";
    return;
  }

  if (cropperObjectUrl) URL.revokeObjectURL(cropperObjectUrl);
  cropperObjectUrl = URL.createObjectURL(file);
  cropperSrcUrl.value = cropperObjectUrl;
  cropperVisible.value = true;
  input.value = "";
}

/**
 * 裁剪确认：上传裁剪后 Blob 至服务端。
 *
 * @param payload - 裁剪结果 { blob, dataUrl }。
 */
async function handleCropConfirm(payload: { blob: Blob; dataUrl: string }) {
  let loadingSvc: { close(): void } | null = null;
  try {
    isUploading.value = true;
    loadingSvc = ElLoading.service({ text: "上传中...", background: "rgba(0,0,0,0.3)" });
    const croppedFile = new File([payload.blob], "avatar.jpg", { type: "image/jpeg" });
    const res = await UserAPI.uploadAvatar(croppedFile);
    const url = res?.url ?? "";
    if (url) {
      userStore.userInfo.avatar = url;
      userProfile.value.avatar = url;
      ElMessage.success("头像已更新");
    }
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : "上传失败");
  } finally {
    isUploading.value = false;
    loadingSvc?.close();
    if (cropperObjectUrl) {
      URL.revokeObjectURL(cropperObjectUrl);
      cropperObjectUrl = "";
    }
  }
}

/** 裁剪取消：释放 Object URL。 */
function handleCropCancel() {
  if (cropperObjectUrl) {
    URL.revokeObjectURL(cropperObjectUrl);
    cropperObjectUrl = "";
  }
}

// ====== 预设头像 ======

const presetDialogVisible = ref(false);
const allPresets = getAllPresets();
const isSelectingPreset = ref(false);

/**
 * 选择预设头像并更新数据库和本地 Store。
 *
 * @param presetId - 预设标识符，如 'preset:03'。
 */
async function handleSelectPreset(presetId: string) {
  if (isSelectingPreset.value) return;
  isSelectingPreset.value = true;
  try {
    await UserAPI.updateProfile({ avatar: presetId });
    userProfile.value.avatar = presetId;
    userStore.userInfo.avatar = presetId;
    presetDialogVisible.value = false;
    ElMessage.success("头像已更新");
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : "更新失败");
  } finally {
    isSelectingPreset.value = false;
  }
}

onMounted(async () => {
  preloadFromStore();
  await loadUserProfile();
});
</script>

<style lang="scss" scoped>
.profile-container {
  min-height: calc(100vh - 84px);
  padding: 20px;
  background: var(--el-fill-color-blank);
}

.user-card {
  .user-info {
    padding: 20px 0;
    text-align: center;

    .avatar-wrapper {
      position: relative;
      display: inline-block;
      width: 100px;
      height: 100px;
      margin-bottom: 16px;
      overflow: hidden;
      cursor: pointer;
      border-radius: 50%;

      &.is-uploading {
        pointer-events: none;
        opacity: 0.65;
      }

      .avatar-overlay {
        position: absolute;
        right: 0;
        bottom: 0;
        left: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 38px;
        background: rgba(0, 0, 0, 0.58);
        opacity: 0;
        transition: opacity 0.22s ease;

        .overlay-icon {
          display: flex;
          flex: 1;
          justify-content: center;
          font-size: 17px;
          color: rgba(255, 255, 255, 0.88);
          cursor: pointer;
          transition: color 0.18s;

          &:hover {
            color: #fff;
          }
        }

        .overlay-divider {
          width: 1px;
          height: 16px;
          background: rgba(255, 255, 255, 0.28);
        }
      }

      &:hover .avatar-overlay {
        opacity: 1;
      }
    }

    .user-name {
      margin-bottom: 8px;

      .nickname {
        font-size: 18px;
        font-weight: 600;
        color: var(--el-text-color-primary);
      }

      .edit-icon {
        margin-left: 8px;
        color: var(--el-text-color-secondary);
        cursor: pointer;
        transition: all 0.3s ease;

        &:hover {
          color: var(--el-color-primary);
        }
      }
    }

    .user-role {
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
  }

  .user-stats {
    display: flex;
    justify-content: space-around;
    padding: 16px 0;

    .stat-item {
      text-align: center;

      .stat-value {
        font-size: 20px;
        font-weight: 600;
        color: var(--el-text-color-primary);
      }

      .stat-label {
        margin-top: 4px;
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
  }
}

.info-card,
.security-card {
  margin-bottom: 20px;

  .card-header {
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }
}

.security-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;

  .security-info {
    .security-title {
      margin-bottom: 4px;
      font-size: 16px;
      font-weight: 500;
      color: var(--el-text-color-primary);
    }

    .security-desc {
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
  }
}

.el-descriptions {
  .el-descriptions__label {
    font-weight: 500;
    color: var(--el-text-color-regular);
  }

  .el-descriptions__content {
    color: var(--el-text-color-primary);
  }

  .gender-icon {
    margin-left: 8px;
    font-size: 16px;

    &.male {
      color: var(--el-color-primary);
    }

    &.female {
      color: var(--el-color-danger);
    }
  }
}

.el-dialog {
  .el-dialog__header {
    padding: 20px;
    margin: 0;
    border-bottom: 1px solid var(--el-border-color-light);
  }

  .el-dialog__body {
    padding: 30px 20px;
  }

  .el-dialog__footer {
    padding: 20px;
    border-top: 1px solid var(--el-border-color-light);
  }
}

.preset-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: flex-start;
  padding: 8px 0;

  .preset-item {
    position: relative;
    cursor: pointer;
    border-radius: 50%;
    transition: transform 0.2s ease;

    &:hover {
      transform: scale(1.08);
    }

    &.active {
      outline: 3px solid var(--el-color-primary);
      outline-offset: 2px;
    }

    &.selecting {
      pointer-events: none;
      cursor: wait;
    }

    .preset-check {
      position: absolute;
      right: -2px;
      bottom: -2px;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 20px;
      height: 20px;
      font-size: 12px;
      font-weight: 700;
      color: var(--el-color-white);
      background: var(--el-color-primary);
      border-radius: 50%;
    }
  }
}

@media (max-width: 768px) {
  .profile-container {
    padding: 10px;
  }

  .el-col {
    width: 100%;
  }
}
</style>
