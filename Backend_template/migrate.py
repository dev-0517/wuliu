# -*- coding: utf-8 -*-
"""轻量迁移：对已存在的表自动补充新增列（create_all 不会改已有表）。"""
import sqlalchemy

from db import Base, engine
from models import Payment, Product, User  # noqa: F401 确保所有表已注册

# 表名 -> {列名: DDL 类型片段}
NEW_COLUMNS = {
    "users": {
        "display_name": "VARCHAR(50)",
        "avatar": "TEXT",
        "bound_phone": "VARCHAR(20)",
        "bound_wechat": "VARCHAR(80)",
        "bound_qq": "VARCHAR(80)",
    },
    "products": {
        "image": "VARCHAR(300)",
    },
}


def migrate_columns() -> None:
    insp = sqlalchemy.inspect(engine)
    with engine.begin() as conn:
        for table, cols in NEW_COLUMNS.items():
            if table not in insp.get_table_names():
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols.items():
                if name not in existing:
                    conn.execute(sqlalchemy.text(
                        f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def migrate_tables() -> None:
    Base.metadata.create_all(bind=engine)   # 新表（如 payments）
    migrate_columns()                       # 旧表补新列
