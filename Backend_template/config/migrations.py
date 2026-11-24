"""0.2 增量升级：保留原会话，允许无案件的日常聊天。"""
from sqlalchemy import inspect, text
from sqlalchemy.schema import AddConstraint


def upgrade_connection(connection):
    inspector = inspect(connection)
    if "conversations" not in inspector.get_table_names():
        return
    case_column = next(c for c in inspector.get_columns("conversations") if c["name"] == "case_id")
    if case_column["nullable"]:
        return
    dialect = connection.dialect.name
    if dialect == "mysql":
        connection.execute(text("ALTER TABLE conversations MODIFY COLUMN case_id INTEGER NULL"))
        connection.commit()
    elif dialect == "sqlite":
        # SQLite 需重建表。事务外暂停外键，避免 DROP 引发消息级联删除。
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        try:
            with connection.begin():
                connection.exec_driver_sql("""CREATE TABLE conversations_v02 (
                    id INTEGER NOT NULL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
                    title VARCHAR(100) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL)""")
                connection.exec_driver_sql("INSERT INTO conversations_v02 SELECT id,user_id,case_id,title,created_at,updated_at FROM conversations")
                connection.exec_driver_sql("DROP TABLE conversations")
                connection.exec_driver_sql("ALTER TABLE conversations_v02 RENAME TO conversations")
                connection.exec_driver_sql("CREATE INDEX ix_conversations_user_id ON conversations(user_id)")
                connection.exec_driver_sql("CREATE INDEX ix_conversations_case_id ON conversations(case_id)")
        finally:
            connection.rollback()
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
    else:
        raise RuntimeError("当前数据库不支持自动升级，请先执行会话表迁移")


async def initialize_database(engine, metadata):
    async with engine.connect() as connection:
        await connection.run_sync(upgrade_connection)
        await connection.commit()
        async with connection.begin():
            await connection.run_sync(metadata.create_all)
        if engine.dialect.name == "mysql":
            await connection.run_sync(ensure_mysql_integrity, metadata)


def ensure_mysql_integrity(connection, metadata):
    """修复旧环境忽略的事务与外键；孤立记录需人工处理，不自动删除。"""
    quote = connection.dialect.identifier_preparer.quote
    # 任何 DDL 前先检查所有关系，避免迁移过程中才发现孤立数据。
    for table in metadata.sorted_tables:
        for fk in table.foreign_keys:
            child, parent = quote(table.name), quote(fk.column.table.name)
            local, remote = quote(fk.parent.name), quote(fk.column.name)
            count = connection.scalar(text(f"SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p ON c.{local}=p.{remote} WHERE c.{local} IS NOT NULL AND p.{remote} IS NULL"))
            if count:
                raise RuntimeError(f"{table.name}.{fk.parent.name} 存在 {count} 条孤立记录，请先备份并处理后重新启动")
    for table in metadata.sorted_tables:
        engine_name = connection.scalar(text("SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=:table"), {"table": table.name})
        if engine_name.lower() != "innodb":
            connection.execute(text(f"ALTER TABLE {quote(table.name)} ENGINE=InnoDB"))
            connection.commit()
    for table in metadata.sorted_tables:
        existing = inspect(connection).get_foreign_keys(table.name)
        for constraint in table.foreign_key_constraints:
            columns = [element.parent.name for element in constraint.elements]
            target = next(iter(constraint.elements)).column.table.name
            matches = [fk for fk in existing if fk["constrained_columns"] == columns and fk["referred_table"] == target]
            if matches and matches[0].get("options", {}).get("ondelete", "").upper() == "CASCADE":
                continue
            if matches:
                raise RuntimeError(f"{table.name} 的现有外键规则与项目不一致，请检查后重试")
            constraint.name = "fk_" + table.name + "_" + "_".join(columns)
            connection.execute(AddConstraint(constraint))
            connection.commit()
    connection.commit()
