import { useEffect, useState, type FormEvent } from 'react';
import { api, patch, post } from './api';

type Teacher = { id: number; slug: string; name: string; subject: string; bio: string; facebook: string | null; tiktok: string | null; youtube: string | null; published: boolean };
type Work = { id: number; teacher_id: number | null; title: string; description: string; kind: string; url: string; published: boolean };
type Package = { id: number; name: string; description: string; price_egp: number; image_count: number; video_count: number; revision_count: number; delivery_days: number; featured: boolean; published: boolean };

export default function PublicAdmin() {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [works, setWorks] = useState<Work[]>([]);
  const [packages, setPackages] = useState<Package[]>([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  async function refresh() {
    const [t,w,p] = await Promise.all([api<Teacher[]>('/admin/public/teachers'),api<Work[]>('/admin/public/work'),api<Package[]>('/admin/public/packages')]);
    setTeachers(t); setWorks(w); setPackages(p);
  }
  useEffect(() => { void refresh().catch(e => setError((e as Error).message)); }, []);
  async function submit(e: FormEvent<HTMLFormElement>, path: string, build: (f: FormData) => object) {
    e.preventDefault();
    const form = e.currentTarget;
    try { await post(path, build(new FormData(form))); form.reset(); await refresh(); setMessage('تمت الإضافة'); setError(''); }
    catch (err) { setError((err as Error).message); }
  }
  async function toggle(path: string, item: Teacher | Work | Package) {
    try { await patch(`/admin/public/${path}/${item.id}`, {...item, published: !item.published}); await refresh(); setMessage(item.published ? 'تم إخفاء العنصر' : 'تم نشر العنصر'); setError(''); }
    catch (err) { setError((err as Error).message); }
  }
  return <><div className="page-heading"><div><p className="eyebrow">المحتوى العام</p><h1>الصفحة العامة والباقات</h1><p className="muted">أضف اللي تحب تعرضه للزوار. الطلبات والمحادثات الخاصة لا تُنشر تلقائيًا.</p></div><a className="button secondary" href="/?public=1" target="_blank" rel="noopener noreferrer">شوف الصفحة العامة ↗</a></div>{error && <div className="alert error" role="alert">{error}</div>}{message && <div className="alert success" role="status">{message}</div>}<div className="public-admin-grid">
    <section className="surface"><div className="surface-title"><h2>باقة جديدة</h2></div><form className="stack-form" onSubmit={e => void submit(e, '/admin/public/packages', f => ({name:f.get('name'),description:f.get('description'),price_egp:Number(f.get('price_egp')),delivery_days:Number(f.get('delivery_days')),image_count:Number(f.get('image_count')),video_count:Number(f.get('video_count')),revision_count:Number(f.get('revision_count')),featured:f.has('featured'),published:f.has('published')}))}><label>اسم الباقة<input name="name" required minLength={2}/></label><label>وصف الباقة<textarea name="description" required minLength={10} rows={3}/></label><div className="form-two"><label>السعر بالجنيه<input name="price_egp" type="number" min={0} step="0.01" required/></label><label>مدة التسليم بالأيام<input name="delivery_days" type="number" min={1} required/></label></div><div className="form-three"><label>صور<input name="image_count" type="number" min={0} required/></label><label>فيديوهات<input name="video_count" type="number" min={0} required/></label><label>تعديلات<input name="revision_count" type="number" min={0} required/></label></div><label className="checkline"><input name="featured" type="checkbox"/> باقة مميزة</label><label className="checkline"><input name="published" type="checkbox"/> انشر الباقة الآن</label><button className="button primary full">إضافة الباقة</button></form></section>
    <section className="surface"><div className="surface-title"><h2>صفحة مدرس جديدة</h2></div><form className="stack-form" onSubmit={e => void submit(e, '/admin/public/teachers', f => ({name:f.get('name'),slug:f.get('slug'),subject:f.get('subject'),bio:f.get('bio'),facebook:f.get('facebook')||null,tiktok:f.get('tiktok')||null,youtube:f.get('youtube')||null,published:f.has('published')}))}><label>اسم المدرس<input name="name" required minLength={2}/></label><label>رابط الصفحة بالإنجليزي<input name="slug" dir="ltr" pattern="[a-z0-9]+(-[a-z0-9]+)*" placeholder="ahmed-ibrahim" required/></label><label>المادة<input name="subject" required minLength={2}/></label><label>تعريف قصير<textarea name="bio" required minLength={10} rows={3}/></label><label>Facebook اختياري<input name="facebook" type="url" dir="ltr"/></label><label>TikTok اختياري<input name="tiktok" type="url" dir="ltr"/></label><label>YouTube اختياري<input name="youtube" type="url" dir="ltr"/></label><label className="checkline"><input name="published" type="checkbox"/> انشر الصفحة الآن</label><button className="button primary full">إضافة صفحة المدرس</button></form></section>
    <section className="surface"><div className="surface-title"><h2>نموذج شغل جديد</h2></div><form className="stack-form" onSubmit={e => void submit(e, '/admin/public/work', f => ({title:f.get('title'),description:f.get('description'),kind:f.get('kind'),teacher_id:f.get('teacher_id')?Number(f.get('teacher_id')):null,url:f.get('url'),published:f.has('published')}))}><label>العنوان<input name="title" required minLength={3}/></label><label>الوصف<textarea name="description" required minLength={10} rows={3}/></label><label>النوع<select name="kind"><option value="image">تصميم صورة</option><option value="video">مونتاج فيديو</option><option value="link">رابط آخر</option></select></label><label>المدرس<select name="teacher_id"><option value="">بدون مدرس</option>{teachers.map(t => <option value={t.id} key={t.id}>{t.name}</option>)}</select></label><label>رابط العمل HTTPS<input name="url" type="url" dir="ltr" required/></label><label className="checkline"><input name="published" type="checkbox"/> انشر النموذج الآن</label><button className="button primary full">إضافة النموذج</button></form></section>
  </div><div className="public-admin-grid public-admin-lists">
    <section className="surface"><div className="surface-title"><h2>الباقات الحالية</h2><span>{packages.length}</span></div>{packages.map(p => <div className="admin-public-row" key={p.id}><div><strong>{p.name}</strong><small>{Number(p.price_egp).toLocaleString('ar-EG')} جنيه · {p.image_count} صور · {p.video_count} فيديو</small></div><button className="text-button" onClick={() => void toggle('packages',p)}>{p.published?'إخفاء':'نشر'}</button></div>)}</section>
    <section className="surface"><div className="surface-title"><h2>صفحات المدرسين</h2><span>{teachers.length}</span></div>{teachers.map(t => <div className="admin-public-row" key={t.id}><div><strong>{t.name}</strong><small>{t.subject} · {t.slug}</small></div><button className="text-button" onClick={() => void toggle('teachers',t)}>{t.published?'إخفاء':'نشر'}</button></div>)}</section>
    <section className="surface"><div className="surface-title"><h2>نماذج الشغل</h2><span>{works.length}</span></div>{works.map(w => <div className="admin-public-row" key={w.id}><div><strong>{w.title}</strong><small>{w.kind}</small></div><button className="text-button" onClick={() => void toggle('work',w)}>{w.published?'إخفاء':'نشر'}</button></div>)}</section>
  </div></>;
}
