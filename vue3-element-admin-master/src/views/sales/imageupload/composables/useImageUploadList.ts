/**
 * 图片上传管理列表页业务逻辑 composable。
 *
 * @module useImageUploadList
 * @description 封装查询、分页、删除、同步（单个/批量）、CSV 导入、CSV 导出等全部业务状态与方法。
 *              视图层仅负责模板编排和模板引用（formRef/dialogRef）的传递。
 */

import { ref, reactive } from "vue";
import type { UploadProps, UploadRequestOptions } from "element-plus";
import { ImageUploadAPI, type ImageUploadPageQuery, type ImageUploadVO } from "@/api/imageUpload";

export function useImageUploadList() {
  /** 表格加载状态。 */
  const isLoading = ref(false);

  /** 表格勾选行 ID 集合。 */
  const selectedIds = ref<string[]>([]);

  /** 批量操作按钮禁用状态（无选中项时为 true）。 */
  const isBatchDisabled = ref(true);

  /** 表格数据总条数。 */
  const total = ref(0);

  /** 查询参数。 */
  const queryParams = reactive<ImageUploadPageQuery>({
    pageNum: 1,
    pageSize: 20,
    imageGroup: "",
    status: undefined as string | undefined,
  });

  /** 表格当前页数据。 */
  const tableData = ref<ImageUploadVO[]>([]);

  /**
   * 获取分页列表数据。
   */
  function fetchData() {
    isLoading.value = true;
    ImageUploadAPI.getPage(queryParams)
      .then((data) => {
        tableData.value = data.list;
        total.value = data.total;
      })
      .finally(() => {
        isLoading.value = false;
      });
  }

  /**
   * 查询（重置页码后拉取数据）。
   */
  function handleQuery() {
    queryParams.pageNum = 1;
    fetchData();
  }

  /**
   * 重置查询条件并重新查询（不含表单重置，由视图层调用 queryFormRef.resetFields 后触发）。
   */
  function resetAndQuery() {
    queryParams.pageNum = 1;
    fetchData();
  }

  /**
   * 每页条数变化回调。
   *
   * @param size - 新的每页条数。
   */
  function handleSizeChange(size: number) {
    queryParams.pageSize = size;
    handleQuery();
  }

  /**
   * 当前页码变化回调。
   *
   * @param page - 新的页码。
   */
  function handleCurrentChange(page: number) {
    queryParams.pageNum = page;
    handleQuery();
  }

  /**
   * 表格选中行变化回调。
   *
   * @param selection - 当前选中的行数据列表。
   */
  function handleSelectionChange(selection: ImageUploadVO[]) {
    selectedIds.value = selection.map((item) => item.id);
    isBatchDisabled.value = !selection.length;
  }

  /**
   * 删除单个图片组。
   *
   * @param row - 行数据。
   */
  function handleDelete(row: ImageUploadVO) {
    ElMessageBox.confirm("确认删除该图片组吗?", "警告", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }).then(() => {
      ImageUploadAPI.deleteByIds(row.id).then(() => {
        ElMessage.success("删除成功");
        handleQuery();
      });
    });
  }

  /**
   * 批量删除选中的图片组。
   */
  function handleBatchDelete() {
    ElMessageBox.confirm("确认删除选中的数据项?", "警告", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }).then(() => {
      ImageUploadAPI.deleteByIds(selectedIds.value.join(",")).then(() => {
        ElMessage.success("删除成功");
        handleQuery();
      });
    });
  }

  /**
   * 单行同步命令处理。
   *
   * @param cmd - 同步命令：'breakpoint'=断点同步，'resync'=重新同步。
   * @param row - 行数据。
   */
  function handleSyncCommand(cmd: string, row: ImageUploadVO) {
    const forceResync = cmd === "resync";
    const label = forceResync ? "重新同步" : "断点同步";
    isLoading.value = true;
    ImageUploadAPI.sync(row.id, forceResync)
      .then(() => {
        ElMessage.success(`${label}成功`);
        handleQuery();
      })
      .finally(() => {
        isLoading.value = false;
      });
  }

  /**
   * 批量同步选中的图片组。
   *
   * @param forceResync - true=全部重新同步，false=仅同步未成功项。
   */
  function handleBatchSync(forceResync: boolean) {
    const label = forceResync ? "重新同步" : "断点同步";
    ElMessageBox.confirm(`确认${label}选中的 ${selectedIds.value.length} 条数据项?`, "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "info",
    }).then(() => {
      isLoading.value = true;
      ImageUploadAPI.batchSync(selectedIds.value, forceResync)
        .then((res: any) => {
          const successCount = res.filter((r: any) => r.success).length;
          const failCount = res.length - successCount;
          if (failCount === 0) {
            ElMessage.success(`${label}成功 ${successCount} 条`);
          } else {
            ElMessage.warning(`${label}完成: 成功 ${successCount} 条, 失败 ${failCount} 条`);
          }
          handleQuery();
        })
        .finally(() => {
          isLoading.value = false;
        });
    });
  }

  /**
   * 下载图片组数据为 CSV 文件。
   *
   * @description 有选中数据时下载选中行，无选中时询问是否下载全部（当前页）。
   *             文件包含 BOM (`\uFEFF`) 以解决 Excel 打开乱码。
   */
  function handleDownload() {
    /**
     * 将数据数组导出为 CSV 并触发浏览器下载。
     *
     * @param data - 行数据数组。
     */
    const downloadData = (data: ImageUploadVO[]) => {
      if (!data || data.length === 0) {
        ElMessage.warning("暂无数据可下载");
        return;
      }

      // CSV Header + BOM for Excel UTF-8 compatibility
      let csvContent = "图片组,状态,Cloud 路径,日志\n";

      data.forEach((row) => {
        const logLastLine = row.log ? row.log.split("\n").pop() : "";
        const escape = (val: any) => `"${String(val || "").replace(/"/g, '""')}"`;

        csvContent += `${escape(row.imageGroup)},${escape(row.status)},${escape(row.cloudPath)},${escape(logLastLine)}\n`;
      });

      const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);
      link.setAttribute("href", url);
      link.setAttribute("download", "image_uploads.csv");
      link.style.visibility = "hidden";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };

    if (selectedIds.value.length > 0) {
      const selectedRows = tableData.value.filter((row) => selectedIds.value.includes(row.id));
      downloadData(selectedRows);
    } else {
      ElMessageBox.confirm("当前没选择数据，是否下载全部数据?", "提示", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "info",
      }).then(() => {
        downloadData(tableData.value);
      });
    }
  }

  /**
   * CSV 文件上传前的校验。
   *
   * @param rawFile - 待上传的原始文件。
   * @returns 是否为合法的 CSV 文件。
   */
  const beforeImport: UploadProps["beforeUpload"] = (rawFile) => {
    const isCSV = rawFile.name.toLowerCase().endsWith(".csv");
    if (!isCSV) {
      ElMessage.error("只能上传 CSV 格式的文件!");
      return false;
    }
    return true;
  };

  /**
   * 处理 CSV 文件导入。
   *
   * @description 上传 CSV → 解析后端返回结果 → 弹窗展示导入汇总 → 用户选择同步方式 → 执行批量同步。
   *              整个流程通过 ElMessageBox HTML 弹窗交互完成。
   * @param options - Element Plus 上传请求选项。
   * @returns Promise（供 el-upload 的 http-request 使用）。
   */
  const handleImport = (options: UploadRequestOptions) => {
    const { file } = options;
    isLoading.value = true;
    return ImageUploadAPI.importCsv(file as File)
      .then((res: any) => {
        const r = res as any;
        const c = r.created || 0;
        const u = r.updated || 0;
        const f = r.failed || 0;
        const fItems = r.failed_items || [];
        const sIds = r.success_ids || [];

        let msg = `<p><strong>导入结果汇总：</strong></p>`;
        if (c > 0) msg += `<p>✅ 新增: ${c} 条</p>`;
        if (u > 0) msg += `<p>🔄 更新: ${u} 条</p>`;

        if (f > 0) {
          msg += `<p style="color:#F56C6C">❌ 失败: ${f} 条</p>`;
          msg += `<div style="max-height:150px;overflow-y:auto;background:#fef0f0;padding:5px;border-radius:4px;margin:5px 0;">`;
          fItems.forEach((item: string) => {
            msg += `<div style="color:#F56C6C;font-size:12px">${item}</div>`;
          });
          msg += `</div>`;
        }

        if (c === 0 && u === 0 && f === 0) {
          ElMessage.warning("未导入任何有效数据");
          handleQuery();
          return;
        }

        msg += `<p style="margin-top:15px">请选择同步方式：</p>`;
        msg += `<div style="margin:10px 0">`;
        msg += `<label style="display:block;margin:5px 0;cursor:pointer"><input type="radio" name="syncMode" value="breakpoint" checked style="margin-right:8px">断点同步（仅同步未成功项）</label>`;
        msg += `<label style="display:block;margin:5px 0;cursor:pointer"><input type="radio" name="syncMode" value="resync" style="margin-right:8px">重新同步（全部重新同步）</label>`;
        msg += `</div>`;

        ElMessageBox.confirm(msg, "导入完成", {
          distinguishCancelAndClose: true,
          confirmButtonText: "立即同步",
          cancelButtonText: "稍后处理",
          dangerouslyUseHTMLString: true,
          type: f > 0 ? "warning" : "success",
          draggable: true,
        })
          .then(() => {
            const selectedRadio = document.querySelector(
              'input[name="syncMode"]:checked'
            ) as HTMLInputElement;
            const forceResync = selectedRadio?.value === "resync";
            const syncLabel = forceResync ? "重新同步" : "断点同步";

            if (sIds.length > 0) {
              isLoading.value = true;
              ImageUploadAPI.batchSync(sIds, forceResync)
                .then((syncRes: any) => {
                  const successCount = syncRes.filter((r: any) => r.success).length;
                  const failCount = syncRes.length - successCount;
                  if (failCount === 0) {
                    ElMessage.success(`${syncLabel}成功 ${successCount} 条`);
                  } else {
                    ElMessage.warning(
                      `${syncLabel}完成: 成功 ${successCount} 条, 失败 ${failCount} 条`
                    );
                  }
                  handleQuery();
                })
                .finally(() => {
                  isLoading.value = false;
                });
            } else {
              ElMessage.info("没有可同步的数据");
              handleQuery();
            }
          })
          .catch(() => {
            handleQuery();
          });
      })
      .catch((err) => {
        console.error("Import error", err);
        ElMessage.error(err.message || err.msg || "导入失败");
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  return {
    isLoading,
    selectedIds,
    isBatchDisabled,
    total,
    queryParams,
    tableData,
    fetchData,
    handleQuery,
    resetAndQuery,
    handleSizeChange,
    handleCurrentChange,
    handleSelectionChange,
    handleDelete,
    handleBatchDelete,
    handleSyncCommand,
    handleBatchSync,
    handleDownload,
    beforeImport,
    handleImport,
  };
}
