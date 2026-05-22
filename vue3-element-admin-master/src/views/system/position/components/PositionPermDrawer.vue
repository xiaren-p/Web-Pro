<template>
  <el-drawer
    v-model="visible"
    :title="'【' + checkedPosition.name + '】权限分配'"
    :size="drawerSize"
  >
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
          @change="handleParentChildLinkedChange"
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
        <el-button type="primary" :loading="loading" @click="handleAssignPermSubmit">
          确 定
        </el-button>
        <el-button @click="visible = false">取 消</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
/**
 * 岗位菜单权限分配抽屉：展示可选菜单树，回显当前岗位已绑定的菜单并支持修改。
 * 所属板块：system。
 */
import { useAppStore } from "@/store/modules/app-store";
import { DeviceEnum } from "@/enums/settings/device-enum";
import { PositionAPI, type PositionPageVO } from "@/api/position";
import { MenuAPI } from "@/api/menu";

const emit = defineEmits(["success"]);

const appStore = useAppStore();

const visible = ref(false);
const loading = ref(false);
const permTreeRef = ref();

const drawerSize = computed(() => (appStore.device === DeviceEnum.DESKTOP ? "600px" : "90%"));

interface CheckedPosition {
  id?: string | number;
  name?: string;
}
const checkedPosition = ref<CheckedPosition>({});

const permKeywords = ref("");
const isExpanded = ref(true);
const parentChildLinked = ref(true);
const menuPermOptions = ref<OptionType[]>([]);

/**
 * 打开权限分配抽屉。
 *
 * @param row 岗位行数据
 */
async function open(row: PositionPageVO) {
  const positionId = row.id;
  if (positionId) {
    visible.value = true;
    loading.value = true;

    checkedPosition.value.id = positionId;
    checkedPosition.value.name = row.name;

    // 加载全量菜单树
    menuPermOptions.value = await MenuAPI.getOptions();

    // 回显该岗位已绑定的菜单
    PositionAPI.getMenuIds(positionId)
      .then((data) => {
        data.forEach((menuId) => permTreeRef.value?.setChecked(menuId, true, false));
      })
      .finally(() => {
        loading.value = false;
      });
  }
}

/** 提交岗位权限保存 */
function handleAssignPermSubmit() {
  const positionId = checkedPosition.value.id;
  if (positionId) {
    const checkedMenuIds: number[] = permTreeRef.value
      ?.getCheckedNodes(false, true)
      .map((node: any) => node.value);

    loading.value = true;
    PositionAPI.saveMenus(String(positionId), checkedMenuIds)
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

/** 展开 / 收缩菜单权限树 */
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

/** 父子联动切换：重置所有选中以避免半选残留 */
function handleParentChildLinkedChange() {
  permTreeRef.value?.setCheckedKeys([]);
}

/** 菜单权限树过滤 */
watch(permKeywords, (val) => {
  permTreeRef.value?.filter(val);
});

function handlePermFilter(value: string, data: any) {
  if (!value) return true;
  return data.label.includes(value);
}

defineExpose({ open });
</script>
