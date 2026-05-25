<template>
  <div class="developer-apps-page">
    <!-- 页头：标题 + 创建按钮 -->
    <div class="page-header">
      <div class="page-header__info">
        <h2 class="page-header__title">开发者应用</h2>
        <p class="page-header__desc">
          通过 Client Credentials 授权，从外部脚本或服务无缝调用
          <code>api/v2</code>
          工作流接口。应用凭据不可访问 api/v1 管理接口。
        </p>
      </div>
      <el-button type="primary" :icon="Plus" @click="handleOpenCreate">创建应用</el-button>
    </div>

    <!-- 应用列表 -->
    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="apps"
        empty-text="暂无应用，点击「创建应用」开始"
        style="width: 100%"
      >
        <el-table-column prop="name" label="应用名称" min-width="160" />

        <el-table-column label="Client ID" min-width="300">
          <template #default="{ row }">
            <div class="client-id-cell">
              <code class="mono-text">{{ row.client_id }}</code>
              <el-tooltip content="复制 Client ID" placement="top">
                <el-icon class="copy-icon" @click="handleCopy(row.client_id, 'Client ID')">
                  <CopyDocument />
                </el-icon>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleOpenRotate(row)">轮换密钥</el-button>
            <el-divider direction="vertical" />
            <el-popconfirm
              title="删除后将立即撤销所有关联 Token，是否确认？"
              width="260"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button link type="danger" :loading="deletingId === row.id">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ① 创建应用对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="创建应用"
      width="480px"
      :close-on-click-modal="false"
      @closed="resetCreateForm"
    >
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="80px">
        <el-form-item label="应用名称" prop="name">
          <el-input
            v-model="createForm.name"
            placeholder="例如：数据同步脚本、自动上传服务"
            maxlength="100"
            show-word-limit
            clearable
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreateConfirm">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- ② 轮换密钥确认对话框 -->
    <el-dialog v-model="rotateConfirmVisible" title="确认轮换密钥" width="440px">
      <el-alert type="warning" show-icon :closable="false" style="margin-bottom: 12px">
        <template #title>
          轮换后，当前应用所有有效的 Access Token 将立即失效，使用旧凭据的调用方需重新获取。
        </template>
      </el-alert>
      <p>
        即将轮换应用
        <strong>{{ rotatingApp?.name }}</strong>
        的 Client Secret，确认继续？
      </p>
      <template #footer>
        <el-button @click="rotateConfirmVisible = false">取消</el-button>
        <el-button type="warning" :loading="submitting" @click="handleRotateConfirm">
          确认轮换
        </el-button>
      </template>
    </el-dialog>

    <!-- ③ 一次性凭据展示对话框（创建 / 轮换共用） -->
    <el-dialog
      v-model="credDialogVisible"
      :title="currentCreds?.scene === 'created' ? '应用创建成功' : '密钥轮换成功'"
      width="580px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      @closed="clearCreds"
    >
      <el-alert type="warning" show-icon :closable="false" style="margin-bottom: 16px">
        <template #title>
          请立即保存以下凭据。
          <strong>Client Secret 仅此一次显示</strong>
          ，关闭后无法找回， 届时只能重新轮换密钥。
        </template>
      </el-alert>

      <div class="cred-block">
        <div class="cred-row">
          <span class="cred-label">应用名称</span>
          <span class="cred-value">{{ currentCreds?.name }}</span>
        </div>
        <div class="cred-row">
          <span class="cred-label">Client ID</span>
          <span class="cred-value mono-text">{{ currentCreds?.client_id }}</span>
          <el-button
            text
            size="small"
            type="primary"
            @click="handleCopy(currentCreds?.client_id ?? '', 'Client ID')"
          >
            复制
          </el-button>
        </div>
        <div class="cred-row">
          <span class="cred-label">Client Secret</span>
          <span class="cred-value mono-text secret-text">{{ currentCreds?.client_secret }}</span>
          <el-button
            text
            size="small"
            type="primary"
            @click="handleCopy(currentCreds?.client_secret ?? '', 'Client Secret')"
          >
            复制
          </el-button>
        </div>
      </div>

      <el-divider />

      <div class="usage-hint">
        <p class="usage-hint__title">调用示例（curl）</p>
        <pre class="code-block">{{ usageExample }}</pre>
      </div>

      <template #footer>
        <el-button type="primary" @click="credDialogVisible = false">我已保存，关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * 开发者应用管理页：展示当前用户注册的 Client Credentials 应用，支持创建、删除、轮换密钥。
 * 所属板块：developer。
 */
import type { FormInstance, FormRules } from "element-plus";
import type { DeveloperApp, OneTimeCredentials } from "@/types/developer/app";

import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { CopyDocument, Plus } from "@element-plus/icons-vue";

import { createApp, deleteApp, fetchApps, rotateAppSecret } from "@/api/developer/apps";

// ─── 列表状态 ──────────────────────────────────────────────────────────────
const loading = ref(false);
const apps = ref<DeveloperApp[]>([]);
const deletingId = ref<number | null>(null);

async function loadApps(): Promise<void> {
  if (loading.value) return;
  loading.value = true;
  try {
    const res = await fetchApps();
    apps.value = res.results;
  } catch {
    ElMessage.error("加载应用列表失败");
  } finally {
    loading.value = false;
  }
}

// ─── 创建应用 ──────────────────────────────────────────────────────────────
const createDialogVisible = ref(false);
const submitting = ref(false);
const createFormRef = ref<FormInstance>();
const createForm = reactive({ name: "" });

const createRules: FormRules = {
  name: [
    { required: true, message: "请输入应用名称", trigger: "blur" },
    { min: 1, max: 100, message: "名称长度 1 ～ 100 字符", trigger: "blur" },
  ],
};

function handleOpenCreate(): void {
  createDialogVisible.value = true;
}

function resetCreateForm(): void {
  createForm.name = "";
  createFormRef.value?.resetFields();
}

async function handleCreateConfirm(): Promise<void> {
  const valid = await createFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  submitting.value = true;
  try {
    const result = await createApp({ name: createForm.name });
    createDialogVisible.value = false;
    await loadApps();
    showCreds({
      name: result.name,
      client_id: result.client_id,
      client_secret: result.client_secret,
      scene: "created",
    });
  } catch {
    ElMessage.error("创建应用失败");
  } finally {
    submitting.value = false;
  }
}

// ─── 删除应用 ──────────────────────────────────────────────────────────────
async function handleDelete(row: DeveloperApp): Promise<void> {
  deletingId.value = row.id;
  try {
    await deleteApp(row.id);
    ElMessage.success(`应用「${row.name}」已删除`);
    await loadApps();
  } catch {
    ElMessage.error("删除失败，请重试");
  } finally {
    deletingId.value = null;
  }
}

// ─── 轮换密钥 ──────────────────────────────────────────────────────────────
const rotateConfirmVisible = ref(false);
const rotatingApp = ref<DeveloperApp | null>(null);

function handleOpenRotate(row: DeveloperApp): void {
  rotatingApp.value = row;
  rotateConfirmVisible.value = true;
}

async function handleRotateConfirm(): Promise<void> {
  if (!rotatingApp.value) return;

  submitting.value = true;
  try {
    const result = await rotateAppSecret(rotatingApp.value.id);
    rotateConfirmVisible.value = false;
    showCreds({
      name: rotatingApp.value.name,
      client_id: rotatingApp.value.client_id,
      client_secret: result.client_secret,
      scene: "rotated",
    });
  } catch {
    ElMessage.error("密钥轮换失败，请重试");
  } finally {
    submitting.value = false;
    rotatingApp.value = null;
  }
}

// ─── 凭据展示（一次性） ────────────────────────────────────────────────────
const credDialogVisible = ref(false);
const currentCreds = ref<OneTimeCredentials | null>(null);

function showCreds(creds: OneTimeCredentials): void {
  currentCreds.value = creds;
  credDialogVisible.value = true;
}

function clearCreds(): void {
  currentCreds.value = null;
}

const usageExample = computed(() => {
  const id = currentCreds.value?.client_id ?? "<CLIENT_ID>";
  const secret = currentCreds.value?.client_secret ?? "<CLIENT_SECRET>";
  return [
    "# 1. 获取 Access Token",
    `curl -X POST http://<SERVER>/o/token/ \\`,
    `  -d "grant_type=client_credentials&client_id=${id}&client_secret=${secret}&scope=api_v2"`,
    "",
    "# 2. 调用 api/v2 接口（以启动任务为例）",
    `curl -X POST http://<SERVER>/api/v2/workflow/ \\`,
    `  -H "Authorization: Bearer <ACCESS_TOKEN>" \\`,
    `  -H "Content-Type: application/json" \\`,
    `  -d '{"workflow_type":"listing_image_upload","params":{"listing_id":1}}'`,
  ].join("\n");
});

// ─── 工具函数 ──────────────────────────────────────────────────────────────
async function handleCopy(text: string, label: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success(`${label} 已复制`);
  } catch {
    ElMessage.warning("复制失败，请手动选中后复制");
  }
}

function formatDateTime(iso: string): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

onMounted(loadApps);
</script>

<style scoped lang="scss">
.developer-apps-page {
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;

  &__title {
    margin: 0 0 6px;
    font-size: 20px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  &__desc {
    margin: 0;
    font-size: 13px;
    color: var(--el-text-color-secondary);

    code {
      padding: 1px 5px;
      font-size: 12px;
      background: var(--el-fill-color-light);
      border-radius: 3px;
    }
  }
}

.client-id-cell {
  display: flex;
  gap: 6px;
  align-items: center;
}

.copy-icon {
  flex-shrink: 0;
  font-size: 15px;
  color: var(--el-color-primary);
  cursor: pointer;

  &:hover {
    color: var(--el-color-primary-light-3);
  }
}

.mono-text {
  font-family: "Courier New", Courier, monospace;
  font-size: 12px;
  word-break: break-all;
}

.cred-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
}

.cred-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.cred-label {
  flex-shrink: 0;
  width: 110px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.cred-value {
  flex: 1;
  font-size: 13px;
  color: var(--el-text-color-primary);
  word-break: break-all;
}

.secret-text {
  font-weight: 500;
  color: var(--el-color-danger);
}

.usage-hint {
  &__title {
    margin: 0 0 8px;
    font-size: 13px;
    font-weight: 600;
    color: var(--el-text-color-regular);
  }
}

.code-block {
  padding: 12px 14px;
  margin: 0;
  overflow-x: auto;
  font-family: "Courier New", Courier, monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #d4d4d4;
  white-space: pre;
  background: #1e1e1e;
  border-radius: 6px;
}
</style>
