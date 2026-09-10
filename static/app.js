const appState = {
  sessionId: localStorage.getItem('tanshan_session_id') || null,
  plan: null,
  request: null,
  skills: [],
  activeView: 'chat',
  mapRoute: null,
};

const viewMeta = {
  chat: ['TRAVEL CONVERSATION', '对话规划'],
  overview: ['TRIP OVERVIEW', '行程总览'],
  itinerary: ['DAILY ITINERARY', '每日路线'],
  map: ['AMAP ROUTE', '高德地图'],
  gallery: ['DESTINATION PHOTOS', '景点图库'],
  budget: ['BUDGET & ADVICE', '预算贴士'],
  preparation: ['TRAVEL CHECKLIST', '旅游准备'],
};

const travelQuotes = [
  '“我会陪着你找到你人生的25号底片”',
];

const amapConfig = window.TANSHAN_AMAP_CONFIG || {};
let amapPromise = null;
let amapInstance = null;
let drivingService = null;
let mapDrawing = false;

const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatMessages = document.getElementById('chatMessages');
const sendButton = document.getElementById('sendButton');

document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => switchView(button.dataset.view)));
document.querySelectorAll('[data-go]').forEach(button => button.addEventListener('click', () => switchView(button.dataset.go)));
document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => {
  chatInput.value = button.dataset.prompt;
  chatInput.focus();
}));
document.querySelectorAll('[data-map-mode]').forEach(button => button.addEventListener('click', () => {
  if (appState.request) loadMapRoute(button.dataset.mapMode);
}));

chatInput.addEventListener('input', () => {
  chatInput.style.height = 'auto';
  chatInput.style.height = `${Math.min(chatInput.scrollHeight, 120)}px`;
});
chatInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

chatForm.addEventListener('submit', async event => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message || sendButton.disabled) return;
  appendMessage('user', message);
  chatInput.value = '';
  chatInput.style.height = 'auto';
  setSending(true);
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: appState.sessionId }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatError(data.detail));
    appState.sessionId = data.session_id;
    localStorage.setItem('tanshan_session_id', data.session_id);
    removeTyping();
    appendMessage('agent', data.reply);
    updateQuickReplies(data.quick_replies || []);
    if (data.plan) {
      appState.plan = data.plan;
      appState.request = data.request;
      appState.skills = data.skills_used || [];
      renderAll();
      showToast(data.stage === 'updated' ? '行程已更新' : '行程规划已完成');
    }
  } catch (error) {
    removeTyping();
    appendMessage('agent', `这次没有规划成功：${error.message}`);
  } finally {
    setSending(false);
  }
});

document.getElementById('clearSession').addEventListener('click', async () => {
  if (appState.sessionId) {
    try { await fetch(`/api/sessions/${encodeURIComponent(appState.sessionId)}`, { method: 'DELETE' }); } catch (_) {}
  }
  localStorage.removeItem('tanshan_session_id');
  window.location.reload();
});

function switchView(view) {
  appState.activeView = view;
  document.querySelectorAll('.nav-item').forEach(item => item.classList.toggle('active', item.dataset.view === view));
  document.querySelectorAll('.app-view').forEach(panel => panel.classList.toggle('active', panel.dataset.viewPanel === view));
  document.getElementById('viewEyebrow').textContent = viewMeta[view][0];
  document.getElementById('viewTitle').textContent = viewMeta[view][1];
  const quote = document.getElementById('travelQuote');
  if (quote) quote.textContent = travelQuotes[0];
  if (view === 'map' && appState.mapRoute) {
    requestAnimationFrame(() => drawAmapRoute(appState.mapRoute));
  }
}

function appendMessage(role, content) {
  const article = document.createElement('article');
  article.className = `message ${role === 'user' ? 'user-message' : 'agent-message'}`;
  article.innerHTML = role === 'user'
    ? `<div class="message-body"><span class="message-role">你</span><p>${escapeHtml(content)}</p></div>`
    : `<img class="agent-avatar" src="/static/scenes/wangge-avatar.jpg" alt="王哥头像"><div class="message-body"><span class="message-role">王哥 · 旅行向导</span><p>${escapeHtml(content)}</p></div>`;
  chatMessages.appendChild(article);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setSending(sending) {
  sendButton.disabled = sending;
  chatInput.disabled = sending;
  if (sending) {
    const typing = document.createElement('article');
    typing.id = 'typingMessage';
    typing.className = 'message agent-message';
    typing.innerHTML = '<img class="agent-avatar" src="/static/scenes/wangge-avatar.jpg" alt="王哥头像"><div class="typing-dots"><i></i><i></i><i></i></div>';
    chatMessages.appendChild(typing);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  } else {
    chatInput.disabled = false;
    chatInput.focus();
  }
}

function removeTyping() { document.getElementById('typingMessage')?.remove(); }

function updateQuickReplies(items) {
  if (!items.length) return;
  const container = document.getElementById('quickPrompts');
  container.innerHTML = items.map(item => `<button type="button" data-dynamic-prompt="${escapeAttr(item)}">${escapeHtml(item)}</button>`).join('');
  container.querySelectorAll('[data-dynamic-prompt]').forEach(button => button.addEventListener('click', () => {
    chatInput.value = button.dataset.dynamicPrompt;
    chatInput.focus();
  }));
}

function renderAll() {
  const { plan, request, skills } = appState;
  const tripRoute = document.getElementById('tripRoute');
  tripRoute.textContent = `${plan.origin} → ${plan.destination} · ${plan.days}天`;
  tripRoute.classList.remove('hidden');
  document.getElementById('briefStatus').textContent = '规划完成';
  document.getElementById('briefDetails').innerHTML = `
    <div><dt>路线</dt><dd>${escapeHtml(plan.origin)} → ${escapeHtml(plan.destination)}</dd></div>
    <div><dt>天数</dt><dd>${plan.days} 天</dd></div><div><dt>人数</dt><dd>${request.travelers} 人</dd></div>
    <div><dt>预算</dt><dd>${escapeHtml(request.budget_level)}</dd></div>`;
  document.getElementById('briefSkills').innerHTML = skills.map(skill => `<i>${escapeHtml(skillLabel(skill))}</i>`).join('');
  renderOverview(plan, request);
  renderItinerary(plan);
  renderBudget(plan);
  renderPreparation(plan);
  loadMapRoute(request.transport_preference);
  loadGallery(plan.destination);
  refreshIcons();
}

function renderOverview(plan, request) {
  document.getElementById('overviewEmpty').classList.add('hidden');
  const root = document.getElementById('overviewContent');
  root.classList.remove('hidden');
  root.innerHTML = `<div class="content-wrap">
    <section class="route-hero"><div><p>${escapeHtml(plan.origin)} TO ${escapeHtml(plan.destination)}</p><h2>${escapeHtml(plan.title)}</h2><span>${escapeHtml(plan.summary)}</span></div></section>
    <div class="overview-stats"><div><span>旅行天数</span><strong>${plan.days} 天</strong></div><div><span>同行人数</span><strong>${request.travelers} 人</strong></div><div><span>预算档位</span><strong>${escapeHtml(request.budget_level)}</strong></div><div><span>交通偏好</span><strong>${escapeHtml(request.transport_preference)}</strong></div></div>
    <section class="content-section"><div class="section-title"><i data-lucide="train-front"></i><h3>怎么去</h3><span>不展示票价</span></div>
      <div class="transport-grid">${plan.transport_options.map(item => `<article class="transport-card">
        <header><div><span>${escapeHtml(item.mode)}</span><h4>${escapeHtml(item.route)}</h4></div><strong>${escapeHtml(item.duration)}</strong></header>
        <div class="hub-row"><span>出发</span><b>${escapeHtml(item.departure)}</b><i data-lucide="arrow-right"></i><span>抵达</span><b>${escapeHtml(item.arrival)}</b></div>
        <ol>${(item.steps || []).map(step => `<li>${escapeHtml(step)}</li>`).join('')}</ol><p>${escapeHtml(item.advice)}</p>
      </article>`).join('')}</div>
    </section></div>`;
  refreshIcons();
}

function renderItinerary(plan) {
  document.getElementById('itineraryEmpty').classList.add('hidden');
  const root = document.getElementById('itineraryContent');
  root.classList.remove('hidden');
  root.innerHTML = `<div class="content-wrap"><header class="section-head"><div><p>${escapeHtml(plan.destination)} · ${plan.days} DAYS</p><h2>逐日路线安排</h2></div><span>相邻片区优先，减少折返</span></header>
    <div class="day-tabs">${plan.itinerary.map((day, index) => `<button class="day-tab ${index === 0 ? 'active' : ''}" type="button" data-day="${day.day}">第 ${day.day} 天</button>`).join('')}</div>
    ${plan.itinerary.map((day, index) => `<article class="day-detail ${index === 0 ? 'active' : ''}" data-day-panel="${day.day}">
      <aside class="day-side"><span>DAY ${day.day} · ${escapeHtml(day.area)}</span><h3>${escapeHtml(day.title)}</h3><p><b>住宿</b>${escapeHtml(day.accommodation)}</p><p><b>餐饮</b>${day.meals.map(escapeHtml).join('；')}</p><p><b>当日预算</b>${escapeHtml(day.daily_cost)}</p></aside>
      <div class="schedule-list">${day.schedule.map(item => `<div class="schedule-item"><time>${escapeHtml(item.time)}</time><div><h4>${escapeHtml(item.activity)}</h4><span>${escapeHtml(item.location)}</span><p>${escapeHtml(item.tips)}</p></div></div>`).join('')}</div>
    </article>`).join('')}</div>`;
  root.querySelectorAll('.day-tab').forEach(tab => tab.addEventListener('click', () => {
    root.querySelectorAll('.day-tab').forEach(item => item.classList.toggle('active', item === tab));
    root.querySelectorAll('[data-day-panel]').forEach(panel => panel.classList.toggle('active', panel.dataset.dayPanel === tab.dataset.day));
  }));
}

function renderBudget(plan) {
  document.getElementById('budgetEmpty').classList.add('hidden');
  const root = document.getElementById('budgetContent');
  root.classList.remove('hidden');
  const items = [['住宿', plan.budget.accommodation], ['餐饮', plan.budget.food], ['门票', plan.budget.tickets], ['市内交通', plan.budget.local_transit]];
  root.innerHTML = `<div class="content-wrap"><header class="section-head compact-head"><div><p>SPEND WITH EASE</p><h2>预算贴士</h2></div><span>只看会影响决定的数字</span></header>
    <section class="budget-total"><div><span>落地旅行预算</span><strong>${escapeHtml(plan.budget.total)}</strong></div><p>${escapeHtml(plan.budget.note)}</p></section>
    <div class="budget-traffic-note"><i data-lucide="train-front"></i><span>往返大交通</span><strong>${escapeHtml(plan.budget.transport)}</strong></div>
    <div class="budget-breakdown budget-breakdown--compact">${items.map(([label, value]) => `<div class="budget-item"><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`).join('')}</div>
    <section class="tips-block tips-block--compact"><div class="section-title"><i data-lucide="list-checks"></i><h3>王哥提醒</h3></div><div class="tip-columns"><ul>${plan.booking_tips.slice(0, 2).map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul><ul>${plan.practical_tips.slice(0, 2).map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div></section>
    <div class="notice">${escapeHtml(plan.notice)}</div></div>`;
  refreshIcons();
}

function renderPreparation(plan) {
  document.getElementById('preparationEmpty').classList.add('hidden');
  const root = document.getElementById('preparationContent');
  root.classList.remove('hidden');
  const prep = plan.preparation;
  const groups = [
    ['证件与预约', 'id-card', [...prep.documents, ...prep.bookings].slice(0, 4)],
    ['衣物与健康', 'shirt', [...prep.clothing, ...prep.health].slice(0, 4)],
    ['设备与当地', 'battery-charging', [...prep.electronics, ...prep.destination_specific].slice(0, 4)],
  ];
  root.innerHTML = `<div class="content-wrap"><header class="section-head compact-head"><div><p>PACK LIGHT</p><h2>${escapeHtml(plan.destination)}出行准备</h2></div><span>三组清单，出发前扫一眼</span></header>
    <section class="essential-strip essential-strip--compact"><div><i data-lucide="badge-check"></i><strong>随身必备</strong></div>${prep.essentials.slice(0, 3).map(item => `<span>${escapeHtml(item)}</span>`).join('')}</section>
    <div class="preparation-grid preparation-grid--compact">${groups.map(([title, icon, items]) => `<section class="prep-group"><header><i data-lucide="${icon}"></i><h3>${title}</h3></header><ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul></section>`).join('')}</div>
    <section class="last-check last-check--compact"><div><i data-lucide="clock-3"></i><h3>出发前最后核对</h3></div><div class="check-grid">${prep.last_check.slice(0, 4).map(item => `<label><input type="checkbox"><span>${escapeHtml(item)}</span></label>`).join('')}</div></section></div>`;
  refreshIcons();
}

async function loadMapRoute(transport = '综合推荐') {
  if (!appState.request) return;
  try {
    const response = await fetch('/api/map/route', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ origin: appState.request.origin, destination: appState.request.destination, transport }),
    });
    const route = await response.json();
    if (!response.ok) throw new Error(formatError(route.detail));
    appState.mapRoute = route;
    renderMapMeta(route);
    if (appState.activeView === 'map') await drawAmapRoute(route);
  } catch (error) {
    showToast(`地图路线暂不可用：${error.message}`);
  }
}

function renderMapMeta(route) {
  document.getElementById('mapEmpty').classList.add('hidden');
  document.getElementById('mapContent').classList.remove('hidden');
  document.getElementById('mapTitle').textContent = `${route.origin} → ${route.destination}`;
  document.getElementById('mapRouteName').textContent = `${route.origin}到${route.destination}`;
  document.getElementById('mapDuration').textContent = route.duration;
  document.getElementById('mapTransport').textContent = route.transport;
  document.getElementById('mapDescription').textContent = route.description;
  document.querySelectorAll('[data-map-mode]').forEach(button => button.classList.toggle('active', button.dataset.mapMode === route.transport));
}

async function getAmap() {
  if (!amapConfig.key || !amapConfig.securityJsCode) throw new Error('AMAP_NOT_CONFIGURED');
  if (!window.AMapLoader) throw new Error('高德地图加载器未连接');
  if (!amapPromise) {
    window._AMapSecurityConfig = { securityJsCode: amapConfig.securityJsCode };
    amapPromise = window.AMapLoader.load({
      key: amapConfig.key,
      version: '2.0',
      plugins: ['AMap.Scale', 'AMap.ToolBar', 'AMap.Geocoder', 'AMap.Driving', 'AMap.PlaceSearch'],
    });
  }
  return amapPromise;
}

async function drawAmapRoute(route) {
  if (mapDrawing || appState.activeView !== 'map') return;
  mapDrawing = true;
  const notice = document.getElementById('mapConfigNotice');
  let AMap = null;
  try {
    AMap = await getAmap();
    notice.classList.add('hidden');
    if (!amapInstance) {
      amapInstance = new AMap.Map('amapContainer', { viewMode: '3D', zoom: 5, pitch: 28, mapStyle: 'amap://styles/whitesmoke' });
      amapInstance.addControl(new AMap.Scale());
      amapInstance.addControl(new AMap.ToolBar({ position: 'RT' }));
    }
    if (drivingService) drivingService.clear();
    amapInstance.clearMap();
    if (route.transport === '自驾') {
      await drawDrivingRoute(AMap, route);
    } else {
      await drawIntercityRoute(AMap, route);
    }
  } catch (error) {
    if (error.message === 'AMAP_NOT_CONFIGURED') {
      notice.classList.remove('hidden');
      refreshIcons();
    } else if (AMap && amapInstance && route.transport === '自驾' && drawSimulatedRoadRoute(AMap, route)) {
      notice.classList.add('hidden');
    } else {
      notice.classList.remove('hidden');
      notice.querySelector('h3').textContent = '高德地图暂时无法加载';
      notice.querySelector('p').textContent = error.message || '请检查 Key、网络和安全密钥配置。';
    }
  } finally {
    mapDrawing = false;
  }
}

function drawDrivingRoute(AMap, route) {
  return new Promise((resolve, reject) => {
    drivingService = new AMap.Driving({
      policy: AMap.DrivingPolicy.LEAST_TIME,
      showTraffic: true,
      hideMarkers: true,
      autoFitView: false,
      extensions: 'all',
    });
    const originPoint = route.points?.[0];
    const destinationPoint = route.points?.[route.points.length - 1];
    const hasCoordinates = originPoint && destinationPoint
      && Number(originPoint.longitude) !== 0 && Number(destinationPoint.longitude) !== 0;
    const searchEndpoints = hasCoordinates
      ? [[Number(originPoint.longitude), Number(originPoint.latitude)], [Number(destinationPoint.longitude), Number(destinationPoint.latitude)]]
      : [
        { keyword: `${route.origin}市政府`, city: route.origin },
        { keyword: `${route.destination}市政府`, city: route.destination },
      ];
    const handleDrivingResult = (status, result) => {
      if (status !== 'complete' || !result.routes?.length) return reject(new Error('高德未返回可用的驾车路线'));
      const best = result.routes[0];
      const path = (best.steps || []).flatMap(step => Array.isArray(step.path) ? step.path : []);
      if (path.length < 2 && Array.isArray(best.path)) path.push(...best.path);
      if (path.length < 2) {
        const fallbackPath = (route.points || [])
          .filter(point => Number(point.longitude) !== 0 && Number(point.latitude) !== 0)
          .map(point => [Number(point.longitude), Number(point.latitude)]);
        if (fallbackPath.length >= 2) {
          const fallbackLine = new AMap.Polyline({
            path: fallbackPath,
            zIndex: 120,
            strokeColor: '#e4a064',
            strokeWeight: 6,
            strokeOpacity: .95,
            strokeStyle: 'dashed',
            isOutline: true,
            borderWeight: 2,
            outlineColor: '#fff4df',
          });
          amapInstance.add(fallbackLine);
          amapInstance.setFitView([fallbackLine], false, [74, 74, 74, 74]);
          document.getElementById('mapDescription').textContent = '高德返回了驾车时长，但未提供道路几何，当前显示两地路线走向；请刷新后重试。';
          resolve();
          return;
        }
        return reject(new Error('高德已返回行程，但没有可绘制的道路坐标'));
      }
      const routeLine = new AMap.Polyline({
        path,
        zIndex: 120,
        strokeColor: '#d87838',
        strokeWeight: 8,
        strokeOpacity: 1,
        strokeStyle: 'solid',
        isOutline: true,
        borderWeight: 3,
        outlineColor: '#fff4df',
        lineJoin: 'round',
        lineCap: 'round',
        showDir: true,
      });
      const startMarker = new AMap.Marker({
        position: path[0],
        title: route.origin,
        content: `<div class="amap-route-marker origin">起<span>${escapeHtml(route.origin)}</span></div>`,
        offset: new AMap.Pixel(-17, -17),
        zIndex: 130,
      });
      const endMarker = new AMap.Marker({
        position: path[path.length - 1],
        title: route.destination,
        content: `<div class="amap-route-marker destination">终<span>${escapeHtml(route.destination)}</span></div>`,
        offset: new AMap.Pixel(-17, -17),
        zIndex: 130,
      });
      amapInstance.add([routeLine, startMarker, endMarker]);
      amapInstance.setFitView([routeLine, startMarker, endMarker], false, [74, 74, 74, 74]);
      document.getElementById('mapRouteName').textContent = `${Math.round(best.distance / 1000).toLocaleString('zh-CN')} 公里`;
      document.getElementById('mapDuration').textContent = formatSeconds(best.time);
      document.getElementById('mapDescription').textContent = `高德已按当前道路数据绘制${route.origin}到${route.destination}的完整驾车轨迹，共${best.steps?.length || 0}段道路。`;
      resolve();
    };
    if (hasCoordinates) {
      drivingService.search(searchEndpoints[0], searchEndpoints[1], handleDrivingResult);
    } else {
      drivingService.search(searchEndpoints, handleDrivingResult);
    }
  });
}

function drawSimulatedRoadRoute(AMap, route) {
  const validPoints = (route.points || []).filter(point => Number(point.longitude) !== 0 && Number(point.latitude) !== 0);
  if (validPoints.length < 2) return false;
  const path = validPoints.map(point => [Number(point.longitude), Number(point.latitude)]);
  const shadowLine = new AMap.Polyline({
    path,
    zIndex: 118,
    strokeColor: '#623a28',
    strokeWeight: 14,
    strokeOpacity: .32,
    lineJoin: 'round',
    lineCap: 'round',
  });
  const routeLine = new AMap.Polyline({
    path,
    zIndex: 120,
    strokeColor: '#d87838',
    strokeWeight: 8,
    strokeOpacity: 1,
    isOutline: true,
    borderWeight: 2,
    outlineColor: '#fff4df',
    lineJoin: 'round',
    lineCap: 'round',
    showDir: true,
  });
  const markers = validPoints.map((point, index) => new AMap.Marker({
    position: path[index],
    title: point.name,
    content: index === 0 || index === validPoints.length - 1
      ? `<div class="amap-route-marker ${index === 0 ? 'origin' : 'destination'}">${index === 0 ? '起' : '终'}<span>${escapeHtml(point.name)}</span></div>`
      : `<div class="amap-waypoint-marker"><i></i><span>${escapeHtml(point.name)}</span></div>`,
    offset: new AMap.Pixel(index === 0 || index === validPoints.length - 1 ? -17 : -8, index === 0 || index === validPoints.length - 1 ? -17 : -8),
    zIndex: 130,
  }));
  amapInstance.add([shadowLine, routeLine, ...markers]);
  amapInstance.setFitView([routeLine, ...markers], false, [76, 76, 76, 76]);
  const corridor = validPoints.map(point => point.name).join(' → ');
  document.getElementById('mapDescription').textContent = `高德驾车服务未返回道路，已按真实城市走廊模拟线路：${corridor}。`;
  return true;
}

async function drawIntercityRoute(AMap, route) {
  const geocoder = new AMap.Geocoder({ city: '全国' });
  const points = await Promise.all(route.points.map(point => geocode(geocoder, point.name)));
  const line = new AMap.Polyline({
    path: points,
    zIndex: 120,
    strokeColor: '#e4a064',
    strokeWeight: route.transport === '飞机' ? 5 : 7,
    strokeOpacity: 1,
    strokeStyle: route.transport === '飞机' ? 'dashed' : route.transport === '火车' ? 'dashed' : 'solid',
    isOutline: true,
    borderWeight: 2,
    outlineColor: '#fff4df',
    lineJoin: 'round', lineCap: 'round',
  });
  const markers = points.map((position, index) => new AMap.Marker({
    position,
    title: route.points[index].name,
    content: `<div class="amap-route-marker ${route.points[index].kind}">${index + 1}<span>${escapeHtml(route.points[index].name)}</span></div>`,
    offset: new AMap.Pixel(-16, -16),
    zIndex: 130,
  }));
  amapInstance.add([line, ...markers]);
  amapInstance.setFitView([line, ...markers], false, [80, 80, 80, 80]);
  document.getElementById('mapDescription').textContent = `高德已定位${route.points.map(point => point.name).join('、')}；${route.transport}按真实交通枢纽展示走向。`;
}

function geocode(geocoder, address) {
  return new Promise((resolve, reject) => geocoder.getLocation(address, (status, result) => {
    if (status === 'complete' && result.geocodes?.length) resolve(result.geocodes[0].location);
    else reject(new Error(`无法定位${address}`));
  }));
}

async function loadGallery(destination) {
  const root = document.getElementById('galleryGrid');
  document.getElementById('galleryLabel').textContent = destination ? `仅显示 ${destination}` : '等待目的地';
  if (!destination) return;
  root.innerHTML = '<div class="gallery-loading"><i></i><span>正在读取高德景点实景图…</span></div>';
  try {
    const AMap = await getAmap();
    const searchResult = await searchAttractions(AMap, destination);
    const pois = await hydrateAttractions(searchResult.search, searchResult.pois);
    const items = pois.map(poi => ({ poi, photo: getPoiPhoto(poi) })).filter(item => item.photo).slice(0, 9);
    if (!items.length) throw new Error('高德当前没有返回带照片的景点');
    root.innerHTML = items.map(({ poi, photo }) => {
      const location = poi.location ? `${poi.location.lng},${poi.location.lat}` : '';
      const detailUrl = location ? `https://uri.amap.com/marker?position=${encodeURIComponent(location)}&name=${encodeURIComponent(poi.name)}` : '#';
      return `<article class="attraction-card"><img src="${escapeAttr(photo)}" alt="${escapeAttr(destination)}${escapeAttr(poi.name)}实景照片" loading="lazy" referrerpolicy="no-referrer">
        <div class="attraction-copy"><span>${escapeHtml(destination)} · ${escapeHtml(poi.type || '风景名胜')}</span><h3>${escapeHtml(poi.name)}</h3><p>${escapeHtml(poi.address || poi.adname || '高德景点地点')}</p><a href="${escapeAttr(detailUrl)}" target="_blank" rel="noreferrer">在高德查看 <i data-lucide="external-link"></i></a></div></article>`;
    }).join('');
    document.getElementById('briefImage').src = items[0].photo;
    document.getElementById('briefImage').alt = `${destination}${items[0].poi.name}实景照片`;
    document.querySelector('.route-hero')?.style.setProperty('background-image', `url(${JSON.stringify(items[0].photo)})`);
    refreshIcons();
  } catch (error) {
    const needsKey = error.message === 'AMAP_NOT_CONFIGURED';
    root.innerHTML = `<div class="gallery-empty"><i data-lucide="${needsKey ? 'key-round' : 'image-off'}"></i><p>${needsKey ? '配置高德 Web 端 Key 后，将自动显示当前目的地的真实景点照片。' : escapeHtml(error.message)}</p></div>`;
    refreshIcons();
  }
}

function searchAttractions(AMap, destination) {
  return new Promise((resolve, reject) => {
    const search = new AMap.PlaceSearch({ city: destination, citylimit: true, type: '110000', pageSize: 30, pageIndex: 1, extensions: 'all' });
    search.search('景点', (status, result) => {
      if (status === 'complete' && result.poiList?.pois?.length) resolve({ search, pois: result.poiList.pois });
      else reject(new Error(`没有找到${destination}的景点照片`));
    });
  });
}

function hydrateAttractions(search, pois) {
  const candidates = pois.slice(0, 12);
  return Promise.all(candidates.map(poi => {
    if (getPoiPhoto(poi) || !poi.id || typeof search.getDetails !== 'function') return Promise.resolve(poi);
    return new Promise(resolve => {
      search.getDetails(poi.id, (status, result) => {
        const detail = result?.poiList?.pois?.[0] || result?.poi || null;
        resolve(detail ? { ...poi, ...detail } : poi);
      });
    });
  }));
}

function getPoiPhoto(poi) {
  const photos = Array.isArray(poi.photos) ? poi.photos : [];
  const raw = photos[0]?.url || photos[0]?._url || photos[0]?._preurl || '';
  if (!raw) return '';
  try {
    const parsed = new URL(String(raw), window.location.origin);
    if (!['http:', 'https:'].includes(parsed.protocol)) return '';
    parsed.protocol = 'https:';
    return parsed.href;
  } catch (_) {
    return '';
  }
}

function formatSeconds(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return hours ? `${hours}小时${minutes}分钟` : `${minutes}分钟`;
}

function skillLabel(name) {
  return ({
    'weather-advice': '天气', 'route-planning': '路线', 'enroute-attractions': '沿途景点', 'trip-budget': '预算',
    'local-food': '美食', 'dietary-taboos': '饮食禁忌', 'local-customs': '风土民情', 'festival-etiquette': '节庆礼仪',
    'regional-culture': '特色文化', 'travel-pitfalls': '避坑', 'travel-preparation': '旅游准备',
  })[name] || name;
}

function refreshIcons() { if (window.lucide) window.lucide.createIcons({ attrs: { 'stroke-width': 1.8 } }); }
function formatError(detail) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg).join('；');
  return '请求失败，请稍后再试。';
}

let toastTimer;
function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
}

function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]); }
function escapeAttr(value) { return escapeHtml(value); }

window.addEventListener('beforeunload', () => {
  if (amapInstance) amapInstance.destroy();
  amapInstance = null;
});

refreshIcons();
