<template>
  <el-drawer
    v-model="visible"
    :title="title"
    append-to-body
    :size="drawerSize"
    @close="handleClose"
  >
    <!-- 用户表单 -->
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="80px">
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="formData.username"
          :readonly="!!formData.id"
          placeholder="请输入用户名"
        />
      </el-form-item>

      <el-form-item v-if="!formData.id" label="密码" prop="password">
        <el-input
          v-model="formData.password"
          type="password"
          show-password
          placeholder="至少6位密码"
        />
      </el-form-item>

      <el-form-item label="用户昵称" prop="nickname">
        <el-input v-model="formData.nickname" placeholder="请输入用户昵称" />
      </el-form-item>

      <el-form-item label="所属部门" prop="deptId">
        <el-tree-select
          v-model="formData.deptId"
          placeholder="请选择所属部门"
          :data="deptOptions"
          filterable
          check-strictly
          :render-after-expand="false"
        />
      </el-form-item>

      <el-form-item label="性别" prop="gender">
        <Dict v-model="formData.gender" code="gender" type="radio" />
      </el-form-item>

      <el-form-item label="角色" prop="roleIds">
        <el-select v-model="formData.roleIds" multiple placeholder="请选择">
          <el-option
            v-for="item in roleOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="手机号码" prop="mobile">
        <el-input v-model="formData.mobile" placeholder="请输入手机号码" maxlength="11" />
      </el-form-item>

      <el-form-item label="邮箱" prop="email">
        <el-input v-model="formData.email" placeholder="请输入邮箱" maxlength="50" />
      </el-form-item>

      <el-form-item label="账号状态" prop="status">
        <el-switch
          v-model="formData.status"
          inline-prompt
          active-text="正常"
          inactive-text="禁用"
          :active-value="1"
          :inactive-value="0"
        />
      </el-form-item>

      <el-form-item v-if="!formData.id" prop="createCloud">
        <template #label>
          <span style="font-size: 12px; white-space: nowrap">创建cloud账号</span>
        </template>
        <el-radio-group v-model="formData.createCloud">
          <el-radio :label="true">是</el-radio>
          <el-radio :label="false">否</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" :loading="loading" @click="handleSubmit">确 定</el-button>
        <el-button @click="handleClose">取 消</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { useAppStore } from "@/store/modules/app-store";
import { DeviceEnum } from "@/enums/settings/device-enum";
import { UserAPI, DeptAPI, RoleAPI } from "@/backend";

const appStore = useAppStore();
const emit = defineEmits(["success"]);

const visible = ref(false);
const title = ref("新增用户");
const loading = ref(false);
const formRef = ref();

const drawerSize = computed(() => (appStore.device === DeviceEnum.DESKTOP ? "600px" : "90%"));

const formData = reactive<any>({
  status: 1,
  createCloud: false,
});

const rules = reactive({
  username: [{ required: true, message: "用户名不能为空", trigger: "blur" }],
  password: [
    { required: true, message: "密码不能为空", trigger: "blur" },
    { min: 6, message: "密码至少6位", trigger: "blur" },
  ],
  nickname: [{ required: true, message: "用户昵称不能为空", trigger: "blur" }],
  deptId: [{ required: true, message: "所属部门不能为空", trigger: "blur" }],
  roleIds: [{ required: true, message: "用户角色不能为空", trigger: "blur" }],
  email: [
    { required: true, message: "邮箱不能为空", trigger: "blur" },
    {
      pattern: /\w[-\w.+]*@([A-Za-z0-9][-A-Za-z0-9]+\.)+[A-Za-z]{2,14}/,
      message: "请输入正确的邮箱地址",
      trigger: "blur",
    },
  ],
  mobile: [
    {
      pattern: /^1[3|4|5|6|7|8|9][0-9]\d{8}$/,
      message: "请输入正确的手机号码",
      trigger: "blur",
    },
  ],
});

const deptOptions = ref<OptionType[]>([]);
const roleOptions = ref<OptionType[]>([]);

/**
 * 打开弹窗
 * @param id 用户ID
 */
async function open(id?: string) {
  visible.value = true;
  // 加载角色下拉数据源
  roleOptions.value = await RoleAPI.getOptions();
  // 加载部门下拉数据源
  deptOptions.value = await DeptAPI.getOptions();

  if (id) {
    title.value = "修改用户";
    UserAPI.getFormData(id).then((data) => {
      Object.assign(formData, { ...data });
    });
  } else {
    title.value = "新增用户";
    formData.id = undefined;
    formData.username = undefined;
    formData.nickname = undefined;
    formData.deptId = undefined;
    formData.mobile = undefined;
    formData.email = undefined;
    formData.roleIds = undefined;

    formData.createCloud = false;
    formData.password = undefined;
    formData.status = 1;
  }
}

function handleClose() {
  visible.value = false;
  formRef.value?.resetFields();
  formRef.value?.clearValidate();
}

// 提交用户表单（防抖）
const handleSubmit = useDebounceFn(() => {
  formRef.value.validate((valid: boolean) => {
    if (valid) {
      const userId = formData.id;
      loading.value = true;
      if (userId) {
        UserAPI.update(userId, formData)
          .then((resp: any) => {
            const data = resp?.data || resp || {};
            // 显示常规成功提示
            ElMessage.success("修改用户成功");
            // 若后端返回 Seafile 同步结果，展示给用户
            if (data.seafileSync) {
              const s = data.seafileSync;
              if (s.success) {
                ElMessage.success("云端账户同步成功");
              } else {
                ElMessageBox.alert(`云端账户同步失败：${s.msg || "未知错误"}`, "云端同步结果", {
                  type: "warning",
                  confirmButtonText: "确定",
                });
              }
            }
            emit("success");
            handleClose();
          })
          .finally(() => (loading.value = false));
      } else {
        const payload = { ...formData };
        if (!payload.password || payload.password.length < 6) {
          ElMessage.warning("请输入至少6位密码");
          loading.value = false;
          return;
        }
        UserAPI.create(payload)
          .then(async (res: any) => {
            ElMessage.success("新增用户成功");
            // 如果勾选了同时创建 cloud 账号，调用后端代理创建
            try {
              if (payload.createCloud) {
                const userId = res?.id || res?.data?.id;
                if (userId) {
                  const resp = await UserAPI.createCloudUsers([userId], {
                    [String(userId)]: payload.password,
                  });
                  const d = resp?.data || resp || {};
                  const fail = d.failCount || 0;
                  if (fail === 0) {
                    ElMessage.success("创建成功！");
                  } else {
                    ElMessage.error("创建失败，联系管理员！");
                  }
                } else {
                  ElMessage.error("创建 cloud 账号失败：未获取到新用户 ID");
                }
              }
            } catch {
              ElMessage.error("创建 cloud 账号时发生错误，请联系管理员");
            }
            emit("success");
            handleClose();
          })
          .finally(() => (loading.value = false));
      }
    }
  });
}, 1000);

defineExpose({ open });
</script>
