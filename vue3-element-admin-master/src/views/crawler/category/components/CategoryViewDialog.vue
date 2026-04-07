<template>
  <el-dialog v-model="visible" title="数据查看" width="480px" @close="handleClose">
    <!-- 数据未返回前转圈加载 -->
    <el-form v-loading="timesChecking" label-width="120px" element-loading-text="正在加载...">
      <el-form-item label="选择日期">
        <el-date-picker
          v-model="time"
          type="date"
          placeholder="选择日期"
          style="width: 100%"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          @change="onDateChanged"
        />
      </el-form-item>
      <el-form-item v-if="needCloudPassword" label="输入 cloud 密码">
        <el-input
          v-model="cloudPassword"
          placeholder="请输入 cloud 密码以刷新后端缓存"
          show-password
          style="width: 100%"
        />
        <div style="margin-top: 8px; text-align: right">
          <el-button size="small" type="primary" @click="refreshCloudPasswordAndRetry">
            刷新并重试
          </el-button>
        </div>
      </el-form-item>
      <el-form-item label="可选时间">
        <el-table :data="timesList" size="small" style="width: 100%">
          <el-table-column prop="index" label="序号" width="60" />
          <el-table-column prop="name" label="时间" />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button
                type="primary"
                link
                size="small"
                :disabled="!row.viewUrl"
                @click="viewTime(row.viewUrl)"
              >
                查看
              </el-button>
              <el-button
                type="primary"
                link
                size="small"
                :disabled="!row.name"
                @click="downloadTime(row.name)"
              >
                下载
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" @click="handleConfirm">确定</el-button>
        <el-button @click="handleClose">取消</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { CategoryAPI, UserAPI } from "@/backend";
import { useUserStoreHook } from "@/store";
import { ElMessage } from "element-plus";

const visible = ref(false);
const time = ref<string | null>(null);
const timesChecking = ref(false);
const needCloudPassword = ref(false);
const cloudPassword = ref("");

// Internal state
const currentCategory = ref<any>(null);
const pendingDownloadName = ref<string | null>(null);
const timesList = ref<any[]>([]);
const allTimes = ref<string[]>([]);
const allTimesDates = ref<string[]>([]);

function handleClose() {
  visible.value = false;
}

function handleConfirm() {
  const v = time.value || "";
  if (v) ElMessage.info(`已选择日期：${v}`);
  visible.value = false;
}

async function open(row: any) {
  visible.value = true;
  time.value = null;
  currentCategory.value = row || null;
  timesList.value = [];
  timesChecking.value = true;

  try {
    const profile: any = await UserAPI.getProfile();
    const cached = !!(
      profile &&
      (profile.seafileCached || (profile.data && profile.data.seafileCached))
    );
    if (cached) {
      needCloudPassword.value = false;
      if (row && row.id) {
        await loadTimes(String(row.id));
      }
    } else {
      needCloudPassword.value = true;
      cloudPassword.value = "";
      pendingDownloadName.value = null;
      ElMessage.info("未找到缓存的 Seafile token，请在弹窗中输入 cloud 密码并点击刷新以继续");
      timesChecking.value = false;
    }
  } catch (err) {
    console.warn(err);
    needCloudPassword.value = true;
    cloudPassword.value = "";
    pendingDownloadName.value = null;
    ElMessage.info("无法查询缓存状态，请输入 cloud 密码并点击刷新以继续");
    timesChecking.value = false;
  }
}

function isNeedCloud(status: number | undefined, data: any) {
  try {
    const needCloudFlag =
      data && ((data.data && data.data.needCloudPassword) || data.needCloudPassword);
    const msg = (data && (data.msg || data.error_msg || data.error || "")) + "";
    const match = /未找到缓存|needCloudPassword|need cloud password|need cloud/i.test(msg);
    return status === 401 || !!needCloudFlag || match;
  } catch (e) {
    console.warn(e);
    return false;
  }
}

async function loadTimes(id: string) {
  try {
    timesChecking.value = true;
    const res = await CategoryAPI.getTimes(id);
    allTimes.value = res && res.all ? res.all : [];

    const toTimestamp = (s: string) => {
      if (!s) return 0;
      if (/^\d{8}$/.test(s)) {
        const t = Date.parse(`${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`);
        return isNaN(t) ? Number(s) : t;
      }
      if (/^\d{6}$/.test(s)) {
        const t = Date.parse(`20${s.slice(0, 2)}-${s.slice(2, 4)}-${s.slice(4, 6)}`);
        return isNaN(t) ? Number(s) : t;
      }
      const tIso = Date.parse(s);
      if (!isNaN(tIso)) return tIso;
      const digits = Number((s || "").replace(/\D/g, ""));
      return isNaN(digits) ? 0 : digits;
    };

    if (Array.isArray(allTimes.value) && allTimes.value.length > 1) {
      allTimes.value = allTimes.value
        .slice()
        .sort((a, b) => toTimestamp(String(b)) - toTimestamp(String(a)));
    }

    allTimesDates.value = allTimes.value.map((n) => {
      if (/^\d{8}$/.test(n)) return `${n.slice(0, 4)}-${n.slice(4, 6)}-${n.slice(6, 8)}`;
      if (/^\d{6}$/.test(n)) return `20${n.slice(0, 2)}-${n.slice(2, 4)}-${n.slice(4, 6)}`;
      return n;
    });

    const display: any[] = [];
    const maxDisplay = 3;
    let nextIdx = 0;

    const checkOne = async (cand: string) => {
      try {
        const chk = await CategoryAPI.checkFile(id, cand);
        if (chk && chk.exists) {
          if (display.length < maxDisplay) {
            const srcIdx = allTimes.value.indexOf(cand);
            display.push({
              index: display.length + 1,
              name: cand,
              viewUrl: (chk as any).viewUrl || null,
              downloadUrl: (chk as any).downloadUrl || null,
              sourceIdx: srcIdx >= 0 ? srcIdx : Number.MAX_SAFE_INTEGER,
            });
          }
          return true;
        }
        return false;
      } catch (err: any) {
        const resp = err && (err.response || err);
        const status = resp && resp.status;
        const data = resp && resp.data;
        if (isNeedCloud(status, data)) {
          needCloudPassword.value = true;
          cloudPassword.value = "";
          pendingDownloadName.value = null;
          ElMessage.info("请输入 cloud 密码（弹窗内嵌），填写后点击'刷新并重试'。若不填写可取消。");
          const e = new Error("needCloud");
          (e as any).code = "needCloud";
          throw e;
        }
        if (status && status !== 404) {
          let msg = "检查文件可用性失败";
          try {
            msg = (data && (data.msg || data.error_msg)) || err.message || msg;
          } catch (ex) {
            console.warn(ex);
          }
          ElMessage.error(msg);
          const e = new Error("fatal");
          (e as any).code = "fatal";
          throw e;
        }
        return false;
      }
    };

    const worker = async (initialCand: string) => {
      let cand = initialCand;
      while (cand && display.length < maxDisplay) {
        const ok = await checkOne(cand);
        if (ok) return;
        if (nextIdx < allTimes.value.length) {
          cand = allTimes.value[nextIdx++];
        } else {
          return;
        }
      }
    };

    try {
      const workers: Promise<any>[] = [];
      for (let i = 0; i < maxDisplay && nextIdx < allTimes.value.length; i++) {
        const cand = allTimes.value[nextIdx++];
        workers.push(worker(cand));
      }
      await Promise.all(workers);
    } catch (e: any) {
      if (e && (e.code === "needCloud" || (e.message && e.message === "needCloud"))) {
        timesChecking.value = false;
        return;
      }
      timesChecking.value = false;
      return;
    }

    display.sort((a, b) => a.sourceIdx - b.sourceIdx);
    timesList.value = display.map((it, idx) => ({
      index: idx + 1,
      name: it.name,
      viewUrl: it.viewUrl,
      downloadUrl: it.downloadUrl,
    }));
  } catch (e: any) {
    const resp = e && (e.response || e);
    const status = resp && resp.status;
    const data = resp && resp.data;
    if (isNeedCloud(status, data)) {
      needCloudPassword.value = true;
      cloudPassword.value = "";
      pendingDownloadName.value = null;
      ElMessage.info("请输入 cloud 密码（弹窗内嵌），填写后点击'刷新并重试'。若不填写可关闭弹窗。");
      return;
    }

    let msg = "查询时间失败";
    try {
      if (data && data.data && data.data.msg) {
        msg = data.data.msg;
      } else if (data && data.msg) {
        msg = data.msg;
      } else if (e && e.message) {
        msg = e.message;
      }
    } catch (ex) {
      console.warn(ex);
    }
    ElMessage.error(msg);
  } finally {
    timesChecking.value = false;
  }
}

async function viewTime(url: string | null | undefined) {
  if (!url) {
    ElMessage.error("无可用外链");
    return;
  }
  window.open(String(url), "_blank");
}

async function downloadTime(name: string) {
  await selectTime(name);
}

async function selectTime(name: string) {
  if (!currentCategory.value || !currentCategory.value.id) {
    ElMessage.error("缺少当前类目信息");
    return;
  }
  const id = String(currentCategory.value.id);
  try {
    const chk = await CategoryAPI.checkFile(id, name);
    if (chk && chk.exists && chk.downloadUrl) {
      window.open(String(chk.downloadUrl), "_blank");
      return;
    }
    const res = await CategoryAPI.downloadFile(id, name);
    // CategoryAPI.downloadFile is expected to return a Blob.
    const blob = res as Blob;

    // Try to read textual body first: backend may return JSON or plain URL string.
    try {
      const text = await blob.text();
      // Try JSON parse
      try {
        const parsed = JSON.parse(text);
        const maybeDownloadUrl =
          (parsed && parsed.data && parsed.data.downloadUrl) || parsed.downloadUrl || null;
        const maybeViewUrl =
          (parsed && parsed.data && parsed.data.viewUrl) || parsed.viewUrl || null;
        if (maybeDownloadUrl) {
          window.open(String(maybeDownloadUrl), "_blank");
          return;
        }
        if (maybeViewUrl) {
          window.open(String(maybeViewUrl), "_blank");
          return;
        }
      } catch {
        // Not JSON — maybe plain URL text
        const trimmed = (text || "").trim();
        if (/^https?:\/\//i.test(trimmed)) {
          window.open(trimmed, "_blank");
          return;
        }
      }
    } catch {
      // reading as text failed; fall through to binary handling
    }

    // Fallback: treat as binary blob and open via object URL
    const url = window.URL.createObjectURL(blob as any);
    window.open(url, "_blank");
    setTimeout(() => window.URL.revokeObjectURL(url), 60 * 1000);
    return;
  } catch (err: any) {
    const resp = err && (err.response || err);
    const status = resp && resp.status;
    const data = resp && resp.data;
    if (status === 404 || (data && data.error_msg && data.error_msg.includes("File not found"))) {
      ElMessage.error("文件不存在");
    } else if (isNeedCloud(status, data)) {
      try {
        needCloudPassword.value = true;
        cloudPassword.value = "";
        pendingDownloadName.value = name;
        ElMessage.info("请输入 cloud 密码（弹窗内嵌），填写后点击'刷新并重试'以继续下载。");
        return;
      } catch (ex) {
        console.warn(ex);
        ElMessage.info("已取消");
      }
    } else {
      let msg = "下载失败";
      try {
        msg = (data && (data.msg || data.error_msg)) || err.message || msg;
      } catch (ex) {
        console.warn(ex);
      }
      ElMessage.error(msg);
    }
  }
}

async function onDateChanged(val: string | null) {
  if (!val) {
    if (currentCategory.value && currentCategory.value.id) {
      await loadTimes(String(currentCategory.value.id));
    }
    return;
  }
  const idx = allTimesDates.value ? allTimesDates.value.findIndex((d) => d === val) : -1;
  if (idx >= 0) {
    const folderName = allTimes.value[idx];
    try {
      const chk = await CategoryAPI.checkFile(String(currentCategory.value.id), folderName);
      if (chk && chk.exists) {
        timesList.value = [
          {
            index: 1,
            name: folderName,
            viewUrl: chk.viewUrl || null,
            downloadUrl: chk.downloadUrl || null,
          },
        ];
      } else {
        timesList.value = [];
        ElMessage.warning("所选日期对应的文件不存在");
      }
    } catch (err) {
      console.warn(err);
      timesList.value = [];
      ElMessage.warning("检查文件失败");
    }
  } else {
    timesList.value = [];
    ElMessage.warning("未找到与所选日期匹配的时间记录");
  }
}

async function refreshCloudPasswordAndRetry() {
  if (!cloudPassword.value) {
    ElMessage.warning("请输入 cloud 密码后再刷新");
    return;
  }
  try {
    timesChecking.value = true;
    await UserAPI.updateProfile({ cloudPassword: cloudPassword.value });
    ElMessage.success("已刷新 cloud token，正在重试...");
    needCloudPassword.value = false;
    const pending = pendingDownloadName.value;
    pendingDownloadName.value = null;
    const catId = currentCategory.value && currentCategory.value.id;
    if (pending && catId) {
      await selectTime(pending);
    } else if (catId) {
      await loadTimes(String(catId));
    }
  } catch (err) {
    console.warn(err);
    ElMessage.error("刷新失败，请检查密码或联系管理员");
    // Nested fallback retry logic
    try {
      timesChecking.value = true;
      await UserAPI.updateProfile({ cloudPassword: cloudPassword.value });
      ElMessage.success("已请求后端刷新 cloud token，正在验证状态...");

      try {
        const profile: any = await UserAPI.getProfile();
        const cached = !!(
          profile &&
          (profile.seafileCached || (profile.data && profile.data.seafileCached))
        );
        if (cached) {
          try {
            const userStore = useUserStoreHook();
            (userStore as any).seafileCached = cached;
          } catch (e) {
            console.warn("更新 userStore seafileCached 失败", e);
          }

          needCloudPassword.value = false;
          const pending = pendingDownloadName.value;
          pendingDownloadName.value = null;
          cloudPassword.value = "";
          const catId = currentCategory.value && currentCategory.value.id;
          if (pending && catId) {
            await selectTime(pending);
          } else if (catId) {
            await loadTimes(String(catId));
          }
        } else {
          ElMessage.error("后端未能缓存 Seafile token，请确认密码是否正确或联系管理员");
        }
      } catch (e) {
        console.warn("验证 profile 失败", e);
        ElMessage.error("刷新后验证失败，请稍后重试");
      }
    } catch (err) {
      console.warn(err);
      ElMessage.error("刷新失败，请检查密码或联系管理员");
    } finally {
      timesChecking.value = false;
      cloudPassword.value = "";
    }
  }
}

defineExpose({ open });
</script>
