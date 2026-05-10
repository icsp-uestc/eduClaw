// EduClaw — Chat UI

const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const chatMessages = document.getElementById('chat-messages');
const skillTrigger = document.getElementById('skill-trigger');
const skillPopover = document.getElementById('skill-popover');
const skillPopoverList = document.getElementById('skill-popover-list');
const skillSelected = document.getElementById('skill-selected');
const welcomeSkills = document.getElementById('welcome-skills');
const convList = document.getElementById('conv-list');
const newChatBtn = document.getElementById('new-chat-btn');
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const overlay = document.getElementById('overlay');
const chatTitle = document.getElementById('chat-title');

let currentSkill = null;
let currentConvId = null;
let conversations = {};
let convOrder = [];
let skills = {};
let llmConnected = false;
let llmModel = null;
let pendingPermission = null; // {pending_id, skill_id, message}

const SKILL_ICONS = {};
const SKILL_NAMES = {};

// Populated from API response
function updateSkillMaps(skillsObj) {
  Object.entries(skillsObj).forEach(([id, s]) => {
    SKILL_ICONS[id] = s.icon;
    SKILL_NAMES[id] = s.name;
  });
}

async function api(url, opts = {}) {
  const res = await fetch(url, opts);
  return res.json();
}

// ===== Init =====
async function init() {
  await checkStatus();
  await loadUser();
  await loadSkills();
  await createNewConv();
  buildPopover();
  document.addEventListener('click', onGlobalClick);
}

// ===== User Management =====
async function loadUser() {
  const { data } = await api('/api/auth/status');
  if (data) {
    document.getElementById('user-name').textContent = data.name;
    document.getElementById('user-badge').title = `${data.name} (${data.student_id})\n${data.major} ${data.grade}\n点击切换用户`;
  }
}

// Click user badge to show user switcher
const userBadge = document.getElementById('user-badge');
let userPopup = null;

userBadge.addEventListener('click', async e => {
  e.stopPropagation();
  if (userPopup) { userPopup.remove(); userPopup = null; return; }

  const { data: users } = await api('/api/auth/users');
  userPopup = document.createElement('div');
  userPopup.className = 'user-popup open';
  userPopup.style.position = 'absolute';
  userPopup.style.top = (userBadge.offsetTop + userBadge.offsetHeight + 4) + 'px';
  userPopup.style.right = '8px';

  // Find current user
  const { data: current } = await api('/api/auth/status');

  users.forEach(u => {
    const item = document.createElement('button');
    item.className = 'user-popup-item' + (current && u.student_id === current.student_id ? ' active' : '');
    item.innerHTML = `\u{1F464} ${u.name} <span style="color:#9ca3af;font-size:11px">${u.student_id}</span>`;
    item.addEventListener('click', async () => {
      await api('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: u.student_id }),
      });
      userPopup.remove(); userPopup = null;
      loadUser();
      createNewConv();
    });
    userPopup.appendChild(item);
  });

  userBadge.parentElement.style.position = 'relative';
  userBadge.parentElement.appendChild(userPopup);

  document.addEventListener('click', function closePopup(ev) {
    if (userPopup && !userPopup.contains(ev.target) && ev.target !== userBadge && !userBadge.contains(ev.target)) {
      userPopup.remove(); userPopup = null;
      document.removeEventListener('click', closePopup);
    }
  });
});

async function checkStatus() {
  try {
    const { data } = await api('/api/status');
    llmConnected = data.llm_available;
    llmModel = data.model;
    if (data.last_error) {
      console.log('LLM last error:', data.last_error);
    }
  } catch (e) {
    llmConnected = false;
  }
  updateStatusUI();
}

function updateStatusUI() {
  const el = document.getElementById('llm-status');
  const txt = document.getElementById('llm-status-text');
  if (!el) return;
  if (llmConnected) {
    el.className = 'llm-status connected';
    el.title = 'LLM 已连接: ' + (llmModel || '') + '\n点击测试连接';
    if (txt) txt.textContent = '模型已连接';
  } else {
    el.className = 'llm-status disconnected';
    el.title = 'LLM 未连接\n点击测试连接';
    if (txt) txt.textContent = '技能模式';
  }
}

// Click status to test LLM connection
document.getElementById('llm-status').addEventListener('click', async () => {
  const el = document.getElementById('llm-status');
  const txt = document.getElementById('llm-status-text');
  el.classList.add('testing');
  if (txt) txt.textContent = '测试中…';

  try {
    const resp = await api('/api/status/test', { method: 'POST' });
    if (resp.ok) {
      llmConnected = true;
      if (txt) txt.textContent = '模型已连接';
      addSystemMsg('模型连接正常 ✓ — ' + (resp.data?.reply || '').slice(0, 50));
    } else {
      llmConnected = false;
      if (txt) txt.textContent = '连接失败';
      addSystemMsg('模型连接失败: ' + (resp.error || '未知错误'));
    }
  } catch (e) {
    llmConnected = false;
    if (txt) txt.textContent = '连接失败';
    addSystemMsg('模型连接失败: ' + e.message);
  }

  updateStatusUI();
  el.classList.remove('testing');
});

function addSystemMsg(text) {
  renderMessage('system', text);
  scrollBottom();
}

async function loadSkills() {
  const { data } = await api('/api/skills');
  if (!data) return;
  skills = data;
  updateSkillMaps(data);
  buildWelcome();
}

function buildWelcome() {
  const el = document.getElementById('welcome-skills');
  if (!el) return;
  el.innerHTML = '';
  Object.entries(skills).forEach(([id, skill]) => {
    const btn = document.createElement('button');
    btn.className = 'welcome-skill';
    btn.innerHTML = `${SKILL_ICONS[id] || ''} ${skill.name}`;
    btn.title = skill.desc;
    btn.addEventListener('click', () => {
      selectSkill(id);
      chatInput.focus();
    });
    el.appendChild(btn);
  });
}

function buildPopover() {
  skillPopoverList.innerHTML = '';
  Object.entries(skills).forEach(([id, skill]) => {
    const item = document.createElement('button');
    item.className = 'skill-popover-item';
    item.innerHTML = `
      <span class="popover-icon">${SKILL_ICONS[id] || ''}</span>
      <span class="popover-name">${skill.name}</span>
      <span class="popover-desc">${skill.desc}</span>`;
    item.addEventListener('click', () => {
      selectSkill(id);
      closePopover();
    });
    skillPopoverList.appendChild(item);
  });

  const divider = document.createElement('div');
  divider.className = 'skill-popover-divider';
  skillPopoverList.appendChild(divider);

  const clearBtn = document.createElement('button');
  clearBtn.className = 'skill-popover-clear';
  clearBtn.innerHTML = '\u2715 清除技能';
  clearBtn.addEventListener('click', () => {
    clearSkill();
    closePopover();
  });
  skillPopoverList.appendChild(clearBtn);
}

function updatePopoverActive() {
  skillPopoverList.querySelectorAll('.skill-popover-item').forEach(item => {
    item.classList.toggle('active', item.dataset.skill === currentSkill);
  });
}

// ===== Popover toggle =====
function togglePopover() {
  const isOpen = skillPopover.classList.contains('open');
  if (isOpen) {
    closePopover();
  } else {
    skillPopover.classList.add('open');
    updatePopoverActive();
  }
}

function closePopover() {
  skillPopover.classList.remove('open');
}

function onGlobalClick(e) {
  if (!skillPopover.classList.contains('open')) return;
  if (!skillPopover.contains(e.target) && e.target !== skillTrigger && !skillTrigger.contains(e.target)) {
    closePopover();
  }
}

// ===== Skill selection =====
function selectSkill(id) {
  if (currentSkill === id) {
    clearSkill();
    return;
  }
  currentSkill = id;
  updateSkillUI();
}

function clearSkill() {
  currentSkill = null;
  updateSkillUI();
}

function updateSkillUI() {
  // Trigger button state
  skillTrigger.classList.toggle('has-skill', !!currentSkill);

  // Selected tag
  skillSelected.innerHTML = '';
  if (currentSkill && skills[currentSkill]) {
    const tag = document.createElement('span');
    tag.className = 'skill-tag';
    tag.innerHTML = `${SKILL_ICONS[currentSkill] || ''} ${skills[currentSkill].name}<button class="tag-remove">\u00d7</button>`;
    tag.querySelector('.tag-remove').addEventListener('click', e => {
      e.stopPropagation();
      clearSkill();
    });
    skillSelected.appendChild(tag);
    chatInput.placeholder = `使用「${skills[currentSkill].name}」技能…`;
  } else {
    chatInput.placeholder = '输入你的问题…';
  }

  updatePopoverActive();
}

// ===== Conversation Management =====
async function createNewConv() {
  try { await api('/api/chat/clear', { method: 'POST' }); } catch(e) {}
  const { data } = await api('/api/conversations', { method: 'POST' });
  currentConvId = data.id;
  conversations[currentConvId] = { id: currentConvId, title: '新对话', messages: [], updated: '' };
  convOrder.unshift(currentConvId);
  chatMessages.innerHTML = `
    <div class="welcome">
      <div class="welcome-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
        </svg>
      </div>
      <h2>你好，我是 EduClaw</h2>
      <p>${llmConnected ? '模型已连接，你可以自由提问。' : '当前以技能模式运行。'}<br>我可以帮你检索课程、规划学习路径、生成能力画像、检测学业预警。</p>
      <div class="welcome-skills" id="welcome-skills"></div>
    </div>`;
  buildWelcome();
  renderConvList();
  clearSkill();
  chatTitle.textContent = 'EduClaw';
  chatInput.value = '';
  chatInput.style.height = 'auto';
  chatInput.focus();
  closeSidebar();
}

async function loadConversation(id) {
  currentConvId = id;
  const conv = conversations[id];
  if (!conv) return;
  chatTitle.textContent = conv.title;
  chatMessages.innerHTML = '';
  clearSkill();

  if (!conv.messages || conv.messages.length === 0) {
    chatMessages.innerHTML = `
      <div class="welcome">
        <div class="welcome-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <h2>开始新对话</h2>
        <p>选择一个技能或直接输入问题。</p>
        <div class="welcome-skills" id="welcome-skills"></div>
      </div>`;
    buildWelcome();
  } else {
    conv.messages.forEach(m => renderMessage(m.role, m.text, m.skill));
  }
  renderConvList();
  scrollBottom();
  closeSidebar();
}

async function deleteConversation(id) {
  await api(`/api/conversations/${id}`, { method: 'DELETE' });
  delete conversations[id];
  convOrder = convOrder.filter(c => c !== id);
  if (currentConvId === id) {
    if (convOrder.length > 0) {
      await loadConversation(convOrder[0]);
    } else {
      await createNewConv();
    }
  }
  renderConvList();
}

function renderConvList() {
  convList.innerHTML = '';
  if (convOrder.length === 0) {
    convList.innerHTML = '<div class="conv-empty">暂无历史对话</div>';
    return;
  }
  convOrder.forEach(id => {
    const conv = conversations[id];
    if (!conv) return;
    const div = document.createElement('div');
    div.className = 'conv-item' + (id === currentConvId ? ' active' : '');
    div.innerHTML = `
      <span class="conv-title">${conv.title || '新对话'}</span>
      <button class="conv-delete" title="删除">\u00d7</button>`;
    div.querySelector('.conv-title').addEventListener('click', () => loadConversation(id));
    div.querySelector('.conv-delete').addEventListener('click', e => { e.stopPropagation(); deleteConversation(id); });
    convList.appendChild(div);
  });
}

// ===== Messaging =====
function renderMessage(role, text, skill, chartData) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  const avatarIcons = { user: '\u{1F464}', assistant: '\u{1F989}', system: '' };
  const avatar = avatarIcons[role] || '';
  let badgeHtml = '';
  if (skill && role === 'assistant') {
    badgeHtml = `<span class="skill-badge ${skill}">${SKILL_NAMES[skill] || skill}</span>\n`;
  }

  let chartHtml = '';
  if (chartData && chartData.labels && chartData.values) {
    chartHtml = renderRadarChart(chartData);
  }

  let actionHtml = '';
  if (role === 'assistant') {
    const { cleanText, actions } = parseActions(text);
    if (actions.length > 0) {
      text = cleanText;
      actionHtml = renderActions(actions);
    }
  }

  div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-body">${badgeHtml}${renderContent(text, role)}${actionHtml}${chartHtml}</div>`;
  chatMessages.appendChild(div);
}

// ===== Radar Chart (Chart.js) =====
function renderRadarChart(data) {
  const labels = data.labels || [];
  const values = data.values || [];
  const pointColors = data.pointColors || [];
  const maxScore = data.maxScore || 100;
  if (labels.length < 3) return '';

  const canvasId = 'radar-' + Math.random().toString(36).slice(2, 8);

  // Defer Chart.js rendering to next frame so DOM is ready
  requestAnimationFrame(() => {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    new Chart(ctx, {
      type: 'radar',
      data: {
        labels: labels,
        datasets: [{
          label: '能力得分',
          data: values,
          backgroundColor: 'rgba(37, 99, 235, 0.15)',
          borderColor: 'rgb(37, 99, 235)',
          borderWidth: 2,
          pointBackgroundColor: pointColors,
          pointBorderColor: pointColors,
          pointRadius: 5,
          pointHoverRadius: 7,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          r: {
            beginAtZero: false,
            min: 0,
            max: maxScore,
            ticks: { stepSize: 20, backdropColor: 'transparent', font: { size: 10 } },
            pointLabels: { font: { size: 12, weight: '500' }, color: '#374151' },
            grid: { color: '#e5e7eb' },
            angleLines: { color: '#e5e7eb' },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(ctx) { return '得分: ' + ctx.raw + ' / ' + maxScore; }
            }
          },
        },
      },
    });
  });

  return `<div class="radar-chart"><canvas id="${canvasId}"></canvas></div>`;
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderContent(text, role) {
  if (role === 'assistant' && typeof marked !== 'undefined') {
    return marked.parse(text, {breaks: true, gfm: true});
  }
  return escapeHtml(text);
}

function showTyping() {
  const div = document.createElement('div');
  div.className = 'msg assistant typing-msg';
  div.innerHTML = `
    <div class="msg-avatar">\u{1F989}</div>
    <div class="msg-body"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
  chatMessages.appendChild(div);
  scrollBottom();
  return div;
}

function removeTyping(el) {
  if (el && el.parentNode) el.remove();
}

function scrollBottom() {
  requestAnimationFrame(() => {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  });
}

function storeMessage(role, text, skill) {
  if (!currentConvId || !conversations[currentConvId]) return;
  const conv = conversations[currentConvId];
  conv.messages.push({ role, text, skill });
  if (conv.messages.length === 1 && role === 'user') {
    conv.title = text.slice(0, 30) + (text.length > 30 ? '\u2026' : '');
    chatTitle.textContent = conv.title;
  }
  conv.updated = new Date().toISOString();
  renderConvList();
}

// ===== Send =====
async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text && !currentSkill) return;
  if (sendBtn.disabled) return;

  const skill = currentSkill;
  const msgText = text || (skill ? '执行' : '');

  const welcome = chatMessages.querySelector('.welcome');
  if (welcome) welcome.remove();

  renderMessage('user', msgText);
  storeMessage('user', msgText, null);
  chatInput.value = '';
  chatInput.style.height = 'auto';
  scrollBottom();

  sendBtn.disabled = true;
  const typing = showTyping();

    try {
    const resp = await api('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msgText, skill, conv_id: currentConvId }),
    });
    removeTyping(typing);

    if (resp.needs_permission) {
      pendingPermission = {
        pending_id: resp.pending_id,
        skill_id: resp.action_id,
        message: msgText,
      };
      showPermissionDialog(resp.action_name, resp.action_desc);
      sendBtn.disabled = false;
      chatInput.focus();
      return;
    }

    const { ok, data, skill: respSkill, chart_data, mode } = resp;
    if (ok) {
      const modeTag = mode === 'llm' ? '' : (mode === 'direct' ? ' [直接]' : '');
      renderMessage('assistant', (data || '(无返回内容)') + modeTag, respSkill, chart_data);
      storeMessage('assistant', data || '', respSkill);
      if (respSkill) clearSkill();
    } else {
      renderMessage('system', '错误: ' + (data || '未知'));
    }
  } catch (e) {
    removeTyping(typing);
    renderMessage('system', '请求失败: ' + e.message);
  }

  sendBtn.disabled = false;
  scrollBottom();
  chatInput.focus();
}

// ===== Permission Dialog =====
const permOverlay = document.getElementById('perm-overlay');
const permDialog = document.getElementById('perm-dialog');
const permDialogTitle = document.getElementById('perm-dialog-title');
const permDialogDesc = document.getElementById('perm-dialog-desc');
const permAllowBtn = document.getElementById('perm-allow-btn');
const permDenyBtn = document.getElementById('perm-deny-btn');

function showPermissionDialog(actionName, actionDesc) {
  permDialogTitle.textContent = `权限确认 — ${actionName}`;
  permDialogDesc.textContent = actionDesc || '是否允许执行此操作？';
  permDialog.classList.add('visible');
  permOverlay.classList.add('visible');
}

function hidePermissionDialog() {
  permDialog.classList.remove('visible');
  permOverlay.classList.remove('visible');
}

permAllowBtn.addEventListener('click', async () => {
  if (!pendingPermission) return;
  const { pending_id, skill_id, message } = pendingPermission;
  pendingPermission = null;
  hidePermissionDialog();

  // Re-show typing and call approve
  const typing = showTyping();
  try {
    const resp = await api('/api/permissions/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pending_id, skill_id, message }),
    });
    removeTyping(typing);
    if (resp.ok) {
      renderMessage('assistant', resp.data || '操作已完成', resp.skill);
      storeMessage('assistant', resp.data || '', resp.skill);
      if (resp.chart_data) {
        const msgEl = chatMessages.lastElementChild;
        if (msgEl) {
          msgEl.querySelector('.msg-body').innerHTML += renderRadarChart(resp.chart_data);
        }
      }
      if (resp.skill) clearSkill();
    } else {
      renderMessage('system', '执行失败: ' + (resp.error || '未知错误'));
    }
  } catch (e) {
    removeTyping(typing);
    renderMessage('system', '请求失败: ' + e.message);
  }
  scrollBottom();
});

permDenyBtn.addEventListener('click', async () => {
  if (!pendingPermission) return;
  const { pending_id } = pendingPermission;
  pendingPermission = null;
  hidePermissionDialog();
  await api('/api/permissions/deny', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pending_id }),
  });
  renderMessage('system', '操作已被拒绝。');
  scrollBottom();
});

// ===== Sidebar toggle =====
function toggleSidebar() {
  sidebar.classList.toggle('open');
  overlay.classList.toggle('visible');
}
function closeSidebar() {
  sidebar.classList.remove('open');
  overlay.classList.remove('visible');
}

// ===== Event listeners =====
skillTrigger.addEventListener('click', e => { e.stopPropagation(); togglePopover(); });
sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
chatInput.addEventListener('input', () => {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
});
newChatBtn.addEventListener('click', createNewConv);
sidebarToggle.addEventListener('click', toggleSidebar);
overlay.addEventListener('click', closeSidebar);

// ===== Init =====
init();

// ===== Task Panel =====
const taskPanel = document.getElementById('task-panel');
const taskOverlay = document.getElementById('task-overlay');
const taskToggleBtn = document.getElementById('task-toggle-btn');
const taskCloseBtn = document.getElementById('task-panel-close');
const taskList = document.getElementById('task-list');
const taskLog = document.getElementById('task-log');
const taskBadge = document.getElementById('task-badge');
const taskTypeSelect = document.getElementById('task-type');
const taskScheduledOpts = document.getElementById('task-scheduled-opts');
const taskTriggerOpts = document.getElementById('task-trigger-opts');
const taskCondition = document.getElementById('task-condition');

function openTaskPanel() {
  taskPanel.classList.add('open');
  taskOverlay.classList.add('visible');
  taskToggleBtn.classList.add('active');
  loadTasks();
  loadConditions();
  loadTaskLog();
}
function closeTaskPanel() {
  taskPanel.classList.remove('open');
  taskOverlay.classList.remove('visible');
  taskToggleBtn.classList.remove('active');
}

taskToggleBtn.addEventListener('click', () => {
  taskPanel.classList.contains('open') ? closeTaskPanel() : openTaskPanel();
});
taskCloseBtn.addEventListener('click', closeTaskPanel);
taskOverlay.addEventListener('click', closeTaskPanel);

taskTypeSelect.addEventListener('change', () => {
  const isTrigger = taskTypeSelect.value === 'trigger';
  taskScheduledOpts.style.display = isTrigger ? 'none' : 'block';
  taskTriggerOpts.style.display = isTrigger ? 'block' : 'none';
});

document.getElementById('task-create-btn').addEventListener('click', async () => {
  const name = document.getElementById('task-name').value.trim();
  const prompt = document.getElementById('task-prompt').value.trim();
  if (!name || !prompt) return;
  const ttype = taskTypeSelect.value;
  const body = { type: ttype, name, prompt };
  if (ttype === 'scheduled') {
    body.interval = parseInt(document.getElementById('task-interval').value) || 3600;
  } else {
    body.condition_id = taskCondition.value;
    body.cooldown = parseInt(document.getElementById('task-cooldown').value) || 86400;
  }
  const { ok } = await api('/api/tasks', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (ok) {
    document.getElementById('task-name').value = '';
    document.getElementById('task-prompt').value = '';
    loadTasks();
  }
});

async function loadTasks() {
  const { data } = await api('/api/tasks');
  taskList.innerHTML = '';
  if (!data || data.length === 0) {
    taskList.innerHTML = '<div class="task-empty">暂无任务</div>';
    taskBadge.style.display = 'none';
    return;
  }
  taskBadge.style.display = 'flex';
  taskBadge.textContent = data.length;
  data.forEach(t => {
    const div = document.createElement('div');
    div.className = 'task-item';
    const typeLabel = t.type === 'scheduled' ? '定时' : '触发';
    const typeClass = t.type === 'scheduled' ? 'task-type-scheduled' : 'task-type-trigger';
    div.innerHTML = `
      <div class="task-item-header">
        <span class="task-item-name">${t.name}</span>
        <span class="task-item-type ${typeClass}">${typeLabel}</span>
      </div>
      <div class="task-item-meta">
        <span>执行: ${t.execution_count}次</span>
        ${t.last_run_at ? `<span>上次: ${t.last_run_at.slice(11,19)}</span>` : ''}
      </div>
      <div class="task-item-actions">
        <button class="task-delete-btn" data-id="${t.task_id}">删除</button>
      </div>`;
    div.querySelector('.task-delete-btn').addEventListener('click', async () => {
      await api(`/api/tasks/${t.task_id}`, { method: 'DELETE' });
      loadTasks();
    });
    taskList.appendChild(div);
  });
}

async function loadConditions() {
  const { data } = await api('/api/tasks/conditions');
  taskCondition.innerHTML = '';
  if (data) {
    Object.entries(data).forEach(([id, desc]) => {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = id;
      opt.title = desc;
      taskCondition.appendChild(opt);
    });
  }
}

async function loadTaskLog() {
  const { data } = await api('/api/tasks/log');
  taskLog.innerHTML = '';
  if (!data || data.length === 0) {
    taskLog.innerHTML = '<div class="task-empty">暂无日志</div>';
    return;
  }
  data.reverse().forEach(entry => {
    const div = document.createElement('div');
    div.className = 'task-log-entry';
    div.innerHTML = `
      <div class="log-time">${entry.time.slice(11, 19)}</div>
      <div class="log-task">${entry.task_name} (${entry.task_type})</div>
      <div class="log-result">${(entry.result || '').slice(0, 150)}</div>`;
    taskLog.appendChild(div);
  });
}

// Poll for task updates every 30s
setInterval(() => { if (document.visibilityState === 'visible') loadTasks(); }, 30000);

// ===== Interactive Actions =====
function parseActions(text) {
  const actions = [];
  const regex = /<action\s+(.*?)>([\s\S]*?)<\/action>/g;
  let cleanText = text;
  let m;
  while ((m = regex.exec(text)) !== null) {
    const attrsStr = m[1];
    const body = m[2].trim();
    const attrs = {};
    for (const am of attrsStr.matchAll(/(\w+)="([^"]*)"/g)) {
      attrs[am[1]] = am[2];
    }
    const action = { type: attrs.type || '', id: attrs.id || '', body };
    if (action.type === 'input') {
      action.prompt = attrs.prompt || '请输入';
    } else if (action.type === 'select') {
      action.options = parseTable(body);
    }
    actions.push(action);
  }
  cleanText = cleanText.replace(regex, '').trim();
  return { cleanText, actions };
}

function parseTable(text) {
  const lines = text.trim().split('\n').filter(l => l.trim() && !l.trim().startsWith('|-'));
  if (lines.length < 2) return [];
  const headers = lines[0].replace(/^\||\|$/g, '').split('|').map(h => h.trim());
  const opts = [];
  for (const line of lines.slice(1)) {
    const cells = line.replace(/^\||\|$/g, '').split('|').map(c => c.trim());
    if (cells.length >= 2) {
      const opt = { value: cells[0] };
      for (let i = 1; i < headers.length && i < cells.length; i++) {
        opt[headers[i]] = cells[i];
      }
      opts.push(opt);
    }
  }
  return opts;
}

function renderActions(actions) {
  let html = '';
  actions.forEach(a => {
    if (a.type === 'select') {
      html += '<div class="action-select">';
      if (a.id) html += `<div class="action-label">请选择:</div>`;
      html += '<div class="action-buttons">';
      a.options.forEach(opt => {
        const label = opt['名称'] || opt['课程'] || opt['选项'] || opt.value;
        const desc = opt['说明'] || opt['难度'] || opt['学分'] || '';
        html += `<button class="action-btn" data-value="${opt.value}" data-action-id="${a.id}">${label}${desc ? '<small>' + desc + '</small>' : ''}</button>`;
      });
      html += '</div></div>';
    } else if (a.type === 'input') {
      html += `<div class="action-input" data-action-id="${a.id}">
        <input type="text" class="action-input-field" placeholder="${a.prompt || '请输入'}" data-action-id="${a.id}">
        <button class="action-input-send" data-action-id="${a.id}">发送</button>
      </div>`;
    }
  });

  // Bind events after rendering
  setTimeout(() => {
    document.querySelectorAll('.action-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const value = btn.dataset.value;
        document.querySelectorAll('.action-btn').forEach(b => { b.disabled = true; b.style.opacity = '.6'; });
        sendActionMessage(value);
      });
    });
    document.querySelectorAll('.action-input-send').forEach(btn => {
      btn.addEventListener('click', () => {
        const input = document.querySelector(`.action-input-field[data-action-id="${btn.dataset.actionId}"]`);
        if (input && input.value.trim()) {
          input.disabled = true;
          btn.disabled = true;
          sendActionMessage(input.value.trim());
        }
      });
    });
    document.querySelectorAll('.action-input-field').forEach(input => {
      input.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
          const btn = document.querySelector(`.action-input-send[data-action-id="${input.dataset.actionId}"]`);
          if (btn && input.value.trim()) {
            input.disabled = true;
            btn.disabled = true;
            sendActionMessage(input.value.trim());
          }
        }
      });
    });
  }, 50);

  return html;
}

async function sendActionMessage(value) {
  renderMessage('user', value);
  storeMessage('user', value, null);
  scrollBottom();

  sendBtn.disabled = true;
  const typing = showTyping();

  try {
    const resp = await api('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: value, skill: currentSkill, conv_id: currentConvId }),
    });
    removeTyping(typing);
    if (resp.needs_permission) {
      pendingPermission = { pending_id: resp.pending_id, skill_id: resp.action_id, message: value };
      showPermissionDialog(resp.action_name, resp.action_desc);
      sendBtn.disabled = false;
      return;
    }
    const { ok, data, skill: respSkill, chart_data, mode } = resp;
    if (ok) {
      const modeTag = mode === 'llm' ? '' : (mode === 'direct' ? ' [直接]' : '');
      renderMessage('assistant', (data || '(无返回内容)') + modeTag, respSkill, chart_data);
      storeMessage('assistant', data || '', respSkill);
      if (respSkill) clearSkill();
    } else {
      renderMessage('system', '错误: ' + (data || '未知'));
    }
  } catch (e) {
    removeTyping(typing);
    renderMessage('system', '请求失败: ' + e.message);
  }
  sendBtn.disabled = false;
  scrollBottom();
}
