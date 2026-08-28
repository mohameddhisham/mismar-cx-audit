import json
import os
import requests
import streamlit as st

# إعدادات الصفحة الرسمية لمسمار
st.set_page_config(
    page_title="نظام تدقيق الطلبات والجودة | مسمار MisMar",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    .stApp {
        background-color: #0B0F19;
        color: #F3F4F6;
    }
    
    .mismar-header {
        background: linear-gradient(135deg, #064E3B 0%, #0F172A 100%);
        padding: 28px;
        border-radius: 20px;
        border: 1px solid #10B98133;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        margin-bottom: 28px;
        text-align: center;
    }
    
    .mismar-header h1 {
        color: #10B981;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 8px;
    }

    .mismar-header p {
        color: #9CA3AF;
        font-size: 1.05rem;
    }

    .justification-card {
        background: linear-gradient(180deg, #111827 0%, #1F2937 100%);
        border-right: 6px solid #10B981;
        padding: 22px;
        border-radius: 14px;
        font-size: 1.15rem;
        line-height: 1.95;
        color: #F9FAFB;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        margin-bottom: 16px;
    }
    
    .evidence-card {
        background-color: #111827;
        border: 1px solid #374151;
        padding: 22px;
        border-radius: 14px;
        color: #D1D5DB;
        line-height: 1.8;
        white-space: pre-wrap;
    }

    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #10B981 0%, #059669 100%);
        color: #FFFFFF;
        font-weight: 700;
        font-size: 1.15rem;
        padding: 14px;
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background: linear-gradient(90deg, #059669 0%, #047857 100%);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

METABASE_ENDPOINTS = {
    "tickets": "https://analysis.mismarapp.com/public/question/5f313cbe-6bb4-43bc-9b4d-70b8de7d17d4.json",
    "comments": "https://analysis.mismarapp.com/public/question/82aba25f-d368-44e3-8392-dce163d78e23.json",
    "status_history": "https://analysis.mismarapp.com/public/question/98fe13e6-298a-4775-8244-3015c9c720fe.json",
    "pricing": "https://analysis.mismarapp.com/public/question/b0114e1f-8577-4faa-a790-eaa2412f39f6.json"
}

def fetch_order_data(order_id: int) -> dict:
    """جلب بيانات الطلب الكاملة من المصادر الأربعة في Metabase"""
    payload = {}
    for key, url in METABASE_ENDPOINTS.items():
        try:
            res = requests.get(f"{url}?order_id={order_id}", timeout=15)
            payload[key] = res.json() if res.status_code == 200 else f"Error HTTP {res.status_code}"
        except Exception as e:
            payload[key] = f"Error: {str(e)}"
    return payload

def analyze_order_rating(api_key: str, order_id: int, ratings: dict) -> str:
    order_data = fetch_order_data(order_id)
    ratings_context = f"تقييمات العميل المدخلة للطلب: {ratings}\n" if ratings else ""

    prompt_text = f"""
    أنت كبير مدققي العمليات وتجربة العملاء (Senior Operations & CX Forensic Auditor) في شركة صيانة السيارات (مسمار - MisMar).
    وظيفتك إجراء فحص ودراسة جنائية تشغيلية متكاملة لبيانات الطلب رقم #{order_id} للوصول للسبب الجذر المباشر خلف التقييم المنخفض.

    {ratings_context}

    البيانات المتاحة للطلب:
    1. 🎫 تذاكر الشكاوى والمتابعة (افحص خانة Description، خانة Result، تواريخ الإنشاء والإغلاق، واسم قسم التذكرة): 
    {json.dumps(order_data.get('tickets'), ensure_ascii=False, indent=2)}

    2. 💬 محادثات الشات والتعليقات الداخلية (افحص نصوص المحادثات بين التشغيل والمركز والعميل، التواقيت، هوية المُرسل، تفاصيل المفاوضات وأجور اليد): 
    {json.dumps(order_data.get('comments'), ensure_ascii=False, indent=2)}

    3. ⏱️ التسلسل الزمني للحالات والمدد (احسب المدة بين كل حالة وأخرى بالدقيقة والساعة واكتشف محطات التعطيل): 
    {json.dumps(order_data.get('status_history'), ensure_ascii=False, indent=2)}

    4. 💰 طلبات التسعير وعروض الأسعار (افحص الفارق الزمني بين طلب التسعير ورفع عرض السعر، تفاصيل قطع الغيار مقابل أجور اليد، العروض المرفوضة والمقبولة): 
    {json.dumps(order_data.get('pricing'), ensure_ascii=False, indent=2)}

    === 🎯 تعليمات وقواعد الصياغة الصارمة ===
    قم بتقسيم إجابتك إلى قسمين يفصل بينهما السطر `===SPLIT===`:

    القسم الأول: [التبرير التشغيلي المباشر لمدير العمليات]
    - فقرة واحدة متصلة ومباشرة فقط (من 4 إلى 5 سطور كحد أقصى).
    - 🛑 **يُمنع تماماً** البدء بذكر أو سرد درجات التقييمات مثل: (يعود سبب تقييم العميل للسعر بـ 2/5 والوقت بـ 3/5...).
    - 🛑 **يُمنع تماماً** استخدام جمل فضفاضة مثل "بسبب كثرة عروض الأسعار والارتباك" دون ذكر السبب الحقيقي الذي أدى لرفض العروض.
    - 🟢 **ابدأ فوراً وبشكل مباشر** بالسبب الحقيقي المستخرج من التذاكر والشات.
    - 🔍 **البحث عن السبب الجذر للأسعار:** اربط اعتراض السعر بالنص المكتوب داخل التذاكر (مثل: اعتراض العميل على ارتفاع أجور اليد مقارنة بأسعار السوق، إضافة قطع اختيارية بشكل مفاجئ دون استشارة العميل، أو الخلاف على تسعير قطع التشليح).
    - 🔍 **البحث عن السبب الجذر للتأخير:** ارجع لتعليقات الشات والتسلسل الزمني لتحديد المتسبب الفعلي في التأخير (مثل: تأخر المركز في التشخيص المبدئي، أو تأخر توريد القطع من المورد).
    - يُمنع استخدام القوائم، العناوين، أو أرقام التذاكر والعروض الداخلية (مثل #658323).

    ===SPLIT===

    القسم الثاني: [الأدلة والوقائع التفصيلية والربط الزمني]
    - اكتب هنا بتفصيل كامل وبلا حدود للحجم كافة الأدلة والحقائق المستخرجة من البيانات الأربعة التي أدت للصياغة أعلاه:
      1. ⏱️ التحليل الزمني للدلتا (Timeline Deltas): احسب بدقة كم استغرق رفع عرض السعر بعد طلب التسعير، وكم استغرقت الحالة الأكثر تأخيراً.
      2. 🎫 أدلة التذاكر: اقتبس نصوص الشكوى (`description`) ونتيجة التذكرة (`result`) كلمة بكلمة (مثل شكاوى أجور اليد والمقارنة بالسوق).
      3. 💬 أدلة الشات: اذكر رسائل المفاوضات ومحادثات مركز الصيانة بالنص مع التوقيت.
      4. 💰 تحليل التسعير: حدد فروق الأسعار، اعتراضات أجور اليد مقابل قطع الغيار، وسبب رفض العروض المبدئية.
    """

    # قائمة موديلات مرشحة بالترتيب (الأحدث أولاً). لو موديل معين اتلغى أو رجّع 404،
    # الكود بيجرب اللي بعده تلقائياً من غير ما يوقف التطبيق.
    candidate_models = [
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-3-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
    ]

    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': api_key
    }
    data = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.3,  # درجة منخفضة للالتزام التام بالحقائق وتجنب التخمين
            "topP": 0.9
        }
    }

    last_error = None
    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            result_json = response.json()
            return result_json['candidates'][0]['content']['parts'][0]['text']

        # لو الموديل مش موجود (404) أو مش متاح، جرب اللي بعده في القائمة
        last_error = f"خطأ في الاتصال بالذكاء الاصطناعي ({response.status_code}) عبر موديل {model_name}: {response.text}"
        if response.status_code == 404:
            continue
        else:
            raise Exception(last_error)

    raise Exception(last_error if last_error else "لم يتم العثور على أي موديل متاح من قائمة المرشحين.")

with st.sidebar:
    st.image("https://mismarapp.com/static/media/logo.f6cf70e4.svg", width=200)
    st.markdown("### ⚙️ إعدادات النظام")
    
    api_key_input = st.text_input(
        "Gemini API Key",
        value="AQ.Ab8RN6L4I0YRUhlGT12J8V0u5DlZM6-sC4vzt3XcXhkU3fq0Zw",
        type="password",
        help="أدخل مفتاح الـ API الخاص بـ Gemini"
    )

st.markdown("""
<div class="mismar-header">
    <h1>🔍 نظام تدقيق الطلبات وتجربة العملاء (MisMar CX Audit)</h1>
    <p>استخراج التبريرات التشغيلية والأسباب الجذرية بدقة مدعومة بالذكاء الاصطناعي</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📋 بيانات الطلب والتقييمات")
    order_id = st.number_input("رقم الطلب (Order ID)", value=1034406, step=1)
    
    st.markdown("##### ⭐️ تقييمات العميل المدخلة:")
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        time_rating = st.slider("الوقت ⏱️", 1, 5, 5)
        price_rating = st.slider("السعر 💰", 1, 5, 3)
        quality_rating = st.slider("الجودة 🛠️", 1, 5, 5)
    with col_r2:
        cs_rating = st.slider("خدمة العملاء 🎧", 1, 5, 5)
        overall_rating = st.slider("التقييم العام ⭐️", 1, 5, 5)

    sample_ratings = {
        "الوقت": time_rating,
        "السعر": price_rating,
        "الجودة": quality_rating,
        "خدمة العملاء": cs_rating,
        "التقييم العام": overall_rating
    }
    
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🚀 بدء التدقيق العميق واستخراج التبرير")

with col2:
    st.subheader("📊 مخرجات التقرير والتدقيق")
    
    if analyze_btn:
        if not api_key_input:
            st.error("⚠️ يرجى إدخال Gemini API Key أولاً من القائمة الجانبية.")
        else:
            with st.spinner("⏳ جاري الفحص الجنائي الرقمي لبيانات الطلب والتذاكر والمحادثات..."):
                try:
                    full_response = analyze_order_rating(api_key_input, order_id, sample_ratings)
                    
                    if "===SPLIT===" in full_response:
                        justification, evidence = full_response.split("===SPLIT===", 1)
                    else:
                        justification = full_response
                        evidence = "لم يتم تفكيك الأدلة بشكل منفصل."

                    clean_justification = justification.strip()

                    st.session_state['audit_result'] = {
                        'justification': clean_justification,
                        'evidence': evidence.strip(),
                        'order_id': order_id,
                    }

                except Exception as e:
                    st.error(f"❌ حدث خطأ أثناء التحليل: {str(e)}")

    if 'audit_result' in st.session_state and st.session_state['audit_result']:
        res = st.session_state['audit_result']
        
        st.markdown("### 📝 التبرير التشغيلي (جاهز للنسخ لمدير العمليات):")
        st.markdown(f'<div class="justification-card">{res["justification"]}</div>', unsafe_allow_html=True)
        
        st.text_area("📋 اضغط Ctrl+A ثم Ctrl+C للنسخ المباشر:", value=res["justification"], height=120)

        st.markdown("### 🔍 الأدلة والوقائع التفصيلية ومحطات الربط الزمني:")
        st.markdown(f'<div class="evidence-card">{res["evidence"]}</div>', unsafe_allow_html=True)
    elif not analyze_btn:
        st.info("👈 قم بإدخال رقم الطلب والضغط على زر التحليل لعرض النتائج هنا.")
