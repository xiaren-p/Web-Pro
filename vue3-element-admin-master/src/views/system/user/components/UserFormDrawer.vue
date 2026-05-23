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

      <el-form-item label="岗位" prop="positionId">
        <!-- admin 账号的岗位为内置绑定，不可修改 -->
        <template v-if="formData.username === 'admin'">
          <el-input :value="formData.positionName || '系统管理员'" disabled style="width: 100%" />
          <div style="font-size: 12px; color: #999; margin-top: 4px">内置管理员账号岗位不可修改</div>
        </template>
        <el-select v-else v-model="formData.positionId" placeholder="请选择岗位" clearable>
          <el-option
            v-for="item in positionOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="管理级别" prop="adminLevel">
        <el-select v-model="formData.adminLevel" placeholder="请选择管理级别">
          <el-option :value="1" label="公司管理员" />
          <el-option :value="2" label="部门管理员" />
          <el-option :value="3" label="普通成员" />
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
import { UserAPI } from "@/api/user";
import { DeptAPI } from "@/api/dept";
import { PositionAPI } from "@/api/position";

const appStore = useAppStore();
const emit = defineEmits(["success"]);

const visible = ref(false);
const title = ref("新增用户");
const loading = ref(false);
const formRef = ref();

const drawerSize = computed(() => (appStore.device === DeviceEnum.DESKTOP ? "600px" : "90%"));

const formData = reactive<any>({
  status: 1,
  adminLevel: 3,
});

const rules = reactive({
  username: [{ required: true, message: "用户名不能为空", trigger: "blur" }],
  password: [
    { required: true, message: "密码不能为空", trigger: "blur" },
    { min: 6, message: "密码至少6位", trigger: "blur" },
  ],
  nickname: [{ required: true, message: "用户昵称不能为空", trigger: "blur" }],
  deptId: [{ required: true, message: "所属部门不能为空", trigger: "blur" }],
  adminLevel: [{ required: true, message: "请选择管理级别", trigger: "blur" }],
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
const positionOptions = ref<OptionType[]>([]);

/**
 * 打开弹窗
 * @param id 用户ID
 */
async function open(id?: string) {
  visible.value = true;
  // 加载岗位下拉数据源
  positionOptions.value = await PositionAPI.getOptions();
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
    formData.positionId = undefined;
    formData.adminLevel = 3;
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
          .then(() => {
            ElMessage.success("修改用户成功");
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
          .then(() => {
            ElMessage.success("新增用户成功");
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
