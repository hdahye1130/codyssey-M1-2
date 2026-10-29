const API = (window.SOLAR_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const $ = id => document.getElementById(id);
const state = { conversationId: null, data: [], page: 0, loading: false };
$('token').value = sessionStorage.getItem('solarToken') || '';

function notice(message) { $('notice').textContent = message; $('notice').hidden = !message; }
function num(x) { return Number(x).toLocaleString('ko-KR', { maximumFractionDigits: 1 }); }
async function request(path, options = {}) {
  const token = $('token').value.trim();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['X-App-Token'] = token;
  let response;
  try { response = await fetch(`${API}${path}`, { ...options, headers }); }
  catch (_) { throw new Error('백엔드 서버에 연결할 수 없습니다. API URL, Render 상태, CORS를 확인해 주세요.'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `요청 오류 (${response.status})`);
  return body;
}
async function refreshSummary() {
  try {
    const s = await request('/api/data/summary');
    $('stat-count').textContent = num(s.count);
    $('stat-avg').textContent = s.count ? num(s.average_mwh) : '—';
    $('stat-max').textContent = s.count ? num(s.maximum.value_mwh) : '—';
    $('stat-max-date').textContent = s.count ? s.maximum.date : 'MWh';
    $('stat-trend').textContent = s.recent_trend || '—';
    $('connection').textContent = '● 서버 연결됨';
    $('connection').style.color = '#a1dfba';
  } catch (e) { $('connection').textContent = '● 연결 오류'; $('connection').style.color = '#fecb83'; notice(e.message); }
}
function switchTab(tab) {
  document.querySelectorAll('.page').forEach(el => el.hidden = el.id !== 'tab-' + tab);
  document.querySelectorAll('.nav').forEach(el => el.classList.toggle('active', el.dataset.tab === tab));
  if (tab === 'data') refreshData();
  if (tab === 'history') refreshHistory();
}
document.querySelectorAll('.nav').forEach(el => el.addEventListener('click', () => switchTab(el.dataset.tab)));
$('save-token').onclick = () => { sessionStorage.setItem('solarToken', $('token').value.trim()); notice(''); refreshSummary(); };

function addMessage(role, content, extra = '') {
  const box = $('messages');
  const intro = box.querySelector('.intro');
  if (intro) intro.remove();
  const el = document.createElement('div');
  el.className = `message ${role} ${extra}`;
  el.textContent = content;
  box.append(el);
  box.scrollTop = box.scrollHeight;
  return el;
}
function clearChat() {
  state.conversationId = null;
  $('messages').replaceChildren();
  addMessage('assistant', '새 대화입니다. 2025년 태양광 발전량에 대해 무엇이 궁금하신가요?');
}
$('new-chat').onclick = clearChat;
document.querySelectorAll('.suggest').forEach(button => button.onclick = () => { $('question').value = button.textContent; $('question').focus(); });
$('chat-form').onsubmit = async event => {
  event.preventDefault();
  if (state.loading) return;
  const question = $('question').value.trim();
  if (!question) return;
  state.loading = true; $('ask').disabled = true;
  addMessage('user', question); $('question').value = '';
  const pending = addMessage('assistant', '데이터 요약을 확인하고 AI 답변을 생성하고 있습니다…', 'loading');
  notice('');
  try {
    const r = await request('/api/chat', { method: 'POST', body: JSON.stringify({ question, conversation_id: state.conversationId }) });
    pending.textContent = r.answer;
    pending.classList.remove('loading');
    state.conversationId = r.conversation_id;
  } catch (e) { pending.textContent = '답변 생성 실패: ' + e.message; pending.classList.remove('loading'); notice(e.message); }
  finally { state.loading = false; $('ask').disabled = false; }
};
$('question').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('chat-form').requestSubmit(); } });

function renderData() {
  const body = $('data-body'); body.replaceChildren();
  const chunk = state.data.slice(state.page * 15, (state.page + 1) * 15);
  if (!chunk.length) { const tr = body.insertRow(); tr.insertCell().colSpan = 4; tr.cells[0].textContent = '표시할 데이터가 없습니다.'; }
  for (const row of chunk) {
    const tr = body.insertRow();
    tr.insertCell().textContent = row.date;
    tr.insertCell().textContent = num(row.value);
    tr.insertCell().textContent = `${row.source || ''} · ${row.memo || ''}`;
    const actions = tr.insertCell();
    const edit = document.createElement('button'); edit.textContent = '수정';
    edit.onclick = async () => {
      const proposed = prompt(`${row.date}의 발전량 (MWh)`, row.value);
      if (proposed === null) return;
      const value = Number(proposed);
      if (!proposed.trim() || !Number.isFinite(value) || value < 0) { notice('0 이상의 유효한 숫자를 입력하세요.'); return; }
      const memo = prompt('수정 메모', row.memo || '');
      if (memo === null) return;
      try { await request('/api/data/' + encodeURIComponent(row.id), { method: 'PUT', body: JSON.stringify({ value, memo }) }); await refreshData(); await refreshSummary(); notice('데이터를 수정했습니다.'); }
      catch (e) { notice(e.message); }
    };
    const del = document.createElement('button'); del.textContent = '삭제';
    del.onclick = async () => {
      if (!confirm(`${row.date}의 발전량 기록을 삭제하시겠습니까?`)) return;
      try { await request('/api/data/' + encodeURIComponent(row.id), { method: 'DELETE' }); await refreshData(); await refreshSummary(); notice('기록을 삭제했습니다.'); }
      catch (e) { notice(e.message); }
    };
    actions.append(edit, del);
  }
  const totalPages = Math.max(1, Math.ceil(state.data.length / 15));
  $('data-page').textContent = `${state.page + 1} / ${totalPages} 페이지 (총 ${state.data.length}개)`;
  $('prev-data').disabled = state.page === 0;
  $('next-data').disabled = state.page + 1 >= totalPages;
}
async function refreshData() {
  try { state.data = await request('/api/data'); state.page = Math.min(state.page, Math.max(0, Math.ceil(state.data.length / 15) - 1)); renderData(); }
  catch (e) { notice(e.message); }
}
$('reload-data').onclick = refreshData;
$('prev-data').onclick = () => { state.page--; renderData(); };
$('next-data').onclick = () => { state.page++; renderData(); };
$('data-form').onsubmit = async event => {
  event.preventDefault();
  try {
    await request('/api/data', { method: 'POST', body: JSON.stringify({ date: $('date').value, value: Number($('value').value), memo: $('memo').value }) });
    $('data-form').reset(); await refreshData(); await refreshSummary(); notice('새로운 데이터를 추가했습니다.');
  } catch (e) { notice(e.message); }
};
async function refreshHistory() {
  const box = $('history-items'); box.replaceChildren();
  try {
    const rows = await request('/api/conversations');
    if (!rows.length) { box.textContent = '저장된 대화가 없습니다.'; return; }
    for (const record of rows) {
      const wrapper = document.createElement('div'); wrapper.className = 'history-item';
      const info = document.createElement('div');
      const name = document.createElement('strong'); name.textContent = record.title;
      const sub = document.createElement('small'); sub.textContent = `${record.message_count}개 메시지 · ${new Date(record.updated_at).toLocaleString('ko-KR')}`;
      info.append(name, sub);
      const controls = document.createElement('div');
      const load = document.createElement('button'); load.textContent = '불러오기';
      load.onclick = async () => {
        try {
          const full = await request('/api/conversations/' + encodeURIComponent(record.id));
          state.conversationId = full.id; $('messages').replaceChildren();
          for (const m of full.messages) addMessage(m.role, m.content);
          switchTab('chat'); notice('');
        } catch (e) { notice(e.message); }
      };
      const del = document.createElement('button'); del.textContent = '삭제';
      del.onclick = async () => {
        if (!confirm('이 대화를 삭제하시겠습니까?')) return;
        try { await request('/api/conversations/' + encodeURIComponent(record.id), { method: 'DELETE' }); if (state.conversationId === record.id) clearChat(); await refreshHistory(); }
        catch (e) { notice(e.message); }
      };
      controls.append(load, del); wrapper.append(info, controls); box.append(wrapper);
    }
  } catch (e) { notice(e.message); }
}
$('reload-history').onclick = refreshHistory;
refreshSummary();
