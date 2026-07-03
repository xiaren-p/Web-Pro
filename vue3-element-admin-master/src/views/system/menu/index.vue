<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <div class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true">
        <el-form-item label="关键字" prop="keywords">
          <el-input
            v-model="queryParams.keywords"
            placeholder="菜单名称"
            clearable
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item class="search-buttons">
          <el-button type="primary" icon="search" @click="handleQuery">搜索</el-button>
          <el-button icon="refresh" @click="handleResetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
    <el-card shadow="hover" class="data-table">
      <div class="data-table__toolbar">
        <div class="data-table__toolbar--actions">
          <el-button
            v-hasPerm="['sys:menu:add']"
            type="success"
            icon="plus"
            @click="openDrawer('0')"
          >
            新增
          </el-button>
        </div>
      </div>
      <el-table
        ref="dataTableRef"
        v-loading="isLoading"
        row-key="id"
        :data="menuTableData"
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        class="data-table__content"
        @row-click="handleRowClick"
      >
        <el-table-column label="菜单名称" min-width="200">
          <template #default="scope">
            <template v-if="scope.row.icon && scope.row.icon.startsWith('el-icon')">
              <el-icon style="vertical-align: -0.15em">
                <component :is="scope.row.icon.replace('el-icon-', '')" />
              </el-icon>
            </template>
            <template v-else-if="scope.row.icon && scope.row.icon.startsWith('tabler:')">
              <div :class="`i-tabler:${scope.row.icon.replace('tabler:', '')}`" />
            </template>
            <template v-else-if="scope.row.icon">
              <div :class="`i-svg:${scope.row.icon}`" />
            </template>
            {{ scope.row.name }}
          </template>
        </el-table-column>
        <el-table-column label="类型" align="center" width="80">
          <template #default="scope">
            <el-tag v-if="scope.row.type === MenuTypeEnum.CATALOG" type="warning">目录</el-tag>
            <el-tag v-if="scope.row.type === MenuTypeEnum.MENU" type="success">菜单</el-tag>
            <el-tag v-if="scope.row.type === MenuTypeEnum.BUTTON" type="danger">按钮</el-tag>
            <el-tag v-if="scope.row.type === MenuTypeEnum.EXTLINK" type="info">外链</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="路由名称" align="left" width="150">
          <template #default="scope">
            <span v-if="scope.row.type === MenuTypeEnum.MENU">{{ scope.row.routeName }}</span>
          </template>
        </el-table-column>
        <el-table-column label="路由路径" align="left" width="150" prop="path" />
        <el-table-column label="组件路径" align="left" width="250" prop="component" />
        <el-table-column label="权限标识" align="center" width="200">
          <template #default="scope">
            <span v-if="scope.row.type === MenuTypeEnum.BUTTON">{{ scope.row.perms }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" align="center" width="80">
          <template #default="scope">
            <el-tag v-if="scope.row.visible === 1" type="success">显示</el-tag>
            <el-tag v-else type="info">隐藏</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="排序" align="center" width="80" prop="sort" />
        <el-table-column fixed="right" align="center" label="操作" width="220">
          <template #default="scope">
            <el-button
              v-if="scope.row.type == MenuTypeEnum.CATALOG || scope.row.type == MenuTypeEnum.MENU"
              v-hasPerm="['sys:menu:add']"
              type="primary"
              link
              size="small"
              icon="plus"
              @click.stop="openDrawer(scope.row.id)"
            >
              新增
            </el-button>
            <el-button
              v-hasPerm="['sys:menu:edit']"
              type="primary"
              link
              size="small"
              icon="edit"
              @click.stop="openDrawer(undefined, scope.row.id)"
            >
              编辑
            </el-button>
            <el-button
              v-hasPerm="['sys:menu:delete']"
              type="danger"
              link
              size="small"
              icon="delete"
              @click.stop="handleDelete(scope.row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <MenuFormDrawer ref="menuFormDrawerRef" @success="handleQuery" />
  </div>
</template>

<script setup lang="ts">
/**
 * 菜单管理列表页。
 *
 * @description 薄编排层：组合 useMenuList composable 与 MenuFormDrawer。
 *              菜单树查询、行选中、删除逻辑全部在 composable 中。
 */
import { useMenuList } from "./composables/useMenuList";
import { MenuTypeEnum } from "@/enums/system/menu-enum";
import MenuFormDrawer from "./components/MenuFormDrawer.vue";

defineOptions({ name: "SysMenu", inheritAttrs: false });

const queryFormRef = ref();
const menuFormDrawerRef = ref();
const { isLoading, queryParams, menuTableData, handleQuery, handleRowClick, handleDelete } =
  useMenuList();

/** 重置查询条件并重新查询。 */
function handleResetQuery() {
  queryFormRef.value?.resetFields();
  handleQuery();
}

/**
 * 打开菜单表单抽屉。
 *
 * @param parentId - 父菜单ID（新建子菜单时传入）。
 * @param menuId - 菜单ID（编辑时传入）。
 */
function openDrawer(parentId?: string, menuId?: string) {
  menuFormDrawerRef.value.open(parentId, menuId);
}

onMounted(() => {
  handleQuery();
});
</script>
