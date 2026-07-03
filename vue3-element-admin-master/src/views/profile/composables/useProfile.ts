/**
 * 个人资料页业务逻辑 composable。
 *
 * @module useProfile
 * @description 封装资料加载、表单提交（账号/密码/手机/邮箱）、表单校验规则。
 *              头像上传和预设选择因其与模板强耦合，保留在视图中。
 */

import { ref, reactive } from "vue";
import { ElMessage } from "element-plus";
import { UserAPI } from "@/api/user";
import { useUserStoreHook } from "@/store";

/** 用户资料 VO。 */
export interface UserProfileVO {
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

/** 修改密码表单。 */
export interface PasswordChangeForm {
  oldPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
}

/** 手机号修改表单。 */
export interface MobileUpdateForm {
  mobile?: string;
}

/** 邮箱修改表单。 */
export interface EmailUpdateForm {
  email?: string;
}

/** 账号资料表单。 */
export interface UserProfileForm {
  id?: string;
  nickname?: string;
  gender?: number;
}

/** 弹窗类型枚举。 */
export const enum DialogType {
  ACCOUNT = "account",
  PASSWORD = "password",
  MOBILE = "mobile",
  EMAIL = "email",
}

export function useProfile() {
  const userStore = useUserStoreHook();

  /** 用户资料。 */
  const userProfile = ref<UserProfileVO>({});

  /** 页面加载状态。 */
  const isLoading = ref(true);

  /** 加载错误信息。 */
  const loadError = ref<string | null>(null);

  /** 弹窗可见性。 */
  const dialogVisible = ref(false);

  /** 弹窗标题。 */
  const dialogTitle = ref("");

  /** 当前弹窗类型。 */
  const dialogType = ref<DialogType>(DialogType.ACCOUNT);

  /** 账号资料表单。 */
  const userProfileForm = reactive<UserProfileForm>({});

  /** 修改密码表单。 */
  const passwordChangeForm = reactive<PasswordChangeForm>({});

  /** 手机号修改表单。 */
  const mobileUpdateForm = reactive<MobileUpdateForm>({});

  /** 邮箱修改表单。 */
  const emailUpdateForm = reactive<EmailUpdateForm>({});

  /** 修改密码校验规则。 */
  const passwordChangeRules = {
    oldPassword: [{ required: true, message: "请输入原密码", trigger: "blur" }],
    newPassword: [{ required: true, message: "请输入新密码", trigger: "blur" }],
    confirmPassword: [{ required: true, message: "请再次输入新密码", trigger: "blur" }],
  };

  /** 手机号校验规则。 */
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

  /** 邮箱校验规则。 */
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
   * 从 Store 预填基本信息，提升首屏感知速度。
   */
  function preloadFromStore() {
    const basic = userStore.userInfo || ({} as unknown);
    if (basic && ((basic as UserProfileVO).username || (basic as UserProfileVO).nickname)) {
      userProfile.value.username = (basic as UserProfileVO).username;
      userProfile.value.nickname = (basic as UserProfileVO).nickname;
      userProfile.value.avatar = (basic as UserProfileVO).avatar;
    }
  }

  /**
   * 从服务端加载完整用户资料（8s 超时保护）。
   */
  async function loadUserProfile() {
    loadError.value = null;
    isLoading.value = true;
    try {
      const data = await Promise.race([
        UserAPI.getProfile(),
        new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 8000)),
      ]);
      userProfile.value = data as unknown as UserProfileVO;
    } catch (err: unknown) {
      if (err instanceof Error && err.message === "timeout") {
        loadError.value = "获取资料超时，请刷新重试";
      } else {
        loadError.value = err instanceof Error ? err.message : "加载失败";
      }
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * 打开弹窗并根据类型初始化表单数据。
   *
   * @param type - 弹窗类型。
   */
  function handleOpenDialog(type: DialogType) {
    dialogType.value = type;
    dialogVisible.value = true;
    switch (type) {
      case DialogType.ACCOUNT:
        dialogTitle.value = "账号资料";
        userProfileForm.id = userProfile.value.id;
        userProfileForm.nickname = userProfile.value.nickname;
        userProfileForm.gender = userProfile.value.gender;
        break;
      case DialogType.PASSWORD:
        dialogTitle.value = "修改密码";
        break;
      case DialogType.MOBILE:
        dialogTitle.value = "绑定手机";
        break;
      case DialogType.EMAIL:
        dialogTitle.value = "绑定邮箱";
        break;
    }
  }

  /**
   * 提交弹窗表单（根据当前类型分发到不同 API）。
   */
  async function handleSubmit() {
    if (dialogType.value === DialogType.ACCOUNT) {
      try {
        await UserAPI.updateProfile({ ...userProfileForm });
        ElMessage.success("账号资料修改成功");
        dialogVisible.value = false;
        await loadUserProfile();
      } catch (err: unknown) {
        ElMessage.error(err instanceof Error ? err.message : "更新失败");
      }
    } else if (dialogType.value === DialogType.PASSWORD) {
      if (passwordChangeForm.newPassword !== passwordChangeForm.confirmPassword) {
        ElMessage.error("两次输入的密码不一致");
        return;
      }
      try {
        await UserAPI.changePassword(passwordChangeForm);
        ElMessage.success("密码修改成功");
        dialogVisible.value = false;
      } catch (err: unknown) {
        ElMessage.error(err instanceof Error ? err.message : "修改密码失败");
      }
    } else if (dialogType.value === DialogType.MOBILE) {
      try {
        await UserAPI.updateProfile({ mobile: mobileUpdateForm.mobile });
        ElMessage.success("手机号修改成功");
        dialogVisible.value = false;
        await loadUserProfile();
      } catch (err: unknown) {
        ElMessage.error(err instanceof Error ? err.message : "修改失败");
      }
    } else if (dialogType.value === DialogType.EMAIL) {
      try {
        await UserAPI.updateProfile({ email: emailUpdateForm.email });
        ElMessage.success("邮箱修改成功");
        dialogVisible.value = false;
        await loadUserProfile();
      } catch (err: unknown) {
        ElMessage.error(err instanceof Error ? err.message : "修改失败");
      }
    }
  }

  return {
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
  };
}
