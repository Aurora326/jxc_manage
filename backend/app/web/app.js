const state = {
  token: localStorage.getItem('access_token') || '',
  user: null,
  view: 'dashboard'
}

const qs = (id) => document.getElementById(id)
const qsa = (sel) => document.querySelectorAll(sel)

async function request(path, options = {}) {
  const headers = options.headers || {}
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`
  if (!headers['Content-Type'] && options.body) headers['Content-Type'] = 'application/json'

  const res = await fetch(path, { ...options, headers })
  if (!res.ok) {
    const msg = await res.text()
    throw new Error(msg || res.statusText)
  }
  if (res.headers.get('content-type')?.includes('application/json')) {
    return res.json()
  }
  return res.text()
}

function showView(name) {
  state.view = name
  qsa('.view').forEach((v) => v.classList.remove('active'))
  const el = qs(`view-${name}`)
  if (el) el.classList.add('active')
  qsa('.menu-item').forEach((m) => m.classList.toggle('active', m.dataset.view === name))
  qs('pageTitle').textContent =
    {
      dashboard: '概览',
      products: '商品管理',
      warehouses: '仓库管理',
      partners: '客户/供应商',
      docs: '单据中心',
      sns: 'SN 查询'
    }[name] || '概览'
}

function setUserInfo() {
  const chip = qs('userChip')
  const logoutBtn = qs('logoutBtn')
  if (state.user) {
    chip.textContent = `${state.user.username} (${state.user.role})`
    logoutBtn.classList.remove('hidden')
  } else {
    chip.textContent = '未登录'
    logoutBtn.classList.add('hidden')
  }
}

async function login() {
  const username = qs('username').value || 'admin'
  const password = qs('password').value || 'admin123'
  const msg = qs('loginMsg')
  msg.textContent = '登录中...'
  try {
    const data = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    })
    state.token = data.access_token
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    await loadMe()
    msg.textContent = '登录成功'
    showView('dashboard')
    await refreshStats()
  } catch (err) {
    msg.textContent = '登录失败'
  }
}

async function loadMe() {
  try {
    const data = await request('/api/auth/me')
    state.user = data
  } catch {
    state.user = null
  }
  setUserInfo()
}

function logout() {
  state.token = ''
  state.user = null
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  setUserInfo()
  showView('auth')
}

function renderTable(el, columns, rows) {
  if (!rows || rows.length === 0) {
    el.innerHTML = '<tbody><tr><td class="muted">暂无数据</td></tr></tbody>'
    return
  }
  const thead = `<tr>${columns.map((c) => `<th>${c.label}</th>`).join('')}</tr>`
  const tbody = rows
    .map((r) => `<tr>${columns.map((c) => `<td>${r[c.key] ?? ''}</td>`).join('')}</tr>`)
    .join('')
  el.innerHTML = `<thead>${thead}</thead><tbody>${tbody}</tbody>`
}

async function refreshStats() {
  try {
    const [products, warehouses, partners] = await Promise.all([
      request('/api/products'),
      request('/api/warehouses'),
      request('/api/partners')
    ])
    qs('statProducts').textContent = products.length
    qs('statWarehouses').textContent = warehouses.length
    qs('statPartners').textContent = partners.length
    qs('statStatus').textContent = '在线'
  } catch {
    qs('statStatus').textContent = '未登录'
  }
}

async function loadProducts() {
  const q = encodeURIComponent(qs('qProducts').value || '')
  const data = await request(`/api/products?q=${q}`)
  renderTable(qs('productsTable'), [
    { key: 'id', label: 'ID' },
    { key: 'sku', label: 'SKU' },
    { key: 'name', label: '名称' },
    { key: 'brand', label: '品牌' },
    { key: 'model', label: '型号' },
    { key: 'unit', label: '单位' },
    { key: 'track_sn', label: 'SN' }
  ], data)
}

async function loadWarehouses() {
  const data = await request('/api/warehouses')
  renderTable(qs('warehousesTable'), [
    { key: 'id', label: 'ID' },
    { key: 'code', label: '编码' },
    { key: 'name', label: '名称' },
    { key: 'location', label: '位置' }
  ], data)
}

async function loadPartners() {
  const type = encodeURIComponent(qs('partnerType').value || '')
  const q = encodeURIComponent(qs('qPartners').value || '')
  const data = await request(`/api/partners?type=${type}&q=${q}`)
  renderTable(qs('partnersTable'), [
    { key: 'id', label: 'ID' },
    { key: 'type', label: '类型' },
    { key: 'name', label: '名称' },
    { key: 'phone', label: '电话' },
    { key: 'address', label: '地址' }
  ], data)
}

async function loadDocs() {
  const docType = encodeURIComponent(qs('docType').value || '')
  const status = encodeURIComponent(qs('docStatus').value || '')
  const q = encodeURIComponent(qs('qDocs').value || '')
  const data = await request(`/api/docs?doc_type=${docType}&status=${status}&q=${q}`)
  renderTable(qs('docsTable'), [
    { key: 'id', label: 'ID' },
    { key: 'doc_type', label: '类型' },
    { key: 'doc_no', label: '单号' },
    { key: 'biz_date', label: '日期' },
    { key: 'status', label: '状态' }
  ], data)
}

async function loadSns() {
  const sn = encodeURIComponent(qs('snCode').value || '')
  const status = encodeURIComponent(qs('snStatus').value || '')
  const data = await request(`/api/sns?sn=${sn}&status=${status}`)
  renderTable(qs('snsTable'), [
    { key: 'id', label: 'ID' },
    { key: 'sn', label: 'SN' },
    { key: 'status', label: '状态' },
    { key: 'warehouse_id', label: '仓库' },
    { key: 'in_doc_id', label: '入库单' },
    { key: 'out_doc_id', label: '出库单' }
  ], data)
}

const modal = {
  el: qs('modal'),
  title: qs('modalTitle'),
  body: qs('modalBody'),
  submit: qs('modalSubmit'),
  open(title, html, onSubmit) {
    this.title.textContent = title
    this.body.innerHTML = html
    this.el.classList.remove('hidden')
    this.submit.onclick = onSubmit
  },
  close() {
    this.el.classList.add('hidden')
  }
}

qs('modalClose').addEventListener('click', () => modal.close())
qs('modalCancel').addEventListener('click', () => modal.close())

function openProductModal() {
  modal.open(
    '新增商品',
    `
    <div class="form-grid">
      <label>SKU</label><input id="mSku" />
      <label>名称</label><input id="mName" />
      <label>品牌</label><input id="mBrand" />
      <label>型号</label><input id="mModel" />
      <label>单位</label><input id="mUnit" placeholder="台/件" />
      <label>SN追踪</label>
      <select id="mTrack">
        <option value="false">否</option>
        <option value="true">是</option>
      </select>
      <label>保修(月)</label><input id="mWarranty" type="number" />
    </div>
    `,
    async () => {
      await request('/api/products', {
        method: 'POST',
        body: JSON.stringify({
          sku: qs('mSku').value,
          name: qs('mName').value,
          brand: qs('mBrand').value || null,
          model: qs('mModel').value || null,
          unit: qs('mUnit').value || null,
          track_sn: qs('mTrack').value === 'true',
          warranty_months: qs('mWarranty').value ? Number(qs('mWarranty').value) : null,
          is_active: true
        })
      })
      modal.close()
      await loadProducts()
      await refreshStats()
    }
  )
}

function openWarehouseModal() {
  modal.open(
    '新增仓库',
    `
    <div class="form-grid">
      <label>编码</label><input id="mCode" />
      <label>名称</label><input id="mName" />
      <label>位置</label><input id="mLocation" />
    </div>
    `,
    async () => {
      await request('/api/warehouses', {
        method: 'POST',
        body: JSON.stringify({
          code: qs('mCode').value || null,
          name: qs('mName').value,
          location: qs('mLocation').value || null
        })
      })
      modal.close()
      await loadWarehouses()
      await refreshStats()
    }
  )
}

function openPartnerModal() {
  modal.open(
    '新增往来单位',
    `
    <div class="form-grid">
      <label>类型</label>
      <select id="mType">
        <option value="CUSTOMER">客户</option>
        <option value="SUPPLIER">供应商</option>
      </select>
      <label>名称</label><input id="mName" />
      <label>电话</label><input id="mPhone" />
      <label>地址</label><input id="mAddress" />
    </div>
    `,
    async () => {
      await request('/api/partners', {
        method: 'POST',
        body: JSON.stringify({
          type: qs('mType').value,
          name: qs('mName').value,
          phone: qs('mPhone').value || null,
          address: qs('mAddress').value || null
        })
      })
      modal.close()
      await loadPartners()
      await refreshStats()
    }
  )
}

function setupMenu() {
  qsa('.menu-item').forEach((btn) => {
    btn.addEventListener('click', () => {
      showView(btn.dataset.view)
      if (btn.dataset.view === 'products') loadProducts()
      if (btn.dataset.view === 'warehouses') loadWarehouses()
      if (btn.dataset.view === 'partners') loadPartners()
      if (btn.dataset.view === 'docs') loadDocs()
      if (btn.dataset.view === 'sns') loadSns()
    })
  })
  qsa('[data-jump]').forEach((btn) => {
    btn.addEventListener('click', () => {
      showView(btn.dataset.jump)
      if (btn.dataset.jump === 'products') loadProducts()
      if (btn.dataset.jump === 'warehouses') loadWarehouses()
      if (btn.dataset.jump === 'partners') loadPartners()
      if (btn.dataset.jump === 'docs') loadDocs()
      if (btn.dataset.jump === 'sns') loadSns()
    })
  })
}

qs('loginBtn').addEventListener('click', login)
qs('logoutBtn').addEventListener('click', logout)
qs('btnLoadProducts').addEventListener('click', loadProducts)
qs('btnLoadWarehouses').addEventListener('click', loadWarehouses)
qs('btnLoadPartners').addEventListener('click', loadPartners)
qs('btnLoadDocs').addEventListener('click', loadDocs)
qs('btnLoadSns').addEventListener('click', loadSns)
qs('btnAddProduct').addEventListener('click', openProductModal)
qs('btnAddWarehouse').addEventListener('click', openWarehouseModal)
qs('btnAddPartner').addEventListener('click', openPartnerModal)

setupMenu()

if (state.token) {
  loadMe().then(() => {
    showView('dashboard')
    refreshStats()
  })
} else {
  showView('auth')
}
