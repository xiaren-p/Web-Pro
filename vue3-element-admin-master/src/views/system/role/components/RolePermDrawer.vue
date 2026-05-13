<template>
  <el-drawer v-model="visible" :title="'【' + checkedRole.name + '】权限分配'" :size="drawerSize">
    <div class="flex-x-between">
      <el-input v-model="permKeywords" clearable class="w-[150px]" placeholder="菜单权限名称">
        <template #prefix>
          <Search />
        </template>
      </el-input>

      <div class="flex-center ml-5">
        <el-button type="primary" size="small" plain @click="togglePermTree">
          <template #icon>
            <Switch />
          </template>
          {{ isExpanded ? "收缩" : "展开" }}
        </el-button>
        <el-checkbox
          v-model="parentChildLinked"
          class="ml-5"
          @change="handleparentChildLinkedChange"
        >
          父子联动
        </el-checkbox>

        <el-tooltip placement="bottom">
          <template #content>
            如果只需勾选菜单权限，不需要勾选子菜单或者按钮权限，请关闭父子联动
          </template>
          <el-icon class="ml-1 color-[--el-color-primary] inline-block cursor-pointer">
            <QuestionFilled />
          </el-icon>
        </el-tooltip>
      </div>
    </div>

    <el-tree
      ref="permTreeRef"
      node-key="value"
      show-checkbox
      :data="menuPermOptions"
      :filter-node-method="handlePermFilter"
      :default-expand-all="true"
      :check-strictly="!parentChildLinked"
      class="mt-5"
    >
      <template #default="{ data }">
        {{ data.label }}
      </template>
    </el-tree>
    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" @click="handleAssignPermSubmit">确 定</el-button>
        <el-button @click="visible = false">取 消</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { useAppStore } from "@/store/modules/app-store";
import { DeviceEnum } from "@/enums/settings/device-enum";
import { RoleAPI, type RolePageVO } from "@/api/role";
import { MenuAPI } from "@/api/menu";

const emit = defineEmits(["success"]);

const appStore = useAppStore();

const visible = ref(false);
const loading = ref(false);
const permTreeRef = ref();

const drawerSize = computed(() => (appStore.device === DeviceEnum.DESKTOP ? "600px" : "90%"));

// 选中的角色
interface CheckedRole {
  id?: string | number;
  name?: string;
}
const checkedRole = ref<CheckedRole>({});

const permKeywords = ref("");
const isExpanded = ref(true);
const parentChildLinked = ref(true);
const menuPermOptions = ref<OptionType[]>([]);

// 打开分配菜单权限弹窗
async function open(row: RolePageVO) {
  const roleId = row.id;
  if (roleId) {
    visible.value = true;
    loading.value = true;

    checkedRole.value.id = roleId;
    checkedRole.value.name = row.name;

    // 获取所有的菜单（树）
    menuPermOptions.value = await MenuAPI.getOptions();

    // 回显角色已拥有的菜单
    RoleAPI.getRoleMenuIds(roleId)
      .then((data) => {
        const checkedMenuIds = data;
        checkedMenuIds.forEach((menuId) => permTreeRef.value!.setChecked(menuId, true, false));
      })
      .finally(() => {
        loading.value = false;
      });
  }
}

// 分配菜单权限提交
function handleAssignPermSubmit() {
  const roleId = checkedRole.value.id;
  if (roleId) {
    const checkedMenuIds: number[] = permTreeRef
      .value!.getCheckedNodes(false, true)
      .map((node: any) => node.value);

    loading.value = true;
    // RoleAPI.updateRoleMenus 在类型定义中接受字符串类型的 roleId，
    // 因此这里将 roleId 显式转换为 string 以避免 TS 类型错误。
    RoleAPI.updateRoleMenus(String(roleId), checkedMenuIds)
      .then(() => {
        ElMessage.success("分配权限成功");
        visible.value = false;
        emit("success");
      })
      .finally(() => {
        loading.value = false;
      });
  }
}

// 展开/收缩 菜单权限树
function togglePermTree() {
  isExpanded.value = !isExpanded.value;
  if (permTreeRef.value) {
    Object.values(permTreeRef.value.store.nodesMap).forEach((node: any) => {
      if (isExpanded.value) {
        node.expand();
      } else {
        node.collapse();
      }
    });
  }
}

// 权限筛选
watch(permKeywords, (val) => {
  permTreeRef.value!.filter(val);
});

function handlePermFilter(
  value: string,
  data: {
    [key: string]: any;
  }
) {
  if (!value) return true;
  return data.label.includes(value);
}

// 父子菜单节点是否联动
function handleparentChildLinkedChange(val: any) {
  parentChildLinked.value = val;
}

defineExpose({
  open,
});
</script>
