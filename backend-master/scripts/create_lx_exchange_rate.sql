-- 生产环境建表脚本：lx_exchange_rate（手动执行）
-- 由于模型 managed=False，Django 迁移不会自动建表，需在 MySQL 终端执行。

CREATE TABLE IF NOT EXISTS `lx_exchange_rate` (
    `id` bigint NOT NULL AUTO_INCREMENT,
    `date` varchar(10) NOT NULL DEFAULT '' COMMENT '汇率年月，形如 2021-08',
    `code` varchar(10) NOT NULL DEFAULT '' COMMENT '币种，如 CNY',
    `icon` varchar(10) NOT NULL DEFAULT '' COMMENT '币种符号，如 ￥',
    `name` varchar(50) NOT NULL DEFAULT '' COMMENT '币种名，如 人民币',
    `rate_org` varchar(20) NOT NULL DEFAULT '1.0000' COMMENT '官方汇率，数据来源于中国银行',
    `my_rate` varchar(20) NOT NULL DEFAULT '1.0000' COMMENT '我的汇率，用户自定义，系统优先使用',
    `update_time` varchar(30) NOT NULL DEFAULT '' COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_code` (`code`),
    KEY `idx_date` (`date`),
    KEY `idx_code_date` (`code`, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='汇率表（领星 → 基础数据 → 汇率）';
