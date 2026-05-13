<template>
  <el-dialog v-model="visible" :title="title" width="600px" @close="handleClose">
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="120px">
      <el-form-item label="服务器名称" prop="server_name">
        <el-input v-model="formData.server_name" placeholder="请输入服务器名称" />
      </el-form-item>
      <el-form-item label="节点" prop="node">
        <el-input v-model="formData.node" placeholder="请输入节点" />
      </el-form-item>
      <el-form-item label="IP" prop="ip">
        <el-input v-model="formData.ip" placeholder="请输入 IP 地址" />
      </el-form-item>

      <el-form-item label="排序" prop="order_num">
        <el-input-number
          v-model="formData.order_num"
          controls-position="right"
          style="width: 100px"
          :min="0"
        />
      </el-form-item>
      <el-form-item label="状态">
        <el-radio-group v-model="formData.status">
          <el-radio :value="1">正常</el-radio>
          <el-radio :value="0">禁用</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" @click="handleSubmit">确 定</el-button>
        <el-button @click="handleClose">取 消</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from "vue";
import { CrawlerAPI } from "@/api/crawler/conf";
import { ElMessage } from "element-plus";

const emit = defineEmits(["success"]);

const visible = ref(false);
const title = ref("");
const formRef = ref();
const loading = ref(false);

const formData = reactive<any>({
  id: undefined,
  server_name: "",
  node: "",
  ip: "",
  status: 1,
  order_num: 1,
});

const rules = computed(() => ({
  server_name: [{ required: true, message: "服务器名称不能为空", trigger: "blur" }],
  node: [{ required: true, message: "节点不能为空", trigger: "blur" }],
  ip: [{ required: true, message: "IP 不能为空", trigger: "blur" }],
}));

function handleClose() {
  visible.value = false;
  formRef.value?.resetFields();
  formRef.value?.clearValidate();
}

function open(id?: string | number) {
  visible.value = true;
  if (id) {
    title.value = "修改 服务器配置";
    CrawlerAPI.getFormData(String(id)).then((data) => Object.assign(formData, data));
  } else {
    title.value = "新增 服务器配置";
    formData.id = undefined;
    formData.server_name = "";
    formData.node = "";
    formData.ip = "";
    formData.status = 1;
    formData.order_num = 1;
  }
}

function handleSubmit() {
  formRef.value.validate((valid: boolean) => {
    if (valid) {
      loading.value = true;
      const id = formData.id;
      if (id) {
        CrawlerAPI.update(String(id), formData)
          .then(() => {
            ElMessage.success("修改成功");
            handleClose();
            emit("success");
          })
          .finally(() => (loading.value = false));
      } else {
        CrawlerAPI.create(formData)
          .then(() => {
            ElMessage.success("新增成功");
            handleClose();
            emit("success");
          })
          .finally(() => (loading.value = false));
      }
    }
  });
}

defineExpose({ open });
</script>
