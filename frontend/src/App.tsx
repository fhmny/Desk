import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { ArrowLeft, Check, CircleHelp, ExternalLink, FileImage, Film, LayoutDashboard, LogOut, MessageCircle, Plus, Send, Users, X } from 'lucide-react';
import { api, clearToken, getToken, patch, post, setToken, type DeskDetail, type DeskRequest, type Kind, type User } from './api';
import PublicHome from './PublicHome';
import PublicAdmin from './PublicAdmin';

const statusText: Record<DeskRequest['status'], string> = {
  submitted: 'جديد', accepted: 'مقبول', in_progress: 'جارٍ العمل', revision_requested: 'يحتاج تعديل', completed: 'مكتمل', canceled: 'ملغي',
};
const kindText = { image: 'تصميم صورة', video: 'مونتاج فيديو' };

function App() {
  const [me, setMe] = useState<User | null>(null);
  const [requests, setRequests] = useState<DeskRequest[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selected, setSelected] = useState<DeskDetail | null>(null);
  const [view, setView] = useState<'requests' | 'team' | 'public'>('requests');
  const [showNew, setShowNew] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(Boolean(getToken()));

  const refresh = useCallback(async () => {
    try {
      const current = await api<User>('/me');
      setMe(current);
      const items = await api<DeskRequest[]>('/requests');
      setRequests(items);
      if (current.role === 'admin') setUsers(await api<User[]>('/users'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
      if (!getToken()) setMe(null);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { if (getToken()) void refresh(); }, [refresh]);
  useEffect(() => {
    if (!me || !selected) return;
    const timer = window.setInterval(() => { void api<DeskDetail>(`/requests/${selected.id}`).then(setSelected).catch(() => {}); }, 15000);
    return () => window.clearInterval(timer);
  }, [me, selected?.id]);

  async function openRequest(id: number) {
    try { setSelected(await api<DeskDetail>(`/requests/${id}`)); setError(''); }
    catch (e) { setError((e as Error).message); }
  }
  async function action(path: string, success: string) {
    try {
      await post(path);
      setNotice(success); setError('');
      await refresh();
      if (selected) await openRequest(selected.id);
    } catch (e) { setError((e as Error).message); }
  }
  async function logout() {
    try { await post('/logout'); } catch { /* Session may already be expired. */ }
    clearToken(); setMe(null); setSelected(null); setUsers([]); setRequests([]);
  }

  if (loading) return <main className="loading-screen"><div className="spinner" /><p>بنجهّز مكتبك...</p></main>;
  if (new URLSearchParams(window.location.search).has('public') || new URLSearchParams(window.location.search).has('teacher')) return <PublicHome />;
  if (!me && !new URLSearchParams(window.location.search).has('login')) return <PublicHome />;
  if (!me) return <Login onLogin={async (token) => { setToken(token); setLoading(true); await refresh(); }} />;

  const roleLabel = { admin: 'إدارة المكتب', teacher: 'مساحة المدرس', designer: 'مساحة المصمم' }[me.role];
  const activeCount = requests.filter(r => !['completed', 'canceled'].includes(r.status)).length;
  return <div className="shell" dir="rtl">
    <aside className="sidebar">
      <div className="brand"><img className="brand-logo" src="/fhmny-logo-small.png" alt="شعار فهمني" /><div><strong>فهمني</strong><small>المكتب الإبداعي</small></div></div>
      <div className="side-caption">مساحة العمل</div>
      <nav aria-label="القائمة الرئيسية">
        <button className={view === 'requests' ? 'nav-link active' : 'nav-link'} onClick={() => { setView('requests'); setSelected(null); }}><LayoutDashboard size={19} /> الطلبات <span>{activeCount}</span></button>
        {me.role === 'admin' && <button className={view === 'team' ? 'nav-link active' : 'nav-link'} onClick={() => { setView('team'); setSelected(null); }}><Users size={19} /> المدرسون والمصممون</button>}
        {me.role === 'admin' && <button className={view === 'public' ? 'nav-link active' : 'nav-link'} onClick={() => { setView('public'); setSelected(null); }}><ExternalLink size={19} /> الصفحة العامة والباقات</button>}
      </nav>
      <div className="sidebar-bottom"><div className="user-initial">{me.name.slice(0, 1)}</div><div className="user-meta"><strong>{me.name}</strong><small>{roleLabel}</small></div><button className="icon-button" title="تسجيل الخروج" aria-label="تسجيل الخروج" onClick={logout}><LogOut size={19} /></button></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><div className="mobile-brand"><img className="mobile-logo" src="/fhmny-logo-small.png" alt="شعار فهمني" /><strong>المكتب الإبداعي</strong></div><span className="topbar-label">{roleLabel}</span><a className="topbar-platform" href="https://fhmny.site/" target="_blank" rel="noopener noreferrer">منصة فهمني <ExternalLink size={15}/></a><span className="topbar-user">{me.name}</span></header>
      <main id="main" className="main-content">
        {error && <div role="alert" className="alert error"><CircleHelp size={18}/>{error}<button onClick={() => setError('')} aria-label="إغلاق"><X size={16}/></button></div>}
        {notice && <div role="status" className="alert success"><Check size={18}/>{notice}<button onClick={() => setNotice('')} aria-label="إغلاق"><X size={16}/></button></div>}
        {selected ? <RequestDetail detail={selected} me={me} users={users} onBack={() => setSelected(null)} onRefresh={async () => { await refresh(); await openRequest(selected.id); }} onAction={action} onError={setError} />
          : view === 'team' && me.role === 'admin' ? <Team users={users} onRefresh={refresh} onError={setError} onNotice={setNotice} />
          : view === 'public' && me.role === 'admin' ? <PublicAdmin />
          : <>
            <div className="page-heading"><div><p className="eyebrow">{me.role === 'admin' ? 'نظرة على المكتب' : 'مساحة عملك'}</p><h1>{me.role === 'teacher' ? `أهلًا، ${me.name.split(' ')[0]}` : me.role === 'designer' ? 'طلباتك الإبداعية' : 'كل الطلبات'}</h1><p className="muted">{me.role === 'teacher' ? 'كل فكرة تبدأ بطلب واضح، ونكمل تفاصيلها مع المصمم هنا.' : 'تابع حالة كل طلب ومحادثاته من مكان واحد.'}</p></div>{me.role === 'teacher' && <button className="button primary" onClick={() => setShowNew(true)}><Plus size={18}/> طلب جديد</button>}</div>
            {me.role === 'teacher' && me.quotas && <div className="quota-grid"><QuotaCard label="تصميمات الصور" quota={me.quotas.image} icon={<FileImage size={21}/>} /><QuotaCard label="مونتاج الفيديو" quota={me.quotas.video} icon={<Film size={21}/>} /></div>}
            <div className="section-head"><div><h2>الطلبات</h2><p>{requests.length ? `${requests.length} طلب في مكتبك` : 'لسه مفيش طلبات هنا'}</p></div></div>
            {requests.length ? <div className="request-list">{requests.map(item => <button key={item.id} className="request-row" onClick={() => void openRequest(item.id)}><span className={`kind-icon ${item.kind}`}>{item.kind === 'image' ? <FileImage size={21}/> : <Film size={21}/>}</span><span className="request-info"><strong>{item.title}</strong><small>{kindText[item.kind]} · طلب #{item.id} · {new Date(item.updated_at).toLocaleDateString('ar-EG')}</small></span><span className={`status status-${item.status}`}>{statusText[item.status]}</span><ArrowLeft size={17} className="row-arrow" /></button>)}</div>
              : <div className="empty-state"><div className="empty-icon"><MessageCircle size={28}/></div><h3>مساحة الأفكار لسه فاضية</h3><p>{me.role === 'teacher' ? 'ابدأ بطلب تصميم أو فيديو واكتب كل التفاصيل اللي محتاجها.' : 'الطلبات المسندة ليك هتظهر هنا أول ما تتضاف.'}</p>{me.role === 'teacher' && <button className="button primary" onClick={() => setShowNew(true)}><Plus size={18}/> ابدأ أول طلب</button>}</div>}
          </>}
      </main>
      <FhmnyFooter />
    </div>
    {showNew && <NewRequest onClose={() => setShowNew(false)} onCreated={async (id) => { setShowNew(false); await refresh(); await openRequest(id); }} onError={setError} />}
  </div>;
}

function Login({ onLogin }: { onLogin: (token: string) => Promise<void> }) {
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) { e.preventDefault(); setBusy(true); setError(''); try { const result = await post<{ token: string }>('/login', { email, password }); await onLogin(result.token); } catch (err) { setError((err as Error).message); } finally { setBusy(false); } }
  return <><main className="login-page" dir="rtl"><div className="login-frame"><div className="login-story"><div className="brand"><img className="brand-logo" src="/fhmny-logo-small.png" alt="شعار فهمني" /><div><strong>فهمني</strong><small>المكتب الإبداعي</small></div></div><div><span className="story-chip">من الفكرة للتسليم</span><h1>كل شغلك الإبداعي<br/>في مكان واحد.</h1><p>اطلب، اتكلم مع المصمم، راجع النسخة، وتابع رصيد الصور والفيديوهات بوضوح.</p></div><div className="story-footer">مساحة خاصة لمدرسي ومصممي فهمني</div></div><div className="login-form-panel"><div className="login-form-wrap"><h2>سجّل دخولك</h2><p>ادخل بحساب المكتب الإبداعي للمتابعة.</p><form onSubmit={submit}><label>البريد الإلكتروني<input type="email" required autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} placeholder="name@example.com" dir="ltr" /></label><label>كلمة المرور<input type="password" required autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" dir="ltr" /></label>{error && <div className="form-error" role="alert">{error}</div>}<button className="button primary full" disabled={busy}>{busy ? 'جاري الدخول...' : 'دخول المكتب'}<ArrowLeft size={18}/></button></form><p className="login-support">معندكش حساب؟ <a href="/">شوف الباقات</a> واختار اللي يناسبك، وبعدها <a href="https://wa.me/201553902490" target="_blank" rel="noopener noreferrer">كلم الدعم على واتساب: 01553902490</a> والإدارة تفتح لك الحساب.</p></div></div></div></main><FhmnyFooter /></>;
}

function FhmnyFooter() {
  return <footer className="fhmny-footer" dir="rtl"><div className="fhmny-footer-inner"><div className="footer-intro"><div className="footer-logo-box"><img src="/fhmny-logo.png" alt="لوجو منصة فهمني" /></div><div><p className="footer-eyebrow">منظومة فهمني</p><h2>مساحة واحدة، أدوات تكمل شغل المدرس.</h2><p>الـDesk ينظم طلبات التصميم والمونتاج. منصة فهمني تقدم للمدرس مساحة للمحتوى والكورسات والامتحانات، وتطبيق التحضير يساعده في إدارة يوم السنتر ومتابعة طلابه.</p></div></div><div className="footer-products"><div className="footer-product"><span>منصة فهمني</span><h3>التعليم الأونلاين</h3><p>كورساته ومحتواه وامتحاناته في تجربة رقمية للمدرس والطالب.</p><a href="https://fhmny.site/" target="_blank" rel="noopener noreferrer">زيارة المنصة <ExternalLink size={16}/></a></div><div className="footer-product"><span>تطبيق التحضير</span><h3>شغل السنتر على الموبايل</h3><p>حضور QR أو يدوي، واجبات واختبارات وتقارير؛ يعمل دون إنترنت ويزامن البيانات عند عودة الاتصال.</p></div></div><div className="footer-end"><span>المكتب الإبداعي جزء مستقل من منظومة خدمات فهمني.</span><a href="https://fhmny.site/" target="_blank" rel="noopener noreferrer">fhmny.site</a></div></div></footer>;
}

function QuotaCard({ label, quota, icon }: { label: string; quota: NonNullable<User['quotas']>['image']; icon: ReactNode }) { return <div className="quota-card"><div className="quota-top"><span className="quota-icon">{icon}</span><span>{label}</span></div><div className="quota-main"><strong>{quota.available}</strong><span>متاح من {quota.total}</span></div><div className="quota-bar"><span style={{ width: quota.total ? `${((quota.completed + quota.reserved) / quota.total) * 100}%` : '0%' }} /></div><div className="quota-foot"><span>{quota.reserved} قيد التنفيذ</span><span>{quota.completed} مكتمل</span></div></div>; }

function NewRequest({ onClose, onCreated, onError }: { onClose: () => void; onCreated: (id: number) => void; onError: (message: string) => void }) {
  const [kind, setKind] = useState<Kind>('image'); const [title, setTitle] = useState(''); const [brief, setBrief] = useState(''); const [refs, setRefs] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) { e.preventDefault(); setBusy(true); try { const result = await post<DeskRequest>('/requests', { kind, title, brief, references: refs.split('\n').map(x => x.trim()).filter(Boolean) }); onCreated(result.id); } catch (err) { onError((err as Error).message); } finally { setBusy(false); } }
  return <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="new-title"><div className="modal-head"><div><p className="eyebrow">فكرة جديدة</p><h2 id="new-title">طلب إبداعي جديد</h2></div><button className="icon-button" onClick={onClose} aria-label="إغلاق"><X size={20}/></button></div><form onSubmit={submit} className="stack-form"><fieldset><legend>نوع الشغل</legend><div className="kind-picker"><button type="button" className={kind === 'image' ? 'kind-choice selected' : 'kind-choice'} onClick={() => setKind('image')}><FileImage size={20}/> تصميم صورة</button><button type="button" className={kind === 'video' ? 'kind-choice selected' : 'kind-choice'} onClick={() => setKind('video')}><Film size={20}/> مونتاج فيديو</button></div></fieldset><label>عنوان الطلب<input required minLength={3} maxLength={200} value={title} onChange={e => setTitle(e.target.value)} placeholder="مثال: بوست إعلان مراجعة نهاية الترم" /></label><label>اشرح اللي محتاجه<textarea required minLength={10} rows={5} value={brief} onChange={e => setBrief(e.target.value)} placeholder="اكتب النص، المقاسات، الألوان، موعد النشر، وأي تفاصيل تساعد المصمم..." /></label><label>روابط مراجع <small>اختياري — رابط في كل سطر</small><textarea rows={3} dir="ltr" value={refs} onChange={e => setRefs(e.target.value)} placeholder="https://..." /></label><div className="modal-actions"><button type="button" className="button ghost" onClick={onClose}>إلغاء</button><button className="button primary" disabled={busy}>{busy ? 'جاري الإرسال...' : 'إرسال الطلب'}<ArrowLeft size={18}/></button></div></form></section></div>;
}

function RequestDetail({ detail, me, users, onBack, onRefresh, onAction, onError }: { detail: DeskDetail; me: User; users: User[]; onBack: () => void; onRefresh: () => Promise<void>; onAction: (path: string, success: string) => Promise<void>; onError: (message: string) => void }) {
  const [message, setMessage] = useState(''); const [url, setUrl] = useState(''); const [label, setLabel] = useState(''); const [linkKind, setLinkKind] = useState<'draft' | 'final'>('draft'); const [busy, setBusy] = useState(false);
  async function send(e: FormEvent) { e.preventDefault(); setBusy(true); try { await post(`/requests/${detail.id}/messages`, { body: message }); setMessage(''); await onRefresh(); } catch (err) { onError((err as Error).message); } finally { setBusy(false); } }
  async function addLink(e: FormEvent) { e.preventDefault(); setBusy(true); try { await post(`/requests/${detail.id}/links`, { url, label, kind: linkKind }); setUrl(''); setLabel(''); await onRefresh(); } catch (err) { onError((err as Error).message); } finally { setBusy(false); } }
  const who = (id: number) => users.find(u => u.id === id)?.name || (id === me.id ? me.name : id === detail.teacher_id ? 'المدرس' : id === detail.designer_id ? 'المصمم' : 'الأدمن');
  const canWork = me.role === 'designer' || me.role === 'admin';
  return <><button className="back-link" onClick={onBack}>رجوع للطلبات <ArrowLeft size={17}/></button><div className="detail-heading"><div><div className="detail-kicker"><span>طلب #{detail.id}</span><span className="divider-dot"/><span>{kindText[detail.kind]}</span></div><h1>{detail.title}</h1><span className={`status status-${detail.status}`}>{statusText[detail.status]}</span></div><div className="detail-actions">{detail.status === 'submitted' && canWork && <button className="button primary" onClick={() => void onAction(`/requests/${detail.id}/accept`, 'تم قبول الطلب')}>قبول الطلب</button>}{detail.status === 'submitted' && me.role === 'teacher' && <button className="button ghost" onClick={() => void onAction(`/requests/${detail.id}/cancel`, 'تم إلغاء الطلب')}>إلغاء الطلب</button>}{['accepted', 'in_progress', 'revision_requested'].includes(detail.status) && me.role === 'designer' && <button className="button primary" onClick={() => void onAction(`/requests/${detail.id}/deliver`, 'تم التسليم وحسابه من الرصيد')}>تم التسليم</button>}{detail.status === 'completed' && me.role === 'teacher' && <button className="button ghost" onClick={() => void onAction(`/requests/${detail.id}/revise`, 'تم طلب تعديل')}>طلب تعديل</button>}{me.role === 'admin' && !['completed', 'canceled'].includes(detail.status) && <button className="button ghost" onClick={async () => { const reason = window.prompt('سبب إلغاء الطلب'); if (reason && reason.trim().length >= 3) { try { await post(`/admin/requests/${detail.id}/cancel`, { reason }); await onRefresh(); } catch (err) { onError((err as Error).message); } } }}>إلغاء إداري</button>}</div></div>
    <div className="detail-grid"><div className="detail-primary"><section className="surface"><div className="surface-title"><h2>وصف الطلب</h2></div><p className="brief-text">{detail.brief}</p></section><section className="surface conversation"><div className="surface-title"><h2>المحادثة</h2><span>{detail.messages.length} رسالة</span></div><div className="messages">{detail.messages.length ? detail.messages.map(m => <div className={m.author_id === me.id ? 'message own' : 'message'} key={m.id}><div className="message-meta"><strong>{who(m.author_id)}</strong><time>{new Date(m.created_at).toLocaleString('ar-EG')}</time></div><p>{m.body}</p></div>) : <div className="chat-empty"><MessageCircle size={25}/><p>اكتب أول رسالة لتوضيح أي تفاصيل في الطلب.</p></div>}</div><form onSubmit={send} className="message-compose"><label className="sr-only" htmlFor="message-input">رسالة جديدة</label><input id="message-input" required maxLength={5000} value={message} onChange={e => setMessage(e.target.value)} placeholder="اكتب سؤالك أو ملاحظتك هنا..."/><button disabled={busy || !message.trim()} aria-label="إرسال الرسالة" title="إرسال الرسالة"><Send size={20}/></button></form></section></div><aside className="detail-side"><section className="surface"><div className="surface-title"><h2>المشاركون</h2></div><div className="person-row"><span className="person-avatar">م</span><div><small>المدرس</small><strong>{who(detail.teacher_id)}</strong></div></div><div className="person-row"><span className="person-avatar alt">ص</span><div><small>المصمم</small><strong>{who(detail.designer_id)}</strong></div></div>{detail.teacher_profile?.subject && <p className="muted">المادة: {detail.teacher_profile.subject}</p>}{detail.teacher_profile && <div className="profile-links">{(['facebook', 'tiktok', 'youtube'] as const).map(key => detail.teacher_profile?.[key] ? <a key={key} href={detail.teacher_profile[key]!} target="_blank" rel="noopener noreferrer">{key}<ExternalLink size={13}/></a> : null)}</div>}</section><section className="surface"><div className="surface-title"><h2>الروابط والملفات</h2></div>{detail.links.length ? <div className="link-list">{detail.links.map(link => <a key={link.id} href={link.url} target="_blank" rel="noopener noreferrer" className="external-link"><span className="link-badge">{link.kind === 'reference' ? 'مرجع' : link.kind === 'draft' ? 'مسودة' : 'نهائي'}</span><span>{link.label}</span><ExternalLink size={16}/></a>)}</div> : <p className="muted">مفيش روابط في الطلب لسه.</p>}{me.role === 'designer' && ['accepted', 'in_progress', 'revision_requested'].includes(detail.status) && <form onSubmit={addLink} className="link-form"><h3>أضف رابط Drive</h3><label>نوع الرابط<select value={linkKind} onChange={e => setLinkKind(e.target.value as 'draft' | 'final')}><option value="draft">مسودة</option><option value="final">التسليم النهائي</option></select></label><label>اسم الرابط<input required value={label} onChange={e => setLabel(e.target.value)} placeholder="مثال: النسخة الأولى"/></label><label>رابط Google Drive<input required type="url" dir="ltr" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://drive.google.com/..."/></label><button className="button secondary full" disabled={busy}>إضافة الرابط</button></form>}</section></aside></div>
  </>;
}

function Team({ users, onRefresh, onError, onNotice }: { users: User[]; onRefresh: () => Promise<void>; onError: (s: string) => void; onNotice: (s: string) => void }) {
  const [name, setName] = useState(''); const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [role, setRole] = useState<'teacher' | 'designer'>('teacher'); const [subject, setSubject] = useState(''); const [facebook, setFacebook] = useState(''); const [tiktok, setTiktok] = useState(''); const [youtube, setYoutube] = useState(''); const [busy, setBusy] = useState(false);
  const [events, setEvents] = useState<Array<{ id: number; actor_id: number; request_id: number | null; action: string; detail: string; created_at: string }>>([]);
  useEffect(() => { void api<typeof events>('/admin/audit?limit=20').then(setEvents).catch(() => {}); }, [users]);
  const teachers = users.filter(u => u.role === 'teacher'), designers = users.filter(u => u.role === 'designer' && u.active);
  async function create(e: FormEvent) { e.preventDefault(); setBusy(true); try { await post('/users', { name, email, password, role, subject: role === 'teacher' ? subject : null, facebook: role === 'teacher' && facebook ? facebook : null, tiktok: role === 'teacher' && tiktok ? tiktok : null, youtube: role === 'teacher' && youtube ? youtube : null }); setName(''); setEmail(''); setPassword(''); setSubject(''); setFacebook(''); setTiktok(''); setYoutube(''); await onRefresh(); onNotice('تم إضافة الحساب'); } catch (err) { onError((err as Error).message); } finally { setBusy(false); } }
  async function assign(teacher: User, data: { designer_id: number; image_limit: number; video_limit: number }) { try { await patch(`/teachers/${teacher.id}/assignment`, data); await onRefresh(); onNotice('تم حفظ التكليف والرصيد'); } catch (err) { onError((err as Error).message); } }
  return <><div className="page-heading"><div><p className="eyebrow">إدارة الفريق</p><h1>المدرسون والمصممون</h1><p className="muted">أضف الحسابات، وحدد المصمم ورصيد كل مدرس.</p></div></div><div className="team-grid"><section className="surface team-list"><div className="surface-title"><h2>المدرسون</h2><span>{teachers.length}</span></div>{teachers.length ? teachers.map(teacher => <Assignment key={teacher.id} teacher={teacher} designers={designers} onSave={data => void assign(teacher, data)} />) : <p className="muted">أضف مدرسًا لبدء توزيع الطلبات.</p>}</section><section className="surface"><div className="surface-title"><h2>حساب جديد</h2></div><form onSubmit={create} className="stack-form"><label>نوع الحساب<select value={role} onChange={e => setRole(e.target.value as 'teacher' | 'designer')}><option value="teacher">مدرس</option><option value="designer">مصمم</option></select></label><label>الاسم<input required minLength={2} value={name} onChange={e => setName(e.target.value)}/></label><label>البريد الإلكتروني<input required type="email" dir="ltr" value={email} onChange={e => setEmail(e.target.value)}/></label><label>كلمة مرور أولية<input required type="password" minLength={8} value={password} onChange={e => setPassword(e.target.value)}/></label>{role === 'teacher' && <><label>المادة<input value={subject} onChange={e => setSubject(e.target.value)}/></label><label>رابط فيسبوك<input type="url" dir="ltr" value={facebook} onChange={e => setFacebook(e.target.value)} /></label><label>رابط تيك توك<input type="url" dir="ltr" value={tiktok} onChange={e => setTiktok(e.target.value)} /></label><label>رابط يوتيوب<input type="url" dir="ltr" value={youtube} onChange={e => setYoutube(e.target.value)} /></label></>}<button className="button primary full" disabled={busy}>{busy ? 'جاري الإضافة...' : 'إضافة الحساب'}<Plus size={17}/></button></form><div className="designer-list"><h3>المصممون الحاليون</h3>{users.filter(u => u.role === 'designer').map(u => <div className="designer-row" key={u.id}><span className="person-avatar alt">{u.name.slice(0, 1)}</span><span>{u.name}</span><small>{u.active ? 'نشط' : 'موقوف'}</small><button className="text-button" onClick={async () => { try { await patch(`/users/${u.id}/active?active=${!u.active}`, {}); await onRefresh(); } catch (err) { onError((err as Error).message); } }}>{u.active ? 'إيقاف' : 'تفعيل'}</button></div>)}</div></section></div><section className="surface audit-panel"><div className="surface-title"><h2>آخر نشاط في المكتب</h2><span>{events.length} حدث</span></div>{events.length ? events.map(event => <div className="audit-row" key={event.id}><span>{({ assignment_updated: 'تحديث إسناد ورصيد', created: 'طلب جديد', accept: 'قبول طلب', deliver: 'تسليم طلب', revise: 'طلب تعديل', cancel: 'إلغاء طلب', admin_cancel: 'إلغاء إداري' } as Record<string, string>)[event.action] || event.action}</span><small>{event.request_id ? `طلب #${event.request_id}` : event.detail}</small><time>{new Date(event.created_at).toLocaleString('ar-EG')}</time></div>) : <p className="muted">لا يوجد نشاط مسجل بعد.</p>}</section></>;
}

function Assignment({ teacher, designers, onSave }: { teacher: User; designers: User[]; onSave: (data: { designer_id: number; image_limit: number; video_limit: number }) => void }) {
  const [designerId, setDesignerId] = useState(teacher.designer_id || 0); const [images, setImages] = useState(teacher.image_limit); const [videos, setVideos] = useState(teacher.video_limit);
  return <div className="assignment"><div className="assignment-head"><span className="person-avatar">{teacher.name.slice(0, 1)}</span><div><strong>{teacher.name}</strong><small>{teacher.subject || teacher.email}</small></div></div><div className="assignment-summary"><span>الصور: {teacher.quotas?.image.completed ?? 0} مكتمل، {teacher.quotas?.image.reserved ?? 0} محجوز، {teacher.quotas?.image.available ?? teacher.image_limit} متاح</span><span>الفيديو: {teacher.quotas?.video.completed ?? 0} مكتمل، {teacher.quotas?.video.reserved ?? 0} محجوز، {teacher.quotas?.video.available ?? teacher.video_limit} متاح</span></div><div className="assignment-fields"><label>المصمم<select value={designerId} onChange={e => setDesignerId(Number(e.target.value))}><option value={0}>اختار المصمم</option>{designers.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label><label>صور<input type="number" min={0} value={images} onChange={e => setImages(Number(e.target.value))}/></label><label>فيديو<input type="number" min={0} value={videos} onChange={e => setVideos(Number(e.target.value))}/></label><button className="button secondary" disabled={!designerId} onClick={() => onSave({ designer_id: designerId, image_limit: images, video_limit: videos })}>حفظ</button></div></div>;
}

export default App;
