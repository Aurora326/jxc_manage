# jxc_manage
1) 总体目标与边界

目标：实现进销存闭环（采购入库/销售出库/调拨/盘点可选），做到：

库存数量准确、可追溯（流水）

家电整机可按 SN 逐台追踪（入库来源、出库去向、保修期）

多仓库之间调拨可控

本机部署：一台电脑运行，浏览器访问；可扩展到局域网多人使用

边界（第一版不做或弱化）

复杂财务：应收应付/发票/总账（后续可加）

复杂成本：先提供“简化移动平均”接口位（后续强化）

售后工单：先做 SN 查询与保修字段预留（后续做维修流程）

2) 技术架构
2.1 后端

FastAPI（接口 + OpenAPI 文档）

SQLAlchemy 2.x（ORM）

Alembic（数据库迁移）

鉴权：JWT（Access/Refresh）

日志：Python logging（建议按天滚动）

2.2 前端

Vue 3 + TypeScript + Vite

状态：Pinia

UI：Element Plus（单据编辑/表格体验成熟）

表格编辑：明细行可用“可编辑表格”组件实现

2.3 数据库（SQLite）

SQLite 文件：data/app.db

启动即执行（关键）：

PRAGMA journal_mode=WAL;

PRAGMA foreign_keys=ON;

PRAGMA synchronous=NORMAL;

3) 业务模型（统一“单据 + 明细 + 审核 + 过账”）
3.1 单据类型（doc_type）

PURCHASE_IN：采购入库

SALES_OUT：销售出库

TRANSFER：调拨（A仓出、B仓入）

ADJUST：库存调整（盘盈盘亏/其它调整）——可第二期做

SALES_RETURN/PURCHASE_RETURN：退货——第三期做

3.2 状态机（status）

DRAFT 草稿（可编辑）

APPROVED 已审核（锁定内容，可选）

POSTED 已过账（写库存流水 + 更新库存余额 + SN 状态变更；禁止修改）

VOID 作废（建议用“红冲单”替代硬回滚）

库存变动只来自“过账（POST）”。保存/审核不动库存。

4) 数据库设计（字段 + 约束 + 索引）

你可以按此建表（Alembic迁移），后续从 SQLite 平滑迁移到 PostgreSQL 也很顺。

4.1 主数据

warehouses

id PK

code（唯一，可选）

name

location（可选）

索引：UNIQUE(code) 或 UNIQUE(name)（二选一）

partners（客户/供应商共用）

id PK

type：CUSTOMER / SUPPLIER

name

phone、address（可选）

索引：INDEX(type, name)

products

id PK

sku（唯一）

name

brand（可选）

model（型号，可选但家电建议必填）

barcode（可选）

unit（台/件）

track_sn（0/1）

warranty_months（默认保修月数，可选）

is_active

索引：UNIQUE(sku)，INDEX(name)，INDEX(brand, model)

users / roles / user_roles

标准 RBAC（最小可先做 users + role 字段；后续再细化）

4.2 单据（统一结构）

docs（单据头）

id PK

doc_type

doc_no（单号，唯一）

biz_date（业务日期）

partner_id（采购=供应商；销售=客户；调拨可空）

from_wh_id、to_wh_id（调拨单头可填；也可只在行级填）

status

remark

created_by, created_at

approved_by, approved_at

posted_by, posted_at

索引：

UNIQUE(doc_no)

INDEX(doc_type, biz_date)

INDEX(status)

doc_lines（单据明细）

id PK

doc_id FK

line_no（行号）

product_id FK

qty（数量，正数）

unit_price（采购/销售用；调拨/盘点可为NULL）

amount（可存冗余：qty*unit_price）

from_wh_id、to_wh_id（支持一张单多仓；调拨行级最清晰）

remark（可选）

索引：

INDEX(doc_id)

INDEX(product_id)

INDEX(from_wh_id, product_id)

INDEX(to_wh_id, product_id)

约束建议：

qty > 0

(doc_id, line_no) 唯一

4.3 库存

stock_balances（库存余额）

warehouse_id FK

product_id FK

qty_on_hand（当前库存）

主键/唯一：(warehouse_id, product_id)

索引：主键已够；可加 INDEX(product_id)

stock_ledger（库存流水）

id PK

warehouse_id

product_id

ref_doc_id

ref_line_id

ref_type（同 doc_type 或更细）

biz_date

in_qty、out_qty（一进一出，另一边为0）

unit_cost（可选，后续毛利）

created_at

索引：

INDEX(warehouse_id, product_id, biz_date)

INDEX(ref_doc_id)

4.4 序列号（SN）

product_sns

id PK

product_id FK

sn（唯一）

status：IN_STOCK / OUT_STOCK / LOCKED / SCRAPPED

warehouse_id（当前所在仓；OUT_STOCK 时可为空或保留发出仓）

in_doc_id, in_line_id, in_date

out_doc_id, out_line_id, out_date

warranty_start, warranty_end（可在出库时写入）

索引/约束：

UNIQUE(sn)

INDEX(product_id, status)

INDEX(warehouse_id, status)

doc_line_sns（单据行与 SN 关联）

id PK

doc_id FK

line_id FK

sn_id FK（指向 product_sns）

约束：

(line_id, sn_id) 唯一

避免一个 SN 同时被多单占用：可在业务逻辑中校验或加唯一约束 (sn_id, doc_id)（看你是否允许同单重复扫描）

5) 过账逻辑（事务 + 校验 + 幂等）
5.1 通用规则

已 POSTED 不能重复过账（幂等）

校验行级仓库：

入库：必须有 to_wh_id

出库：必须有 from_wh_id

调拨：必须同时有 from_wh_id 与 to_wh_id，且不能相同

SN 商品校验：

入库：SN 数量必须等于 qty

出库：SN 必须都在 from_wh_id 且状态 IN_STOCK

调拨：SN 在 from_wh，过账后变更 warehouse_id=to_wh

5.2 伪代码（核心）
def post_doc(doc_id, user_id):
    with db.transaction():  # 必须事务
        doc = lock_doc_for_update(doc_id)

        if doc.status == 'POSTED':
            return  # 幂等：直接成功

        assert doc.status in ('APPROVED', 'DRAFT')  # 看你是否允许草稿直接过账

        lines = load_lines(doc_id)

        # 1) 逐行校验（库存、SN、仓库）
        for line in lines:
            product = load_product(line.product_id)

            if doc.doc_type == 'PURCHASE_IN':
                wh = line.to_wh_id or doc.to_wh_id
                assert wh is not None
                if product.track_sn:
                    sns = load_line_sns(line.id)
                    assert len(sns) == line.qty
                    assert all(sn.status in ('LOCKED','IN_STOCK')?  # 入库一般新增或LOCKED
                               for sn in sns)

            if doc.doc_type == 'SALES_OUT':
                wh = line.from_wh_id or doc.from_wh_id
                assert wh is not None
                assert get_balance(wh, line.product_id) >= line.qty
                if product.track_sn:
                    sns = load_line_sns(line.id)
                    assert len(sns) == line.qty
                    assert all(sn.status == 'IN_STOCK' and sn.warehouse_id == wh for sn in sns)

            if doc.doc_type == 'TRANSFER':
                from_wh = line.from_wh_id or doc.from_wh_id
                to_wh = line.to_wh_id or doc.to_wh_id
                assert from_wh and to_wh and from_wh != to_wh
                assert get_balance(from_wh, line.product_id) >= line.qty
                if product.track_sn:
                    sns = load_line_sns(line.id)
                    assert len(sns) == line.qty
                    assert all(sn.status == 'IN_STOCK' and sn.warehouse_id == from_wh for sn in sns)

        # 2) 写流水 + 更新余额 + 更新SN
        for line in lines:
            product = load_product(line.product_id)

            if doc.doc_type == 'PURCHASE_IN':
                wh = line.to_wh_id or doc.to_wh_id
                add_ledger_in(wh, line, doc)
                inc_balance(wh, line.product_id, line.qty)
                if product.track_sn:
                    for sn in load_line_sns(line.id):
                        upsert_sn_in(sn, wh, doc, line)  # 新增或更新 in_xxx 字段, status=IN_STOCK

            elif doc.doc_type == 'SALES_OUT':
                wh = line.from_wh_id or doc.from_wh_id
                add_ledger_out(wh, line, doc)
                dec_balance(wh, line.product_id, line.qty)
                if product.track_sn:
                    for sn in load_line_sns(line.id):
                        mark_sn_out(sn, doc, line)  # status=OUT_STOCK, out_xxx, warranty_start/end

            elif doc.doc_type == 'TRANSFER':
                from_wh = line.from_wh_id or doc.from_wh_id
                to_wh = line.to_wh_id or doc.to_wh_id
                add_ledger_out(from_wh, line, doc)
                dec_balance(from_wh, line.product_id, line.qty)
                add_ledger_in(to_wh, line, doc)
                inc_balance(to_wh, line.product_id, line.qty)
                if product.track_sn:
                    for sn in load_line_sns(line.id):
                        move_sn(sn, to_wh, doc, line)  # warehouse_id=to_wh

        # 3) 更新单据状态
        doc.status = 'POSTED'
        doc.posted_by = user_id
        doc.posted_at = now()
        save(doc)


注意：SQLite 没有真正的 SELECT ... FOR UPDATE，但你可以用“事务 + 更新状态时校验 + 单据行唯一约束”来防并发重复过账；本机部署一般足够。

6) 接口设计（给前端直接对接）
6.1 鉴权

POST /api/auth/login：用户名/密码 → tokens

POST /api/auth/refresh

GET /api/me

6.2 主数据

GET /api/products?q=&page=

POST /api/products

PUT /api/products/{id}

GET /api/partners?type=SUPPLIER|CUSTOMER&q=

POST /api/partners

PUT /api/partners/{id}

GET /api/warehouses

POST /api/warehouses

6.3 单据

GET /api/docs?doc_type=&status=&date_from=&date_to=&q=

GET /api/docs/{id}

POST /api/docs（创建草稿：含头+行）

PUT /api/docs/{id}（仅 DRAFT 可改）

POST /api/docs/{id}/approve

POST /api/docs/{id}/post ✅（核心）

6.4 SN（扫码/批量导入）

GET /api/sns?sn=&status=&warehouse_id=&product_id=

POST /api/docs/{id}/lines/{line_id}/sns/import

body：{ "sns": ["SN001","SN002", ...] }（支持粘贴）

POST /api/docs/{id}/lines/{line_id}/sns/scan

body：{ "sn": "SNxxx" }（逐个扫码）

DELETE /api/docs/{id}/lines/{line_id}/sns/{sn_id}（删除误扫）

6.5 库存

GET /api/stock/balances?warehouse_id=&q=（q可匹配 sku/name/model）

GET /api/stock/ledger?warehouse_id=&product_id=&date_from=&date_to=

7) 前端页面与交互（家电友好）
7.1 菜单

基础资料：商品、客户、供应商、仓库

单据：采购入库、销售出库、调拨单（盘点/调整二期）

库存：库存余额、库存流水、SN 查询

报表：进销存汇总（按日/按商品/按仓库）

7.2 单据编辑页（统一体验）

上：单据头（日期、往来单位、仓库、备注）

下：明细表格（商品、数量、单价、金额、仓库）

SN 商品行：展开/弹窗录入 SN

支持：扫码枪输入、粘贴多行、一键校验重复/长度/是否已存在

右上角按钮：保存草稿 / 审核 / 过账

7.3 SN 查询页（售后/追踪最常用）

输入 SN → 显示：

当前状态（在库/已出库/调拨中…）

当前仓库（如在库）

入库来源（供应商、入库单号、日期）

出库去向（客户、出库单号、日期）

保修到期日（如果启用）

8) 后端项目结构（推荐）
backend/
  app/
    main.py
    core/        # 配置、JWT、依赖注入、异常、日志
    db/          # engine/session、alembic、pragmas
    models/      # SQLAlchemy models
    schemas/     # Pydantic DTO
    services/    # 业务服务：post_doc、sn校验、库存更新
    api/
      routes/
        auth.py
        products.py
        partners.py
        warehouses.py
        docs.py
        stock.py
        sns.py
  alembic/
  requirements.txt

9) 本机部署方式（最省心）
9.1 运行（开发/内网）

后端：uvicorn app.main:app --host 0.0.0.0 --port 8000

前端：npm run build → 输出 dist/

方式A：nginx 托管 dist，反代到 8000

方式B：FastAPI 直接挂载静态文件（更简单）

9.2 数据备份（强烈建议）

每天自动复制 app.db 到 backup/（日期命名）

SQLite WAL 模式下备份建议用 SQLite 的在线备份 API 或在业务低峰复制（简单场景复制也能用，但要注意一致性）

10) 里程碑计划（建议按这个做）

A（最小可用）

商品/客户/供应商/仓库

采购入库、销售出库

库存余额/流水

SN：入库录入 + 出库选择 + SN 查询

B（提升业务贴合）

调拨单（频繁）

审核/反审核策略（可选）

报表：进销存汇总、按仓/按型号

C（完善）

盘点/调整

退货

成本与毛利（移动平均→FIFO）

售后工单（可选）

11) 风险点与我给你的“防踩坑”建议

SN 录入体验决定系统成败：一定要做“扫码/批量粘贴 + 重复校验 + 一键清空”

库存只允许过账变动：否则很快对不上

SQLite 多人并发有限：WAL + 事务基本够用；如果未来多人高频同时过账，再迁移 PG

不建议“直接回滚过账”：用“红冲单/反向单据”更安全（第二期加）
