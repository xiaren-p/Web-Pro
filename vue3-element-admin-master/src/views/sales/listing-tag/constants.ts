export const tagStatusOptions = [
  { label: "创建中", value: "creating" },
  { label: "正常", value: "normal" },
  { label: "修改中", value: "modifying" },
  { label: "删除中", value: "deleting" },
];

export const presetColors = [
  { label: "红色", value: "#f56c6c" },
  { label: "橙色", value: "#e6a23c" },
  { label: "黄色", value: "#f0d930" },
  { label: "绿色", value: "#67c23a" },
  { label: "青色", value: "#40bfff" },
  { label: "蓝色", value: "#409eff" },
  { label: "紫色", value: "#9093ff" },
  { label: "灰色", value: "#909399" },
];

export const tableColumns = [
  {
    prop: "tagName",
    label: "标签名称",
    fixed: "left",
    minWidth: 140,
  },
  {
    prop: "type",
    label: "标签类型",
    width: 120,
    align: "center",
  },
  {
    prop: "createByName",
    label: "创建人",
    width: 120,
    align: "center",
  },
  {
    prop: "modifyByName",
    label: "最后编辑人",
    width: 130,
    align: "center",
  },
  {
    prop: "color",
    label: "颜色",
    width: 100,
    align: "center",
  },
  {
    prop: "status",
    label: "状态",
    width: 100,
    align: "center",
  },
  {
    prop: "createTime",
    label: "创建时间",
    width: 170,
    sortable: "custom",
  },
  {
    prop: "updateTime",
    label: "更新时间",
    width: 170,
    sortable: "custom",
  },
  {
    prop: "actions",
    label: "操作",
    fixed: "right",
    width: 140,
    align: "center",
  },
];
