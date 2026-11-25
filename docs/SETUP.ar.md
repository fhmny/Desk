# تشغيل Creative Desk محليًا

## المتطلبات

Python 3.10+ وNode.js 20+، وشبكة تسمح بتنزيل حزم `pip` و`npm` عند أول تثبيت. كل أوامر التشغيل من داخل `desk/`، ولا تحتاج تعديل مشاريع فهمني الأخرى.

## تشغيل الباك

من `desk/backend`:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DESK_DATABASE_URL = 'sqlite:///./desk.db'
$env:DESK_CORS_ORIGINS = 'http://localhost:5173'
$env:DESK_SETUP_KEY = 'ضع-سرًا-طويلًا-عشوائيًا-هنا'
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

الخدمة تنشئ قاعدة SQLite تلقائيًا عند بدء التشغيل. واجهة API التفاعلية: `http://localhost:8000/docs`.

## إنشاء أول أدمن

هذه العملية تعمل مرة واحدة فقط، وتتطلب قيمة `DESK_SETUP_KEY` نفسها في الترويسة `X-Setup-Key`. مثال PowerShell:

```powershell
$body = @{ name='Admin'; email='admin@example.com'; password='كلمة-مرور-قوية-هنا'; role='admin' } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/desk/setup' -Method Post -ContentType 'application/json' -Headers @{ 'X-Setup-Key'=$env:DESK_SETUP_KEY } -Body $body
```

بعد إنشاء الأدمن، ادخل من الواجهة وأضف المصممين والمدرسين، ثم حدد مصممًا ورصيد الصور والفيديو لكل مدرس. لا تشارك سر الإعداد أو تضعه في Git.

## تشغيل الفرونت

من `desk/frontend`:

```powershell
npm.cmd install
npm.cmd run dev
```

الواجهة على `http://localhost:5173`. Vite يمرر طلبات `/api` محليًا إلى باك المنفذ `8000`. عند نشر الواجهة على أصل مختلف، اضبط `VITE_API_URL` و`DESK_CORS_ORIGINS` وفق العنوان الفعلي. الصور والفيديوهات تُفتح من Google Drive عبر الروابط؛ لا يتم رفعها إلى السيرفر.

## الاختبارات

من `desk/backend`: `py -3 -m pytest -q`. اختبارات التدفق تغطي صلاحيات الأدوار، عزل المصممين، المحادثة، الرصيد، التسليم، التعديل والإلغاء.

## قبل الإنتاج

استخدم قاعدة بيانات مدارة ونسخًا احتياطية، HTTPS، سر إعداد قوي، وحدود طلبات على الدخول والإعداد، وضبط CORS على أصل الواجهة فقط. يلزم اختبار القبول المتزامن لطلبات الرصيد قبل تشغيل عدة عمال أو بيع الباقات؛ SQLite المحلي مخصص للتطوير والتجربة الأولى. قرار ربط الدخول بحسابات المنصة مؤجل، ويحتاج تصميمًا منفصلًا قبل إضافته.
