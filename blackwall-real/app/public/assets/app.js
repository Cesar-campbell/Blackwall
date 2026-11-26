'use strict';

/* ---------- Íconos y logo ---------- */
const IC = {
  home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
  folder: '<path d="M3 6a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6"/><circle cx="17" cy="9" r="2.5"/><path d="M17 14c2.5 0 4.5 2 4.5 5"/>',
  log: '<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  sliders: '<path d="M4 6h9M19 6h1M4 12h3M13 12h7M4 18h11M21 18h-1"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.5-7 8-7s8 3 8 7"/>',
  out: '<path d="M9 4H5a2 2 0 00-2 2v12a2 2 0 002 2h4M16 8l4 4-4 4M20 12H9"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
};
const ic = (n, c = '') => `<svg class="ic ${c}" viewBox="0 0 24 24" aria-hidden="true">${IC[n]}</svg>`;
const LOGO = z => `<svg width="${z}" height="${z}" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="26" fill="none" stroke="#e8f0f9" stroke-width="5" stroke-dasharray="42 12.45" transform="rotate(-80 32 32)"/><circle cx="32" cy="32" r="16" fill="#0a4d8c"/><path d="M26.5 31v-3.5a5.5 5.5 0 0 1 11 0V31" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/><rect x="23.5" y="30.5" width="17" height="13" rx="2.5" fill="#fff"/><circle cx="32" cy="36" r="2" fill="#0a4d8c"/><rect x="31.2" y="37" width="1.6" height="3.6" rx=".6" fill="#0a4d8c"/></svg>`;

const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
$('#icLogo').innerHTML = LOGO(48);
$('#bOut').innerHTML = ic('out') + ' Salir';

/* ---------- Catálogos ---------- */
const GRUPOS = { GRP_TI_ADMIN: 'ROL_ADMIN', GRP_SOC_ANALISTA: 'ROL_ANALISTA', GRP_CUM_AUDITOR: 'ROL_AUDITOR', GRP_USR_USUARIO: 'ROL_USUARIO', GRP_PUB_INVITADO: 'ROL_INVITADO' };
const RL = { ROL_ADMIN: 'Administrador', ROL_ANALISTA: 'Analista', ROL_AUDITOR: 'Auditor', ROL_USUARIO: 'Usuario', ROL_INVITADO: 'Invitado' };
const DESC = {
  ROL_ADMIN: 'Administras cuentas y configuración. Solo lees la auditoría, así no puedes alterar tu propia huella.',
  ROL_ANALISTA: 'Gestionas y resuelves casos de seguridad. No borras casos ni administras usuarios.',
  ROL_AUDITOR: 'Revisas cumplimiento y trazabilidad. Solo lectura: quien audita no opera.',
  ROL_USUARIO: 'Reportas incidentes y consultas el estado de los tuyos.',
  ROL_INVITADO: 'Consultas información pública.',
};
const SEV = ['baja', 'media', 'alta', 'critica'], EST = ['abierto', 'en_analisis', 'resuelto'];
const MSG_LOGIN = 'No se pudo iniciar sesión. Inténtalo de nuevo.';

/* ---------- Sesión y llamadas a la API ---------- */
const S = { ses: null, tok: null, exp: 0, view: 'inicio' };
const sc = () => S.ses ? S.ses.scopes : [];
const has = s => sc().includes(s);
const rol = () => (S.ses?.roles || [])[0];

function aplicar(s) {
  S.ses = s; S.tok = s.access_token; S.exp = s.exp;
}
async function pedirSesion(renovar = false) {
  const r = await fetch('/auth/sesion' + (renovar ? '?renovar=1' : ''), { credentials: 'same-origin', cache: 'no-store' });
  if (r.status !== 200) return null;
  const s = await r.json(); aplicar(s); return s;
}
async function token() {
  if (!S.tok || S.exp - Date.now() / 1000 < 20) { if (!await pedirSesion()) throw { status: 401, body: { detalle: 'Tu sesión expiró.' } }; }
  return S.tok;
}
async function call(m, p, b) {
  let t; try { t = await token(); } catch (e) { return e; }
  const r = await fetch('/api' + p, { method: m, headers: { Authorization: 'Bearer ' + t, ...(b ? { 'Content-Type': 'application/json' } : {}) }, body: b ? JSON.stringify(b) : undefined });
  let body = null; try { body = await r.json(); } catch { /* sin cuerpo */ }
  return { status: r.status, body };
}
const must = r => { if (r.status >= 400) throw r; return r; };

/* ---------- Utilidades de interfaz ---------- */
const NAV = [
  ['inicio', 'home', 'Inicio', () => true],
  ['casos', 'folder', 'Casos', () => has('casos:leer') || has('casos:leer_propios')],
  ['usuarios', 'users', 'Usuarios', () => has('usuarios:leer') || has('usuarios:admin')],
  ['auditoria', 'log', 'Auditoría', () => has('auditoria:leer')],
  ['config', 'sliders', 'Configuración', () => has('config:admin')],
  ['cuenta', 'user', 'Mi cuenta', () => true],
];
const TITULO = { inicio: 'Inicio', casos: 'Casos', usuarios: 'Usuarios', auditoria: 'Auditoría', config: 'Configuración', cuenta: 'Mi cuenta' };
const badge = s => ({ critica: 'no', alta: 'no', media: 'al', baja: 'ok', abierto: 'al', en_analisis: 'mut', resuelto: 'ok' }[s] || 'mut');
const pill = (t, k) => `<span class="pill ${k}">${esc(t)}</span>`;
const txt = s => String(s).replace('_', ' ');
const fecha = t => new Date(t).toLocaleString('es-PA', { dateStyle: 'short', timeStyle: 'medium' });
const iniciales = n => n.split(' ').map(x => x[0]).join('').slice(0, 2).toUpperCase();
function toast(res, ok = 'Listo') {
  const g = res.status < 400, d = document.createElement('div');
  d.className = g ? '' : 'no'; d.textContent = g ? ok : (res.body?.detalle || res.body?.error || 'No se pudo completar');
  $('#toast').appendChild(d); setTimeout(() => d.remove(), 3800);
}
function modal(h) { const m = $('#modal'); m.hidden = false; m.innerHTML = `<div class="box">${h}</div>`; m.onclick = e => { if (e.target === m) m.hidden = true; }; }
const closeM = () => { $('#modal').hidden = true; };
const head = (t, sub, btn = '') => `<div class="vt"><div><h2>${t}</h2>${sub ? `<p>${sub}</p>` : ''}</div><div>${btn}</div></div>`;
function barras() { document.querySelectorAll('[data-w]').forEach(i => { i.style.width = i.dataset.w + '%'; }); }

/* ---------- Arranque y navegación ---------- */
async function arrancar() {
  const e = new URLSearchParams(location.search).get('e');
  if (e) $('#lerr').innerHTML = `<div class="err">${esc(MSG_LOGIN)}</div>`;
  if (await pedirSesion()) { history.replaceState(null, '', '/'); entrarApp(); }
}
function entrarApp() {
  document.body.classList.add('in');
  const s = S.ses;
  $('#wName').textContent = s.nombre; $('#wRole').textContent = RL[rol()] || '';
  $('#av').textContent = iniciales(s.nombre);
  $('#side').innerHTML = '<div class="lg"><span>' + LOGO(38) + '</span>BLACKWALL</div>' +
    NAV.filter(n => n[3]()).map(n => `<button data-v="${n[0]}">${ic(n[1])}<span>${n[2]}</span></button>`).join('');
  location.hash = 'inicio'; go('inicio', true);
}
async function render() {
  const v = VIEWS[S.view] ? S.view : 'inicio'; $('#vtitle').textContent = TITULO[v] || '';
  try { $('#view').innerHTML = await VIEWS[v](); barras(); }
  catch (e) {
    if (e.status === 401) { location.replace('/'); return; }
    $('#view').innerHTML = e.status === 403
      ? `<div class="card denied"><div class="big">403</div><h2>Acceso denegado</h2><p class="mut mt1">${esc(e.body.detalle)}. El intento quedó registrado en la auditoría.</p><button class="btn mt" data-v="inicio">Volver al inicio</button></div>`
      : `<div class="card denied"><h2>Algo salió mal</h2><p class="mut">${esc(e.body?.detalle || 'Error inesperado')}</p></div>`;
  }
}
async function go(v, first) {
  S.view = v; document.querySelectorAll('#side button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  const el = $('#view'); el.classList.remove('enter'); await render(); void el.offsetWidth; el.classList.add('enter'); if (!first) window.scrollTo(0, 0);
}
window.addEventListener('hashchange', () => { const v = location.hash.slice(1); if (S.ses && v && v !== S.view) go(VIEWS[v] ? v : 'inicio'); });

/* ---------- Vistas ---------- */
const ACCIONES = {
  ROL_ADMIN: [['users', 'Gestionar usuarios', 'usuarios'], ['log', 'Ver auditoría', 'auditoria'], ['sliders', 'Configuración', 'config'], ['folder', 'Ver casos', 'casos']],
  ROL_ANALISTA: [['folder', 'Ver casos', 'casos'], ['plus', 'Reportar incidente', null, 'nuevo'], ['users', 'Ver usuarios', 'usuarios']],
  ROL_AUDITOR: [['log', 'Revisar auditoría', 'auditoria'], ['folder', 'Ver casos', 'casos'], ['users', 'Ver usuarios', 'usuarios']],
  ROL_USUARIO: [['plus', 'Reportar incidente', null, 'nuevo'], ['folder', 'Mis casos', 'casos']], ROL_INVITADO: [],
};
const VIEWS = {
  async inicio() {
    const st = must(await call('GET', '/estadisticas')).body;
    const bars = l => l.map(([k, n]) => `<div class="bar"><span>${txt(k)}</span><div><i data-w="${st.total ? Math.max(n ? 4 : 0, Math.round(n / st.total * 100)) : 0}"></i></div><b>${n}</b></div>`).join('');
    const q = ACCIONES[rol()] || [];
    return `<div class="hero"><h2>Hola, ${esc(S.ses.nombre.split(' ')[0])}</h2><p>${DESC[rol()] || ''}</p></div>
    ${q.length ? `<div class="quick">${q.map(([i, t, v, a]) => `<button ${v ? `data-v="${v}"` : `data-a="${a}"`}>${ic(i)}${t}</button>`).join('')}</div>` : ''}
    <div class="card"><h3>Estadísticas · ${esc(st.alcance)}</h3>${st.publico ? `<p>Casos registrados: <b>${st.total}</b> · Casos resueltos: <b>${st.resueltos}</b></p>`
      : `<div class="g2"><div><p>Total de casos: <b>${st.total}</b></p><div class="ct mt1">Por estado</div>${bars(st.estado)}</div><div><div class="ct">Por severidad</div>${bars(st.severidad)}</div></div>`}</div>`;
  },
  async casos() {
    S.casosData = must(await call('GET', '/casos')).body; const own = !has('casos:leer'), nuevo = has('casos:escribir') || has('casos:crear');
    return head(own ? 'Mis casos' : 'Casos de incidentes', own ? 'Aquí ves los incidentes que reportaste.' : 'Todos los incidentes registrados.', nuevo ? `<button class="btn" data-a="nuevo">${ic('plus')} Reportar incidente</button>` : '') +
      `<div class="card"><div class="tools"><input id="fq" placeholder="Buscar por título o ID…"><select id="fe"><option value="">Todos los estados</option>${EST.map(e => `<option value="${e}">${txt(e)}</option>`).join('')}</select></div><div class="tw"><table><thead><tr><th>ID</th><th>Título</th><th>Severidad</th><th>Estado</th>${own ? '' : '<th>Reporta</th>'}<th></th></tr></thead><tbody id="tb">${filasCasos()}</tbody></table></div></div>`;
  },
  async usuarios() {
    const l = must(await call('GET', '/usuarios')).body, adm = has('usuarios:admin'); S.usuarios = l;
    return head('Usuarios', adm ? 'Administra las cuentas. Cada usuario pertenece a un grupo del directorio y de él recibe su rol.' : 'Usuarios del directorio (solo lectura).', adm ? `<button class="btn" data-a="unuevo">${ic('plus')} Nuevo usuario</button>` : '') +
      `<div class="card tw"><table><thead><tr><th>Usuario</th><th>Nombre</th><th>Grupo</th><th>Rol</th><th>2 pasos</th><th>Estado</th>${adm ? '<th></th>' : ''}</tr></thead><tbody>${l.map(u => {
        const yo = u.id === S.ses.usuario;
        return `<tr><td class="mono">${esc(u.id)}</td><td>${esc(u.nombre)}</td><td class="mono sm">${esc(u.grupo || '—')}</td><td>${RL[u.rol] || 'Servicio'}</td>
        <td>${u.servicio ? pill('n/a', 'mut') : u.mfa ? pill('activo', 'ok') : (u.rol === 'ROL_ADMIN' || u.rol === 'ROL_AUDITOR') ? pill('pendiente', 'al') : pill('no', 'mut')}</td>
        <td>${u.servicio ? pill('servicio', 'al') : u.bloqueado ? pill('bloqueado', 'no') : pill('activo', 'ok')}</td>
        ${adm ? `<td class="nw">${u.servicio || yo ? '' : `<button class="btn sec s" data-a="uedit" data-id="${esc(u.id)}">Editar</button> `}${u.bloqueado ? `<button class="btn s" data-a="unlock" data-id="${esc(u.id)}">Desbloquear</button> ` : ''}${u.servicio || yo ? '' : `<button class="btn no s" data-a="udel" data-id="${esc(u.id)}">Eliminar</button>`}</td>` : ''}</tr>`;
      }).join('')}</tbody></table></div>`;
  },
  async auditoria() {
    S.audData = must(await call('GET', '/auditoria')).body;
    return head('Auditoría', 'Quién hizo qué, qué se permitió y qué se denegó.', `<button class="btn sec s" data-a="recargar">Actualizar</button>`) +
      `<div class="card"><div class="tools"><input id="aq" placeholder="Buscar por usuario o evento…"><select id="ar"><option value="">Todos los resultados</option><option value="ALLOW">Permitidos</option><option value="DENY">Denegados</option></select></div><div class="tw"><table><thead><tr><th>Hora</th><th>Usuario</th><th>Evento</th><th>Resultado</th><th>Detalle</th></tr></thead><tbody id="atb">${filasAud()}</tbody></table></div></div>`;
  },
  async config() {
    const c = must(await call('GET', '/config')).body;
    return head('Configuración', 'Parámetros de seguridad del sistema.') + `<div class="card maxw"><label for="cT">Duración de la sesión activa (minutos, entre 5 y 15)</label><input id="cT" type="number" min="5" max="15" value="${c.tokenMin}"><label for="cI">Intentos fallidos antes de bloquear</label><input id="cI" type="number" min="3" max="10" value="${c.maxIntentos}"><label for="cB">Duración del bloqueo (segundos)</label><input id="cB" type="number" min="10" max="3600" value="${c.bloqueoSeg}"><button class="btn mt" data-a="guardarcfg">Guardar cambios</button></div>`;
  },
  async cuenta() {
    const s = S.ses, r = rol(), obl = r === 'ROL_ADMIN' || r === 'ROL_AUDITOR';
    return head('Mi cuenta', 'Tus datos y tu sesión.', `<button class="btn no s" data-a="salir">Cerrar sesión</button>`) +
      `<div class="g2"><div class="stack"><div class="card"><h3>Perfil</h3><table><tbody><tr><td class="mut">Nombre</td><td>${esc(s.nombre)}</td></tr><tr><td class="mut">Usuario</td><td class="mono">${esc(s.usuario)}</td></tr><tr><td class="mut">Rol</td><td>${RL[r] || ''}</td></tr><tr><td class="mut">Grupo</td><td class="mono">${esc((s.grupos || []).join(', '))}</td></tr><tr><td class="mut">Verificación en dos pasos</td><td>${obl ? pill('obligatoria para tu rol', 'ok') : pill('opcional', 'mut')}</td></tr></tbody></table></div>
      <div class="card"><h3>Contraseña</h3><p class="sm">Mínimo 12 caracteres, sin reutilizar tus últimas 5 contraseñas.</p><a class="btn mt1" href="/auth/cambiar-clave">Cambiar contraseña</a><p class="mut sm mt1">Tras 5 intentos fallidos al iniciar sesión la cuenta se bloquea un tiempo.</p></div></div>
</div>`;
  },
};
function filasCasos() {
  const q = ($('#fq')?.value || '').toLowerCase(), e = $('#fe')?.value || '', own = !has('casos:leer');
  const l = S.casosData.filter(k => (!e || k.estado === e) && (!q || (k.titulo + ' ' + k.id).toLowerCase().includes(q)));
  return l.map(k => `<tr><td class="mono">${esc(k.id)}</td><td>${esc(k.titulo)}</td><td>${pill(k.severidad, badge(k.severidad))}</td><td>${pill(txt(k.estado), badge(k.estado))}</td>${own ? '' : `<td class="mono sm">${esc(k.propietario)}</td>`}<td class="nw"><button class="btn sec s" data-a="ver" data-id="${esc(k.id)}">Abrir</button>${has('casos:borrar') ? ` <button class="btn no s" data-a="borrar" data-id="${esc(k.id)}">Borrar</button>` : ''}</td></tr>`).join('') || `<tr><td colspan="6" class="empty">No hay casos que coincidan.</td></tr>`;
}
function filasAud() {
  const q = ($('#aq')?.value || '').toLowerCase(), r = $('#ar')?.value || '';
  return S.audData.filter(a => (!r || a.res === r) && (!q || (a.u + ' ' + a.ev + ' ' + a.det).toLowerCase().includes(q))).map(a => `<tr><td class="mono sm">${esc(fecha(a.t))}</td><td class="mono sm">${esc(a.u)}</td><td class="mono sm">${esc(a.ev)}</td><td>${pill(a.res === 'ALLOW' ? 'Permitido' : 'Denegado', a.res === 'ALLOW' ? 'ok' : 'no')}</td><td class="sm">${esc(a.det)}</td></tr>`).join('') || `<tr><td colspan="5" class="empty">Sin eventos.</td></tr>`;
}

/* ---------- Formularios (modales) ---------- */
const formCaso = () => `<h3 class="mb1">Reportar incidente</h3><label for="nT">Título</label><input id="nT" maxlength="120" placeholder="¿Qué pasó?"><label for="nD">Descripción</label><textarea id="nD" rows="3" maxlength="2000"></textarea><label for="nS">Severidad</label><select id="nS">${SEV.map(s => `<option ${s === 'media' ? 'selected' : ''}>${s}</option>`).join('')}</select><div class="fx mt"><button class="btn" data-a="crear">Reportar</button><button class="btn sec" data-a="cerrar">Cancelar</button></div>`;
const formUser = (id, u) => {
  const e = !!id;
  return `<h3 class="mb1">${e ? 'Editar usuario' : 'Nuevo usuario'}</h3>
 <label for="uI">Usuario (apellido.nombre)</label><input id="uI" value="${e ? esc(id) : ''}" ${e ? 'disabled' : ''} placeholder="perez.juan" maxlength="40">
 <label for="uN">Nombre completo</label><input id="uN" value="${e ? esc(u.nombre) : ''}" maxlength="80">
 <label for="uG">Grupo del directorio</label><select id="uG">${Object.entries(GRUPOS).map(([g, r]) => `<option value="${g}" ${e && u.grupo === g ? 'selected' : ''}>${g} → ${RL[r]}</option>`).join('')}</select>
 ${e ? '' : `<label for="uP">Contraseña inicial (mínimo 12 caracteres)</label><input id="uP" type="password" autocomplete="new-password">`}
 <div class="fx mt"><button class="btn" data-a="${e ? 'uguardar' : 'ucrear'}" data-id="${esc(id || '')}">${e ? 'Guardar' : 'Crear usuario'}</button><button class="btn sec" data-a="cerrar">Cancelar</button></div>`;
};
async function abrirCaso(id) {
  const r = await call('GET', '/casos/' + encodeURIComponent(id)); if (r.status !== 200) return toast(r); const k = r.body;
  const full = has('casos:escribir'), mio = !full && has('casos:escribir_propios') && k.estado === 'abierto', puedeCom = has('comentarios:escribir') || has('comentarios:escribir_propios');
  modal(`<h3 class="mb1">${esc(k.id)} · ${esc(k.titulo)}</h3><p class="mt1">${pill(k.severidad, badge(k.severidad))} ${pill(txt(k.estado), badge(k.estado))} <span class="mut sm">reportado por <span class="mono">${esc(k.propietario)}</span></span></p><p class="mut">${esc(k.descripcion) || 'Sin descripción.'}</p>
  ${full ? `<div class="g2"><div><label for="eE">Estado</label><select id="eE">${EST.map(e => `<option value="${e}" ${k.estado === e ? 'selected' : ''}>${txt(e)}</option>`).join('')}</select></div><div><label for="eS">Severidad</label><select id="eS">${SEV.map(e => `<option ${k.severidad === e ? 'selected' : ''}>${e}</option>`).join('')}</select></div></div><button class="btn s mt1" data-a="estado" data-id="${esc(k.id)}">Guardar cambios</button>` : ''}
  ${mio ? `<label for="mT">Editar mi reporte</label><input id="mT" value="${esc(k.titulo)}"><textarea id="mD" rows="2" class="mt1">${esc(k.descripcion)}</textarea><button class="btn s mt1" data-a="miedit" data-id="${esc(k.id)}">Guardar</button>` : ''}
  <div class="ct mt2">Comentarios</div>${k.comentarios.map(c => `<div class="com"><span><b class="mono">${esc(c.autor)}</b> ${esc(c.texto)}</span><span class="nw">${has('comentarios:escribir') ? `<button class="btn sec s" data-a="cedit" data-id="${esc(k.id)}" data-c="${c.id}" data-x="${esc(c.texto)}">Editar</button> ` : ''}${has('comentarios:borrar') ? `<button class="btn no s" data-a="cdel" data-id="${esc(k.id)}" data-c="${c.id}">Borrar</button>` : ''}</span></div>`).join('') || '<p class="mut sm">Sin comentarios.</p>'}
  ${puedeCom ? `<input id="cX" class="mt1" placeholder="Escribe un comentario" maxlength="1000" aria-label="Comentario"><button class="btn s mt1" data-a="comentar" data-id="${esc(k.id)}">Comentar</button>` : ''}
  <div class="mt2"><button class="btn sec" data-a="cerrar">Cerrar</button></div>`);
}

/* ---------- Sesión: salir ---------- */
async function salir() {
  try {
    const r = await fetch('/auth/logout', { method: 'POST', headers: { 'X-CSRF-Token': S.ses.csrf }, credentials: 'same-origin' });
    const j = await r.json();
    S.ses = S.tok = null;
    if (j.redirect) { location.href = j.redirect; return; }
  } catch { /* se muestra el aviso local */ }
  location.replace('/');
}

/* ---------- Eventos ---------- */
$('#side').onclick = e => { const b = e.target.closest('button'); if (b) { location.hash = b.dataset.v; if (S.view === b.dataset.v) go(b.dataset.v); } };
$('#bOut').onclick = () => salir();
document.addEventListener('input', e => {
  if (e.target.id === 'fq' || e.target.id === 'fe') $('#tb').innerHTML = filasCasos();
  if (e.target.id === 'aq' || e.target.id === 'ar') $('#atb').innerHTML = filasAud();
});
document.addEventListener('click', async e => {
  const b = e.target.closest('[data-a],[data-v]'); if (!b) return;
  if (b.dataset.v && !b.dataset.a) { closeM(); location.hash = b.dataset.v; if (S.view === b.dataset.v) go(b.dataset.v); return; }
  const a = b.dataset.a, id = b.dataset.id, enc = encodeURIComponent, done = async (r, m) => { toast(r, m); if (r.status < 400) { closeM(); await render(); } };
  if (a === 'cerrar') closeM();
  if (a === 'nuevo') modal(formCaso());
  if (a === 'crear') done(await call('POST', '/casos', { titulo: $('#nT').value, descripcion: $('#nD').value, severidad: $('#nS').value }), 'Incidente reportado');
  if (a === 'ver') abrirCaso(id);
  if (a === 'estado') done(await call('PUT', '/casos/' + enc(id), { estado: $('#eE').value, severidad: $('#eS').value }), 'Caso actualizado');
  if (a === 'miedit') done(await call('PUT', '/casos/' + enc(id), { titulo: $('#mT').value, descripcion: $('#mD').value }), 'Reporte actualizado');
  if (a === 'borrar' && confirm('¿Borrar el caso ' + id + '? Esta acción no se puede deshacer.')) done(await call('DELETE', '/casos/' + enc(id)), 'Caso borrado');
  if (a === 'comentar') { const r = await call('POST', `/casos/${enc(id)}/comentarios`, { texto: $('#cX').value }); toast(r, 'Comentario agregado'); if (r.status < 400) abrirCaso(id); }
  if (a === 'cedit') { const x = prompt('Editar comentario', b.dataset.x); if (x != null) { const r = await call('PUT', `/casos/${enc(id)}/comentarios/${b.dataset.c}`, { texto: x }); toast(r, 'Comentario editado'); if (r.status < 400) abrirCaso(id); } }
  if (a === 'cdel' && confirm('¿Borrar este comentario?')) { const r = await call('DELETE', `/casos/${enc(id)}/comentarios/${b.dataset.c}`); toast(r, 'Comentario borrado'); if (r.status < 400) abrirCaso(id); }
  if (a === 'unuevo') modal(formUser());
  if (a === 'uedit') modal(formUser(id, S.usuarios.find(u => u.id === id)));
  if (a === 'ucrear') done(await call('POST', '/usuarios', { id: $('#uI').value.trim(), nombre: $('#uN').value, grupo: $('#uG').value, clave: $('#uP').value }), 'Usuario creado');
  if (a === 'uguardar') done(await call('PUT', '/usuarios/' + enc(id), { nombre: $('#uN').value, grupo: $('#uG').value }), 'Usuario actualizado');
  if (a === 'udel' && confirm('¿Eliminar al usuario ' + id + '?')) done(await call('DELETE', '/usuarios/' + enc(id)), 'Usuario eliminado');
  if (a === 'unlock') done(await call('POST', `/usuarios/${enc(id)}/desbloquear`), 'Cuenta desbloqueada');
  if (a === 'recargar') render();
  if (a === 'guardarcfg') done(await call('PUT', '/config', { tokenMin: +$('#cT').value, maxIntentos: +$('#cI').value, bloqueoSeg: +$('#cB').value }), 'Configuración guardada');
  if (a === 'salir') salir();
});

/* Auditoría en vivo: se actualiza sola cada pocos segundos mientras está abierta (sin perder lo escrito en los filtros) */
setInterval(async () => {
  if (!S.ses || S.view !== 'auditoria' || !$('#atb') || document.hidden || !$('#modal').hidden) return;
  const r = await call('GET', '/auditoria');
  if (r.status === 200) { S.audData = r.body; $('#atb').innerHTML = filasAud(); }
}, 5000);

arrancar();
