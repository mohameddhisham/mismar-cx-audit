import json
import html
from typing import Any

import requests
import streamlit as st
from groq import Groq

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="نظام تدقيق الطلبات والجودة | مسمار MisMar",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap'
    );

    html,
    body,
    [class*="css"] {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        text-align: right;
    }

    .stApp {
        background-color: #0B0F19;
        color: #F3F4F6;
    }

    .mismar-header {
        background: linear-gradient(
            135deg,
            #064E3B 0%,
            #0F172A 100%
        );

        padding: 30px;
        border-radius: 20px;

        border: 1px solid rgba(
            16,
            185,
            129,
            0.25
        );

        box-shadow:
            0 10px 30px rgba(
                0,
                0,
                0,
                0.5
            );

        margin-bottom: 30px;
        text-align: center;

        direction: rtl;
    }

    .mismar-header h1 {
        color: #10B981;

        font-family: 'Tajawal', sans-serif;

        font-weight: 800;

        font-size: 2.2rem;

        margin: 0 0 10px 0;
    }

    .mismar-header p {
        color: #9CA3AF;

        font-family: 'Tajawal', sans-serif;

        font-size: 1.05rem;

        margin: 0;
    }

    .justification-card {
        background: linear-gradient(
            180deg,
            #111827 0%,
            #1F2937 100%
        );

        border-right: 6px solid #10B981;

        padding: 22px;

        border-radius: 14px;

        font-size: 1.15rem;

        line-height: 1.95;

        color: #F9FAFB;

        box-shadow:
            0 4px 15px rgba(
                0,
                0,
                0,
                0.2
            );

        margin-bottom: 16px;

        direction: rtl;

        text-align: right;
    }

    .evidence-card {
        background-color: #111827;

        border: 1px solid #374151;

        padding: 22px;

        border-radius: 14px;

        color: #D1D5DB;

        line-height: 1.8;

        white-space: pre-wrap;

        direction: rtl;

        text-align: right;
    }

    .stButton > button {
        width: 100%;

        background: linear-gradient(
            90deg,
            #10B981 0%,
            #059669 100%
        );

        color: #FFFFFF;

        font-weight: 700;

        font-size: 1.15rem;

        padding: 14px;

        border-radius: 12px;

        border: none;

        box-shadow:
            0 4px 14px rgba(
                16,
                185,
                129,
                0.3
            );

        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background: linear-gradient(
            90deg,
            #059669 0%,
            #047857 100%
        );

        transform: translateY(-2px);
    }

    section[data-testid="stSidebar"] {
        background-color: #0F172A;
    }

    input,
    textarea {
        direction: rtl !important;
        text-align: right !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# METABASE ENDPOINTS
# ============================================================

METABASE_ENDPOINTS = {
    "tickets": "https://analysis.mismarapp.com/public/question/5f313cbe-6bb4-43bc-9b4d-70b8de7d17d4.json",
    "comments": "https://analysis.mismarapp.com/public/question/82aba25f-d368-44e3-8392-dce163d78e23.json",
    "status_history": "https://analysis.mismarapp.com/public/question/98fe13e6-298a-4775-8244-3015c9c720fe.json",
    "pricing": "https://analysis.mismarapp.com/public/question/b0114e1f-8577-4faa-a790-eaa2412f39f6.json",
}

GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

# ============================================================
# GROQ MODELS API
# ============================================================

def get_groq_models(api_key: str) -> list[dict[str, Any]]:
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("Groq API Key غير موجود.")

    response = requests.get(
        GROQ_MODELS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=20,
    )

    if response.status_code != 200:
        raise Exception(
            f"فشل جلب موديلات Groq.\n\nHTTP {response.status_code}\n{response.text}"
        )

    data = response.json()
    models = data.get("data", [])
    if not isinstance(models, list):
        raise Exception("Groq returned an unexpected models response.")

    return models


def get_model_ids(api_key: str) -> list[str]:
    models = get_groq_models(api_key)
    model_ids = []
    for model in models:
        model_id = model.get("id")
        if model_id:
            model_ids.append(model_id)
    return sorted(set(model_ids))


def choose_best_model(model_ids: list[str]) -> str | None:
    preferred_models = [
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-120b",
        "qwen/qwen3.6-27b",
        "llama-3.1-8b-instant",
    ]

    available = set(model_ids)
    for preferred in preferred_models:
        if preferred in available:
            return preferred

    if model_ids:
        return model_ids[0]

    return None

# ============================================================
# FETCH ORDER DATA
# ============================================================

def fetch_order_data(order_id: int) -> dict[str, Any]:
    payload = {}
    for key, url in METABASE_ENDPOINTS.items():
        try:
            response = requests.get(
                url,
                params={"order_id": order_id},
                timeout=20,
            )
            if response.status_code == 200:
                try:
                    payload[key] = response.json()
                except ValueError:
                    payload[key] = "Error: Invalid JSON returned by Metabase."
            else:
                payload[key] = f"Error HTTP {response.status_code}: {response.text[:500]}"
        except requests.Timeout:
            payload[key] = "Error: Metabase request timed out."
        except requests.RequestException as exc:
            payload[key] = f"Connection Error: {str(exc)}"
        except Exception as exc:
            payload[key] = f"Unexpected Error: {str(exc)}"

    return payload

# ============================================================
# DATA CLEANING UTILITY
# ============================================================

def clean_and_minify(data: Any, max_items: int = 15, max_chars: int = 2500) -> str:
    if not data:
        return "[]"
        
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
        
    if isinstance(data, list):
        data = data[-max_items:]
        cleaned_list = []
        for item in data:
            if isinstance(item, dict):
                cleaned_dict = {}
                for k, v in item.items():
                    if v in (None, "", [], {}): 
                        continue
                    key_lower = str(k).lower()
                    if "url" in key_lower or "uuid" in key_lower or "token" in key_lower:
                        continue
                    cleaned_dict[k] = v
                cleaned_list.append(cleaned_dict)
            else:
                cleaned_list.append(item)
                
        result_str = json.dumps(cleaned_list, ensure_ascii=False, indent=2)
    else:
        result_str = json.dumps(data, ensure_ascii=False, indent=2)
        
    if len(result_str) > max_chars:
        result_str = result_str[-max_chars:]
        
    return result_str

# ============================================================
# DYNAMIC PROMPT BUILDER FOR MULTIPLE AUDIT TYPES
# ============================================================

def build_audit_prompt(
    order_id: int,
    order_data: dict[str, Any],
    ratings: dict[str, int],
    audit_type: str,
) -> str:

    ratings_context = f"تقييمات العميل المدخلة للطلب: {ratings}\n" if ratings else ""

    tickets_str = clean_and_minify(order_data.get("tickets"), max_items=10, max_chars=2000)
    comments_str = clean_and_minify(order_data.get("comments"), max_items=20, max_chars=3500)
    status_history_str = clean_and_minify(order_data.get("status_history"), max_items=15, max_chars=2000)
    pricing_str = clean_and_minify(order_data.get("pricing"), max_items=10, max_chars=2000)

    # ----------------------------------------------------
    # اختيار التعليمات المخصصة بناءً على هدف التدقيق
    # ----------------------------------------------------
    if audit_type == "تدقيق التقييمات المنخفضة (شامل)":
        audit_instructions = """
        🎯 **هدف التدقيق الحقيقي:** الوصول للسبب الجذر المباشر خلف التقييم المنخفض.
        - 🔍 **البحث عن أسباب السعر:** اربط اعتراض السعر بالنص المكتوب داخل التذاكر والتعليقات (ارتفاع أجور اليد مقارنة بالسوق، إضافة قطع اختيارية، تسعير التشليح).
        - 🔍 **البحث عن أسباب الوقت:** ارجع للتعليقات والتسلسل الزمني لتحديد المتسبب الفعلي (تأخر المركز في التشخيص، أو تأخر المورد).
        """
    elif audit_type == "تأخير مرحلة [جاري الفحص والتشخيص]":
        audit_instructions = """
        🎯 **هدف التدقيق الحقيقي:** التحقيق في سبب التأخير في مرحلة [جاري الفحص والتشخيص] حصراً.
        - 🔍 **تركيز الفحص الجنائي:**
          1. قارن بين وقت استلام السيارة / تحويل الحالة لـ [جاري الفحص] ووقت إصدار تذكرة التشخيص أو الشات.
          2. افحص التعليقات والتذاكر: هل كان هناك تأخير من مركز الصيانة في البدء بالفحص؟ أم تأخير في طلب موافقة العميل؟ أم نقص معلومات من العميل/التشغيل؟
          3. حدد بالدقائق والتواريخ كم استغرقت هذه المرحلة ومن الطرف المتسبب الرئيسي في التعطيل (المركز، التشغيل، أم العميل).
        """
    elif audit_type == "تأخير مرحلة [جاري التسعير]":
        audit_instructions = """
        🎯 **هدف التدقيق الحقيقي:** التحقيق في سبب التأخير في مرحلة [جاري التسعير] حصراً.
        - 🔍 **تركيز الفحص الجنائي:**
          1. افحص جدول طلبات التسعير وعروض الأسعار (`pricing`) والتسلسل الزمني للحالات: كم الفارق الزمني بين طلب التسعير ورفع عرض السعر الأول؟
          2. ارجع لمحادثات الشات (`comments`): هل تم رفع طلب التسعير بدون توضيح أجور اليد؟ متى تم الاستفسار عنها ومتى تم الرد؟
          3. هل تأخر فريق التسعير/التشغيل في رفع العرض للعميل؟ أم تم رفض العرض وإعادة التسعير عدة مرات؟ حدد السبب والمسؤول بدقة.
        """
    else:  # تأخير مرحلة [جاري العمل / الصيانة]
        audit_instructions = """
        🎯 **هدف التدقيق الحقيقي:** التحقيق في سبب التأخير المفرط في مرحلة [جاري العمل / الصيانة] حصراً.
        - 🔍 **تركيز الفحص الجنائي:**
          1. افحص الوقت المستغرق منذ موافقة العميل/تحويل الطلب لـ [جاري العمل] حتى الجاهزية.
          2. ابحث في الشات والتذاكر: هل التأخير بسبب تأخر توفير وتوريد قطع الغيار من المورد؟ أم تأخر الورشة نفسها في التركيب والإنجاز؟
          3. هل ظهرت مشاكل أو عيوب جديدة أثناء العمل تطلبت إعادة تسعير أو استشارات إضافية؟ اذكر التفاصيل والتواريخ المحددة.
        """

    prompt_text = f"""
    أنت كبير مدققي العمليات وتجربة العملاء (Senior Operations & CX Forensic Auditor) في شركة صيانة السيارات (مسمار - MisMar).
    وظيفتك إجراء فحص ودراسة جنائية تشغيلية لبيانات الطلب رقم #{order_id}.

    {ratings_context}

    {audit_instructions}

    البيانات المتاحة للطلب:
    1. 🎫 تذاكر الشكاوى والمتابعة: 
    {tickets_str}

    2. 💬 محادثات الشات والتعليقات الداخلية: 
    {comments_str}

    3. ⏱️ التسلسل الزمني للحالات والمدد: 
    {status_history_str}

    4. 💰 طلبات التسعير وعروض الأسعار: 
    {pricing_str}

    === 🎯 تعليمات وقواعد الصياغة الصارمة ===
    قم بتقسيم إجابتك إلى قسمين يفصل بينهما السطر `===SPLIT===`:

    القسم الأول: [التبرير التشغيلي المباشر لمدير العمليات]
    - فقرة واحدة متصلة ومباشرة فقط (من 4 إلى 5 سطور كحد أقصى) جاهزة للنسخ.
    - 🛑 **يُمنع تماماً** البدء بسرد درجات التقييمات.
    - 🛑 **يُمنع تماماً** استخدام جمل فضفاضة مثل "بسبب كثرة عروض الأسعار والارتباك" دون ذكر السبب الحقيقي المباشر والطرف المتسبب.
    - 🟢 **ابدأ فوراً وبشكل مباشر** بالسبب الحقيقي والمتسبب الفعلي في المشكلة موضوع التدقيق.
    - يُمنع استخدام القوائم، العناوين، أو أرقام التذاكر والعروض الداخلية.

    ===SPLIT===

    القسم الثاني: [الأدلة والوقائع التفصيلية والربط الزمني]
    - اكتب بتفصيل كامل وبلا حدود للحجم كافة الأدلة والحقائق المستخرجة التي أدت للاستنتاج أعلاه:
      1. ⏱️ التحليل الزمني للدلتا (Timeline Deltas): احسب الفوارق الزمنية الدقيقة بالساعات والدقائق للمرحلة المستهدفة بالتدقيق.
      2. 🎫 أدلة التذاكر: اقتبس نصوص الشكوى (`description`) ونتيجة التذكرة (`result`) بالنص.
      3. 💬 أدلة الشات: اذكر رسائل المحادثات والتعليقات المتعلقة بالمشكلة مع التوقيت وهوية المُرسل.
      4. 💰 تحليل التسعير: حدد تفاصيل الأسعار، زمن تقديم العروض، وسبب التأخير أو الرفض إن وجد.
    """
    return prompt_text

# ============================================================
# GROQ ANALYSIS RUNNER
# ============================================================

def analyze_order_rating(
    api_key: str,
    order_id: int,
    ratings: dict[str, int],
    audit_type: str,
    model_name: str,
) -> str:

    order_data = fetch_order_data(order_id)
    prompt = build_audit_prompt(order_id, order_data, ratings, audit_type)

    client = Groq(api_key=api_key.strip())

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "أنت Senior Operations وCX Forensic Auditor. حلل البيانات بدقة ولا تخترع أي معلومات واستند فقط على المرفقات.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.3,
            top_p=0.9,
            max_tokens=2500,
        )
    except Exception as exc:
        raise Exception(
            f"خطأ في الاتصال بالذكاء الاصطناعي عبر Groq ({model_name}):\n{str(exc)}"
        )

    if not response or not response.choices:
        raise Exception("Groq returned an empty response.")

    content = response.choices[0].message.content
    if not content:
        raise Exception("Groq returned empty content.")

    return content.strip()

# ============================================================
# SIDEBAR UI
# ============================================================

with st.sidebar:
    st.image(
        "https://mismarapp.com/static/media/logo.f6cf70e4.svg",
        width=200,
    )

    st.markdown("### ⚙️ إعدادات النظام")

    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secret_key = ""

    secret_key = str(secret_key).strip()

    api_key_input = st.text_input(
        "Groq API Key",
        value=secret_key,
        type="password",
        help="يمكن تحميل المفتاح من Streamlit Secrets.",
    )

    api_key = api_key_input.strip()

    if api_key:
        st.success("🔐 Groq API Key موجود")
    else:
        st.warning("⚠️ أضف GROQ_API_KEY في Secrets أو أدخله يدوياً.")

    available_models = []
    selected_model = None

    if api_key:
        try:
            available_models = get_model_ids(api_key)
            if available_models:
                recommended_model = choose_best_model(available_models)
                default_index = 0
                if recommended_model in available_models:
                    default_index = available_models.index(recommended_model)

                selected_model = st.selectbox(
                    "🤖 اختر موديل Groq",
                    options=available_models,
                    index=default_index,
                    help="تلميح: الموديل llama-3.3-70b-versatile يُعطي أفضل نتائج تحليلية عربية.",
                )

                st.success(f"✅ تم العثور على {len(available_models)} موديل")
                st.caption("الموديل المختار:")
                st.code(selected_model, language="text")
            else:
                st.error("لم يتم العثور على أي موديلات.")
        except Exception as exc:
            st.error("❌ فشل اكتشاف موديلات Groq")
            st.code(str(exc), language="text")

# ============================================================
# MAIN LAYOUT & INPUTS
# ============================================================

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📋 بيانات الطلب ونوع التدقيق")

    order_id = st.number_input(
        "رقم الطلب (Order ID)",
        min_value=1,
        value=1034406,
        step=1,
    )

    # 🎯 خيارات تحديد نوع التدقيق المطلوب
    audit_type = st.radio(
        "🔍 اختر المشكلة المطلوبة للتدقيق الاستقصائي:",
        options=[
            "تدقيق التقييمات المنخفضة (شامل)",
            "تأخير مرحلة [جاري الفحص والتشخيص]",
            "تأخير مرحلة [جاري التسعير]",
            "تأخير مرحلة [جاري العمل / الصيانة]"
        ],
        index=0,
        help="حدد الهدف الجذري الذي تريد حصر التحليل عليه ليقوم النظام بالفحص الموجه"
    )

    st.markdown("---")
    st.markdown("##### ⭐️ تقييمات العميل المدخلة (اختياري):")

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
        "التقييم العام": overall_rating,
    }

    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🚀 بدء التدقيق الموجه واستخراج التبرير")

# ============================================================
# OUTPUT & RENDERING
# ============================================================

with col2:
    st.subheader("📊 مخرجات التقرير والتدقيق")

    if analyze_btn:
        if not api_key:
            st.error("⚠️ يرجى إدخال Groq API Key.")
        elif not selected_model:
            st.error("⚠️ لم يتم العثور على موديل متاح في Groq.")
        else:
            with st.spinner(f"⏳ جاري الفحص الجنائي لـ ({audit_type})..."):
                try:
                    full_response = analyze_order_rating(
                        api_key=api_key,
                        order_id=int(order_id),
                        ratings=sample_ratings,
                        audit_type=audit_type,
                        model_name=selected_model,
                    )

                    if "===SPLIT===" in full_response:
                        justification, evidence = full_response.split("===SPLIT===", 1)
                    else:
                        justification = full_response
                        evidence = "لم يتم تفكيك الأدلة بشكل منفصل."

                    st.session_state["audit_result"] = {
                        "justification": justification.strip(),
                        "evidence": evidence.strip(),
                        "order_id": int(order_id),
                        "audit_type": audit_type,
                        "model": selected_model,
                    }

                    st.success("✅ اكتمل التدقيق بنجاح.")

                except Exception as exc:
                    st.error("❌ حدث خطأ أثناء التحليل:")
                    st.code(str(exc), language="text")

if "audit_result" in st.session_state and st.session_state["audit_result"]:
    result = st.session_state["audit_result"]
    justification = result["justification"]
    evidence = result["evidence"]

    st.markdown(f"### 📝 التبرير التشغيلي لـ ({result.get('audit_type', '')}):")
    safe_justification = html.escape(justification)

    st.markdown(
        f"""
        <div class="justification-card">
            {safe_justification}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.text_area(
        "📋 اضغط Ctrl+A ثم Ctrl+C للنسخ المباشر:",
        value=justification,
        height=150,
    )

    st.markdown("### 🔍 الأدلة والوقائع التفصيلية ومحطات الربط الزمني:")
    safe_evidence = html.escape(evidence)

    st.markdown(
        f"""
        <div class="evidence-card">
            {safe_evidence}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(f"Order ID: {result['order_id']} | Type: {result.get('audit_type', '')} | Model: {result['model']}")
else:
    if not analyze_btn:
        st.info("👈 اختر نوع المشكلة ثم اضغط على زر التحليل لعرض النتائج هنا.")
