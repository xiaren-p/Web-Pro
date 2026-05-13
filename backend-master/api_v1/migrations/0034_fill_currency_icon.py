"""
数据迁移：补全 currency_icon 表中缺失的国家 → 货币代码映射。

规则：update_or_create 保留已有记录，仅插入缺失行，不覆盖用户已修改的数据。
"""

from django.db import migrations


# (country, code, icon, name)
CURRENCY_ICON_DATA = [
    # 欧元区
    ("FR", "EUR", "€", "欧元"),
    ("DE", "EUR", "€", "欧元"),
    ("IT", "EUR", "€", "欧元"),
    ("ES", "EUR", "€", "欧元"),
    ("NL", "EUR", "€", "欧元"),
    ("BE", "EUR", "€", "欧元"),
    ("AT", "EUR", "€", "欧元"),
    ("FI", "EUR", "€", "欧元"),
    ("PT", "EUR", "€", "欧元"),
    ("IE", "EUR", "€", "欧元"),
    ("GR", "EUR", "€", "欧元"),
    ("LU", "EUR", "€", "欧元"),
    ("CY", "EUR", "€", "欧元"),
    ("EE", "EUR", "€", "欧元"),
    ("LT", "EUR", "€", "欧元"),
    ("LV", "EUR", "€", "欧元"),
    ("MT", "EUR", "€", "欧元"),
    ("SI", "EUR", "€", "欧元"),
    ("SK", "EUR", "€", "欧元"),
    # 英语圈
    ("US", "USD", "$",    "美元"),
    ("GB", "GBP", "£",    "英镑"),
    ("UK", "GBP", "£",    "英镑"),
    ("CA", "CAD", "CA$",  "加拿大元"),
    ("AU", "AUD", "A$",   "澳大利亚元"),
    # 亚洲
    ("JP", "JPY", "JP¥",  "日元"),
    ("CN", "CNY", "￥",   "人民币"),
    ("HK", "HKD", "HK$",  "港元"),
    ("SG", "SGD", "S$",   "新加坡元"),
    ("IN", "INR", "₹",    "印度卢比"),
    ("MY", "MYR", "RM",   "马来西亚林吉特"),
    ("ID", "IDR", "Rp",   "印度尼西亚卢比"),
    ("PH", "PHP", "₱",    "菲律宾比索"),
    ("TH", "THB", "฿",    "泰铢"),
    ("VN", "VND", "₫",    "越南盾"),
    # 中东
    ("AE", "AED", "د",    "阿联酋迪拉姆"),
    ("SA", "SAR", "﷼",   "沙特里亚尔"),
    # 欧洲（非欧元区）
    ("SE", "SEK", "kr",   "瑞典克朗"),
    ("PL", "PLN", "zł",   "波兰兹罗提"),
    ("TR", "TRY", "₺",    "土耳其里拉"),
    # 美洲
    ("MX", "MXN", "Mex$", "墨西哥比索"),
    ("BR", "BRL", "R$",   "巴西雷亚尔"),
]


def fill_currency_icon(apps, schema_editor):
    """补填所有缺失的 currency_icon 记录（已存在则跳过，不覆盖）。"""
    CurrencyIcon = apps.get_model("api_v1", "CurrencyIcon")
    for country, code, icon, name in CURRENCY_ICON_DATA:
        CurrencyIcon.objects.get_or_create(
            country=country,
            defaults={"code": code, "icon": icon, "name": name},
        )


def noop(apps, schema_editor):
    """回滚时不做操作，保留数据以防意外删除。"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0033_lxadportfolios_lxcampaigninfo_lxcampaignmetrics_and_more"),
    ]

    operations = [
        migrations.RunPython(fill_currency_icon, noop),
    ]
