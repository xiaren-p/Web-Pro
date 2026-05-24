<template>
  <div class="profile-container">
    <!-- 错误态 -->
    <el-result v-if="loadError" icon="warning" title="加载失败" :sub-title="loadError">
      <template #extra>
        <el-button type="primary" @click="loadUserProfile">重试</el-button>
      </template>
    </el-result>

    <!-- 加载态 -->
    <el-skeleton v-else-if="loading" :rows="8" animated />

    <!-- 内容态 -->
    <el-row v-else :gutter="20">
      <!-- 左侧个人信息卡片 -->
      <el-col :span="8">
        <el-card class="user-card">
          <div class="user-info">
            <div class="avatar-wrapper" :class="{ 'is-uploading': uploading }">
              <el-avatar :src="resolveAvatarSrc(userStore.userInfo.avatar ?? '')" :size="100" />
              <div class="avatar-overlay">
                <el-tooltip content="上传图片" placement="top" :show-after="400">
                  <el-icon class="overlay-icon" @click="triggerFileUpload"><Camera /></el-icon>
                </el-tooltip>
                <div class="overlay-divider" />
                <el-tooltip content="选择预设" placement="top" :show-after="400">
                  <el-icon class="overlay-icon" @click="presetDialogVisible = true"><Picture /></el-icon>
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
    <el-dialog v-model="dialog.visible" :title="dialog.title" :width="500">
      <!-- 账号资料 -->
      <el-form
        v-if="dialog.type === DialogType.ACCOUNT"
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
        v-if="dialog.type === DialogType.PASSWORD"
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
        v-else-if="dialog.type === DialogType.MOBILE"
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
        v-else-if="dialog.type === DialogType.EMAIL"
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
    <avatar-cropper
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
          :class="{ active: userProfile.avatar === preset.id, selecting: selectingPreset }"
          @click="handleSelectPreset(preset.id)"
        >
          <el-avatar :src="preset.dataUri" :size="72" />
          <span v-if="userProfile.avatar === preset.id" class="preset-check">✓</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="presetDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { UserAPI } from "@/api/user";
import { useUserStoreHook } from "@/store";
import { Camera, Edit, Male, Female, Picture } from "@element-plus/icons-vue";
import { ref, reactive, onMounted } from "vue";
import { ElLoading, ElMessage } from "element-plus";
import AvatarCropper from "@/components/AvatarCropper/index.vue";
import { resolveAvatarSrc, getAllPresets } from "@/utils/avatarPresets";

// 本地类型定义
interface UserProfileVO {
  id?: string;
  username?: string;
  nickname?: string;
  avatar?: string;
  email?: string;
  mobile?: string;
  gender?: number;
  deptName?: string;
  positionName?: string;
  createTime?: string;
}
interface PasswordChangeForm {
  oldPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
}
interface MobileUpdateForm {
  mobile?: string;
}
interface EmailUpdateForm {
  email?: string;
}
interface UserProfileForm {
  id?: string;
  nickname?: string;
  gender?: number;
}

const userStore = useUserStoreHook();
const userProfile = ref<UserProfileVO>({});
const loading = ref(true);
const loadError = ref<string | null>(null);

// file input 在下方与上传逻辑一起声明

const enum DialogType {
  ACCOUNT = "account",
  PASSWORD = "password",
  MOBILE = "mobile",
  EMAIL = "email",
}

const dialog = reactive({
  visible: false,
  title: "",
  type: "" as DialogType, // 修改账号资料,修改密码、绑定手机、绑定邮箱
});
const userProfileFormRef = ref();
const passwordChangeFormRef = ref();
const mobileBindingFormRef = ref();
const emailBindingFormRef = ref();

const userProfileForm = reactive<UserProfileForm>({});
const passwordChangeForm = reactive<PasswordChangeForm>({});
const mobileUpdateForm = reactive<MobileUpdateForm>({});
const emailUpdateForm = reactive<EmailUpdateForm>({});



// 修改密码校验规则
const passwordChangeRules = {
  oldPassword: [{ required: true, message: "请输入原密码", trigger: "blur" }],
  newPassword: [{ required: true, message: "请输入新密码", trigger: "blur" }],
  confirmPassword: [{ required: true, message: "请再次输入新密码", trigger: "blur" }],
};

// 手机号校验规则
const mobileBindingRules = {
  mobile: [
    { required: true, message: "请输入手机号", trigger: "blur" },
    {
      pattern: /^1[3|4|5|6|7|8|9][0-9]\d{8}$/,
      message: "请输入正确的手机号码",
      trigger: "blur",
    },
  ],
};

// 邮箱校验规则
const emailBindingRules = {
  email: [
    { required: true, message: "请输入邮箱", trigger: "blur" },
    {
      pattern: /\w[-\w.+]*@([A-Za-z0-9][-A-Za-z0-9]+\.)+[A-Za-z]{2,14}/,
      message: "请输入正确的邮箱地址",
      trigger: "blur",
    },
  ],
};

/**
 * 打开弹窗
 * @param type 弹窗类型 ACCOUNT: 账号资料 PASSWORD: 修改密码 MOBILE: 绑定手机 EMAIL: 绑定邮箱
 */
const handleOpenDialog = (type: DialogType) => {
  dialog.type = type;
  dialog.visible = true;
  switch (type) {
    case DialogType.ACCOUNT:
      dialog.title = "账号资料";
      // 初始化表单数据
      userProfileForm.id = userProfile.value.id;
      userProfileForm.nickname = userProfile.value.nickname;
      userProfileForm.gender = userProfile.value.gender;
      break;
    case DialogType.PASSWORD:
      dialog.title = "修改密码";
      break;
    case DialogType.MOBILE:
      dialog.title = "绑定手机";
      break;
    case DialogType.EMAIL:
      dialog.title = "绑定邮箱";
      break;
  }
};

/**
 * 提交表单
 */
const handleSubmit = async () => {
  if (dialog.type === DialogType.ACCOUNT) {
    try {
    await UserAPI.updateProfile({ ...userProfileForm });
      ElMessage.success("账号资料修改成功");
      dialog.visible = false;
      loadUserProfile();
    } catch (err: any) {
      ElMessage.error(err?.message || "更新失败");
    }
  } else if (dialog.type === DialogType.PASSWORD) {
    if (passwordChangeForm.newPassword !== passwordChangeForm.confirmPassword) {
      ElMessage.error("两次输入的密码不一致");
      return;
    }
    try {
      await UserAPI.changePassword(passwordChangeForm);
      ElMessage.success("密码修改成功");
      dialog.visible = false;
    } catch (err: any) {
      ElMessage.error(err?.message || "修改密码失败");
    }
  } else if (dialog.type === DialogType.MOBILE) {
    try {
      await UserAPI.updateProfile({ mobile: mobileUpdateForm.mobile });
      ElMessage.success("手机号修改成功");
      dialog.visible = false;
      loadUserProfile();
    } catch (err: any) {
      ElMessage.error(err?.message || "修改失败");
    }
  } else if (dialog.type === DialogType.EMAIL) {
    try {
      await UserAPI.updateProfile({ email: emailUpdateForm.email });
      ElMessage.success("邮箱修改成功");
      dialog.visible = false;
      loadUserProfile();
    } catch (err: any) {
      ElMessage.error(err?.message || "修改失败");
    }
  }
};

/**
 * 取消
 */
const handleCancel = () => {
  dialog.visible = false;
  if (dialog.type === DialogType.ACCOUNT) {
    userProfileFormRef.value?.resetFields();
  } else if (dialog.type === DialogType.PASSWORD) {
    passwordChangeFormRef.value?.resetFields();
  } else if (dialog.type === DialogType.MOBILE) {
    mobileBindingFormRef.value?.resetFields();
  } else if (dialog.type === DialogType.EMAIL) {
    emailBindingFormRef.value?.resetFields();
  }
};

const fileInput = ref<HTMLInputElement | null>(null);
const uploading = ref(false);

// 裁剪弹窗状态
const cropperVisible = ref(false);
const cropperSrcUrl = ref("");
let cropperObjectUrl = ""; // createObjectURL 引用，需主动释放

// 预设头像选择
const presetDialogVisible = ref(false);
const allPresets = getAllPresets();
const selectingPreset = ref(false);

const triggerFileUpload = () => {
  if (uploading.value) return;
  fileInput.value?.click();
};

/**
 * 选择文件后打开裁剪弹窗（不直接上传原图）。
 * 前端白名单校验：仅允许 JPG / PNG / WEBP，最大 5MB。
 *
 * @param {Event} e - input[type=file] change 事件。
 */
const handleFileChange = (e: Event) => {
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

  // 创建 Object URL 传入裁剪弹窗（弹窗关闭后统一释放）
  if (cropperObjectUrl) URL.revokeObjectURL(cropperObjectUrl);
  cropperObjectUrl = URL.createObjectURL(file);
  cropperSrcUrl.value = cropperObjectUrl;
  cropperVisible.value = true;
  input.value = "";
};

/**
 * 裁剪确认回调：将裁剪后 Blob 上传至服务端。
 * 服务端 upload_avatar 已原子化写 DB，此处无需再调 updateProfile。
 *
 * @param {{ blob: Blob; dataUrl: string }} payload - 裁剪结果。
 */
const handleCropConfirm = async (payload: { blob: Blob; dataUrl: string }) => {
  let loadingSvc: { close(): void } | null = null;
  try {
    uploading.value = true;
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
    uploading.value = false;
    loadingSvc?.close();
    if (cropperObjectUrl) {
      URL.revokeObjectURL(cropperObjectUrl);
      cropperObjectUrl = "";
    }
  }
};

/** 裁剪取消：释放 Object URL。 */
const handleCropCancel = () => {
  if (cropperObjectUrl) {
    URL.revokeObjectURL(cropperObjectUrl);
    cropperObjectUrl = "";
  }
};

/**
 * 选择预设头像：直接调 updateProfile，更新 DB 和本地 store。
 *
 * @param {string} presetId - 预设标识符，如 'preset:03'。
 */
const handleSelectPreset = async (presetId: string) => {
  if (selectingPreset.value) return;
  selectingPreset.value = true;
  try {
    await UserAPI.updateProfile({ avatar: presetId });
    userProfile.value.avatar = presetId;
    userStore.userInfo.avatar = presetId;
    presetDialogVisible.value = false;
    ElMessage.success("头像已更新");
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : "更新失败");
  } finally {
    selectingPreset.value = false;
  }
};

/** 加载用户信息 */
const preloadFromStore = () => {
  // 先用已登录的简要信息填充，提升感知速度
  const basic = userStore.userInfo || ({} as any);
  if (basic && (basic.username || basic.nickname)) {
    userProfile.value.username = basic.username;
    userProfile.value.nickname = basic.nickname;
    userProfile.value.avatar = basic.avatar;
  }
};

const loadUserProfile = async () => {
  loadError.value = null;
  loading.value = true;
  try {
    const data = await Promise.race([
      UserAPI.getProfile(),
      new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 8000)),
    ]);
    userProfile.value = data as any;
  } catch (err: any) {
    if (err?.message === "timeout") {
      loadError.value = "获取资料超时，请刷新重试";
    } else {
      loadError.value = err?.message || "加载失败";
    }
  } finally {
    loading.value = false;
  }
};

onMounted(async () => {
  // 预填用户基本信息，随后拉取完整资料
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
        bottom: 0;
        left: 0;
        right: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 38px;
        background: rgba(0, 0, 0, 0.58);
        opacity: 0;
        transition: opacity 0.22s ease;

        .overlay-icon {
          flex: 1;
          display: flex;
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
      color: #409eff;
    }

    &.female {
      color: #f56c6c;
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
      cursor: wait;
      pointer-events: none;
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
      color: #fff;
      background: var(--el-color-primary);
      border-radius: 50%;
    }
  }
}

// 响应式适配
@media (max-width: 768px) {
  .profile-container {
    padding: 10px;
  }

  .el-col {
    width: 100%;
  }
}
</style>
