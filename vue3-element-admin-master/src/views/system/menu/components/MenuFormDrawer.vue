<template>
  <el-drawer v-model="visible" :title="title" :size="drawerSize" @close="handleClose">
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px">
      <el-form-item label="父级菜单" prop="parentId">
        <el-tree-select
          v-model="formData.parentId"
          placeholder="选择上级菜单"
          :data="menuOptions"
          filterable
          check-strictly
          :render-after-expand="false"
        />
      </el-form-item>

      <el-form-item label="菜单名称" prop="name">
        <el-input v-model="formData.name" placeholder="请输入菜单名称" />
      </el-form-item>

      <el-form-item label="菜单类型" prop="type">
        <el-radio-group v-model="formData.type" @change="handleMenuTypeChange">
          <el-radio :value="MenuTypeEnum.CATALOG">目录</el-radio>
          <el-radio :value="MenuTypeEnum.MENU">菜单</el-radio>
          <el-radio :value="MenuTypeEnum.BUTTON">按钮</el-radio>
          <el-radio :value="MenuTypeEnum.EXTLINK">外链</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item v-if="formData.type == MenuTypeEnum.EXTLINK" label="外链地址" prop="path">
        <el-input v-model="formData.path" placeholder="请输入外链完整路径" />
      </el-form-item>

      <el-form-item v-if="formData.type == MenuTypeEnum.MENU" prop="routeName">
        <template #label>
          <div class="flex-y-center">
            路由名称
            <el-tooltip placement="bottom" effect="light">
              <template #content>
                如果需要开启缓存，需保证页面 defineOptions 中的 name 与此处一致，建议使用驼峰。
              </template>
              <el-icon class="ml-1 cursor-pointer">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </div>
        </template>
        <el-input v-model="formData.routeName" placeholder="User" />
      </el-form-item>

      <el-form-item
        v-if="formData.type == MenuTypeEnum.CATALOG || formData.type == MenuTypeEnum.MENU"
        prop="path"
      >
        <template #label>
          <div class="flex-y-center">
            路由路径
            <el-tooltip placement="bottom" effect="light">
              <template #content>
                定义应用中不同页面对应的 URL 路径，目录需以 / 开头，菜单项不用。例如：系统管理目录
                /system，系统管理下的用户管理菜单 user。
              </template>
              <el-icon class="ml-1 cursor-pointer">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </div>
        </template>
        <el-input
          v-if="formData.type == MenuTypeEnum.CATALOG"
          v-model="formData.path"
          placeholder="/system"
        />
        <el-input v-else v-model="formData.path" placeholder="user" />
      </el-form-item>

      <el-form-item v-if="formData.type == MenuTypeEnum.MENU" prop="component">
        <template #label>
          <div class="flex-y-center">
            组件路径
            <el-tooltip placement="bottom" effect="light">
              <template #content>
                组件页面完整路径，相对于 src/views/，如 system/user/index，缺省后缀 .vue
              </template>
              <el-icon class="ml-1 cursor-pointer">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </div>
        </template>

        <el-input v-model="formData.component" placeholder="system/user/index" style="width: 95%" />
      </el-form-item>
      <el-form-item v-if="formData.type !== MenuTypeEnum.BUTTON" prop="visible" label="显示状态">
        <el-radio-group v-model="formData.visible">
          <el-radio :value="1">显示</el-radio>
          <el-radio :value="0">隐藏</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="排序" prop="sort">
        <el-input-number
          v-model="formData.sort"
          style="width: 100px"
          controls-position="right"
          :min="0"
        />
      </el-form-item>

      <!-- 权限标识 -->
      <el-form-item v-if="formData.type == MenuTypeEnum.BUTTON" label="权限标识" prop="perms">
        <el-input v-model="formData.perms" placeholder="sys:user:add" />
      </el-form-item>

      <el-form-item v-if="formData.type !== MenuTypeEnum.BUTTON" label="图标" prop="icon">
        <!-- 图标选择器 -->
        <icon-select v-model="formData.icon" />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" @click="handleSubmit">确 定</el-button>
        <el-button @click="handleClose">取 消</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { useAppStore } from "@/store/modules/app-store";
import { DeviceEnum } from "@/enums/settings/device-enum";
import { MenuAPI, type MenuForm } from "@/api/menu";
import { MenuTypeEnum } from "@/enums/system/menu-enum";

const emit = defineEmits(["success"]);
const appStore = useAppStore();

const visible = ref(false);
const title = ref("");
const formRef = ref();

const drawerSize = computed(() => (appStore.device === DeviceEnum.DESKTOP ? "600px" : "90%"));

// 顶级菜单下拉选项
const menuOptions = ref<OptionType[]>([]);

// 初始菜单表单数据
const initialMenuFormData = ref<MenuForm>({
  id: undefined,
  parentId: "0",
  visible: 1,
  sort: 1,
  type: MenuTypeEnum.MENU, // 默认菜单
  routeName: "",
  path: "",
  component: "",
  perms: "",
});

// 菜单表单数据
const formData = ref({ ...initialMenuFormData.value });

// 表单验证规则
const rules = reactive({
  parentId: [{ required: true, message: "请选择父级菜单", trigger: "blur" }],
  name: [{ required: true, message: "请输入菜单名称", trigger: "blur" }],
  type: [{ required: true, message: "请选择菜单类型", trigger: "blur" }],
  routeName: [{ required: true, message: "请输入路由名称", trigger: "blur" }],
  path: [{ required: true, message: "请输入路由路径", trigger: "blur" }],
  component: [{ required: true, message: "请输入组件路径", trigger: "blur" }],
  visible: [{ required: true, message: "请选择显示状态", trigger: "change" }],
});

/**
 * 打开表单弹窗
 *
 * @param parentId 父菜单ID
 * @param menuId 菜单ID
 */
function open(parentId?: string, menuId?: string) {
  MenuAPI.getOptions(true)
    .then((data) => {
      menuOptions.value = [{ value: "0", label: "顶级菜单", children: data }];
    })
    .then(() => {
      visible.value = true;
      if (menuId) {
        title.value = "编辑菜单";
        MenuAPI.getFormData(menuId).then((data) => {
          initialMenuFormData.value = { ...data };
          formData.value = data;
        });
      } else {
        title.value = "新增菜单";
        formData.value = { ...initialMenuFormData.value };
        formData.value.parentId = parentId?.toString() || "0";
      }
    });
}

// 菜单类型切换
function handleMenuTypeChange() {
  // 如果菜单类型改变
  if (formData.value.type !== initialMenuFormData.value.type) {
    if (formData.value.type === MenuTypeEnum.MENU) {
      // 目录切换到菜单时，清空组件路径
      if (initialMenuFormData.value.type === MenuTypeEnum.CATALOG) {
        formData.value.component = "";
      } else {
        // 其他情况，保留原有的组件路径
        formData.value.path = initialMenuFormData.value.path;
        formData.value.component = initialMenuFormData.value.component;
      }
    }
    // 非按钮类型时，清空权限标识，避免误保存
    if (formData.value.type !== MenuTypeEnum.BUTTON) {
      formData.value.perms = "";
    }
  }
}

/**
 * 提交表单
 */
function handleSubmit() {
  formRef.value.validate((isValid: boolean) => {
    if (isValid) {
      const menuId = formData.value.id;
      if (menuId) {
        //修改时父级菜单不能为当前菜单
        if (formData.value.parentId == menuId) {
          ElMessage.error("父级菜单不能为当前菜单");
          return;
        }
        MenuAPI.update(menuId, formData.value).then(() => {
          ElMessage.success("修改成功");
          emit("success");
          handleClose();
        });
      } else {
        MenuAPI.create(formData.value).then(() => {
          ElMessage.success("新增成功");
          emit("success");
          handleClose();
        });
      }
    }
  });
}

// 关闭弹窗
function handleClose() {
  visible.value = false;
  formRef.value.resetFields();
  formRef.value.clearValidate();
}

defineExpose({ open });
</script>
