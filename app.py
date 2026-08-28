import json
import requests
import streamlit as st
from google import genai
from google.genai import types

# ==========================================
# 1. إعدادات الصفحة والهوية البصرية الرسمية لمسمار
# ==========================================
st.set_page_config(
    page_title="نظام تدقيق الطلبات والجودة | مسمار MisMar",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تطبيق التنسيقات البصرية والهوية (CSS)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
    
    html, body, [class*="css"] {
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

# ==========================================
# 2. روابط Metabase لجلب بيانات الطلبات
# ==========================================
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

# ==========================================
# 3. القائمة الجانبية والشعار
# ==========================================
with st.sidebar:
    st.image("https://mismarapp.com/static/media/logo.f6cf70e4.svg", width=200)
    st.markdown("### ⚙️ إعدادات النظام")
    
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    api_key_input = st.text_input("Gemini API Key", value=secret_key, type="password")

    api_key = api_key_input.strip() if api_key_input else secret_key.strip()

    if not api_key:
        st.warning("⚠️ يرجى إدخال Gemini API Key للبدء.")

    st.markdown("---")
    st.info("💡 هذا التطبيق مخصص لفريق الجودة والتدقيق التشغيلي لتسهيل تحليل الأسباب الجذرية لتقييمات العملاء.")

# ==========================================
# 4. الواجهة الرئيسية وإدخال التقييمات
# ==========================================
st.markdown("""
<div class="mismar-header">
    <h1>🔍 نظام تدقيق الطلبات وتجربة العملاء (MisMar CX Audit)</h1>
    <p>استخراج التبريرات التشغيلية والأسباب الجذرية بدقة مدعومة بالذكاء الاصطناعي</p>
</div>
""", unsafe_allow_html=True)

col_input, col_result = st.columns([1, 1], gap="large")

with col_input:
    st.subheader("📋 بيانات الطلب والتقييمات")
    
    order_id = st.number_input("رقم الطلب (Order ID)", min_value=1000000, max_value=9999999, value=1034406, step=1)
    
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

# ==========================================
# 5. منطق التحليل واستدعاء نموذج الذكاء الاصطناعي
# ==========================================
if analyze_btn:
    if not api_key:
        st.error("❌ لا يمكن إجراء التحليل بدون إدخال المفتاح!")
    else:
        with st.spinner("⏳ جاري سحب بيانات الطلب والجداول والجنايات الرقمية وتحليلها..."):
            try:
                # 1. سحب بيانات Metabase الفعلية للطلب
                order_data = fetch_order_data(order_id)
                ratings_context = f"تقييمات العميل المدخلة للطلب: {sample_ratings}\n"

                # 2. بناء البرومبت الشامل المزود بالبيانات المباشرة
                prompt_text = f"""
                أنت كبير مدققي العمليات وتجربة العملاء (Senior Operations & CX Forensic Auditor) في شركة صيانة السيارات (مسمار - MisMar).
                وظيفتك إجراء فحص ودراسة جنائية تشغيلية متكاملة لبيانات الطلب رقم #{order_id} للوصول للسبب الجذر المباشر خلف التقييم المنخفض.

                {ratings_context}

                البيانات المتاحة للطلب من النظام:
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
                - 🛑 يُمنع تماماً البدء بذكر أو سرد درجات التقييمات مثل: (يعود سبب تقييم العميل للسعر بـ 2/5 والوقت بـ 3/5...).
                - 🛑 يُمنع تماماً استخدام جمل فضفاضة مثل "بسبب كثرة عروض الأسعار والارتباك" دون ذكر السبب الحقيقي الذي أدى لرفض العروض.
                - 🟢 ابدأ فوراً وبشكل مباشر بالسبب الحقيقي المستخرج من التذاكر والشات.
                - 🔍 البحث عن السبب الجذر للأسعار: اربط اعتراض السعر بالنص المكتوب داخل التذاكر (مثل: اعتراض العميل على ارتفاع أجور اليد مقارنة بأسعار السوق، إضافة قطع اختيارية بشكل مفاجئ، أو الخلاف على تسعير قطع التشليح).
                - 🔍 البحث عن السبب الجذر للتأخير: ارجع لتعليقات الشات والتسلسل الزمني لتحديد المتسبب الفعلي في التأخير (مثل: تأخر المركز في التشخيص المبدئي، أو تأخر توريد القطع من المورد).
                - يُمنع استخدام القوائم، العناوين، أو أرقام التذاكر والعروض الداخلية (مثل #658323).

                ===SPLIT===

                القسم الثاني: [الأدلة والوقائع التفصيلية والربط الزمني]
                - اكتب هنا بتفصيل كامل وبلا حدود للحجم كافة الأدلة والحقائق المستخرجة من البيانات الأربعة التي أدت للصياغة أعلاه:
                  1. ⏱️ التحليل الزمني للدلتا (Timeline Deltas): احسب بدقة كم استغرق رفع عرض السعر بعد طلب التسعير، وكم استغرقت الحالة الأكثر تأخيراً.
                  2. 🎫 أدلة التذاكر: اقتبس نصوص الشكوى (`description`) ونتيجة التذكرة (`result`) كلمة بكلمة.
                  3. 💬 أدلة الشات: اذكر رسائل المفاوضات ومحادثات مركز الصيانة بالنص مع التوقيت.
                  4. 💰 تحليل التسعير: حدد فروق الأسعار، اعتراضات أجور اليد مقابل قطع الغيار، وسبب رفض العروض المبدئية.
                """

                # 3. إعداد العميل واستخدام آلية الكشف والمرونة المتعددة للنماذج (المرشحين)
                client = genai.Client(api_key=api_key)

                candidate_models = [
                    "gemini-2.5-flash",
                    "gemini-2.5-flash-lite",
                    "gemini-1.5-flash",
                ]

                def get_working_model():
                    try:
                        available = {m.name.split("/")[-1] for m in client.models.list()}
                    except Exception:
                        available = None

                    if available:
                        for name in candidate_models:
                            if name in available:
                                return name
                        for name in sorted(available):
                            if "flash" in name and "flash-lite" not in name:
                                return name
                        for name in sorted(available):
                            if "flash" in name:
                                return name

                    return candidate_models[0]

                model_name = get_working_model()
                response = None

                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt_text,
                        config=types.GenerateContentConfig(
                            temperature=0.3,
                            top_p=0.9
                        )
                    )
                except Exception:
                    last_error = None
                    for name in candidate_models:
                        if name == model_name:
                            continue
                        try:
                            response = client.models.generate_content(
                                model=name,
                                contents=prompt_text,
                                config=types.GenerateContentConfig(
                                    temperature=0.3,
                                    top_p=0.9
                                )
                            )
                            break
                        except Exception as e2:
                            last_error = e2
                            continue
                    if response is None:
                        raise last_error if last_error else Exception("لا يوجد موديل متاح حالياً")

                ai_text = response.text

                if "===SPLIT===" in ai_text:
                    parts = ai_text.split("===SPLIT===")
                    justification = parts[0].strip() if len(parts) > 0 else ai_text
                    details = parts[1].strip() if len(parts) > 1 else ""
                else:
                    justification = ai_text
                    details = ""

                st.session_state["audit_result"] = {
                    "justification": justification,
                    "evidence": details,
                    "order_id": order_id
                }
                st.success("✅ تم الفحص والتحليل بنجاح!")

            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء الاتصال بالذكاء الاصطناعي أو سحب البيانات: {str(e)}")

# ==========================================
# 6. عرض النتائج والتقارير
# ==========================================
with col_result:
    st.subheader("📊 مخرجات التقرير والتدقيق")
    
    if "audit_result" in st.session_state and st.session_state["audit_result"]:
        res = st.session_state["audit_result"]
        
        st.markdown("##### 📝 التبرير التشغيلي (جاهز للنسخ لمدير العمليات):")
        st.markdown(f'<div class="justification-card">{res["justification"]}</div>', unsafe_allow_html=True)
        
        st.text_area("📋 حدد النص بالكامل للنسخ السريع (Ctrl+A -> Ctrl+C):", value=res["justification"], height=130)

        st.markdown("##### 🔍 الأدلة والوقائع التفصيلية ومحطات الربط الزمني:")
        st.markdown(f'<div class="evidence-card">{res["evidence"]}</div>', unsafe_allow_html=True)
    else:
        st.info("👈 قم بإدخال رقم الطلب والتقييمات، ثم اضغط على زر التحليل لتعرض النتائج هنا.")
