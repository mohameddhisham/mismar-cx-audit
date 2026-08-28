import json
import html
from typing import Any

import requests
import streamlit as st
from groq import Groq


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="نظام تدقيق الطلبات والجودة | مسمار MisMar",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');

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

    /* ========================================================
       HEADER
       ======================================================== */

    .mismar-header {
        background: linear-gradient(
            135deg,
            #064E3B 0%,
            #0F172A 100%
        );

        padding: 28px;
        border-radius: 20px;
        border: 1px solid #10B98133;

        box-shadow:
            0 10px 30px rgba(0, 0, 0, 0.5);

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
        margin: 0;
    }

    /* ========================================================
       JUSTIFICATION CARD
       ======================================================== */

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
            0 4px 15px rgba(0, 0, 0, 0.2);

        margin-bottom: 16px;

        direction: rtl;
        text-align: right;
    }

    /* ========================================================
       EVIDENCE CARD
       ======================================================== */

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

        box-shadow:
            0 4px 15px rgba(0, 0, 0, 0.15);
    }

    /* ========================================================
       BUTTONS
       ======================================================== */

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
            0 4px 14px rgba(16, 185, 129, 0.3);

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

    /* ========================================================
       SIDEBAR
       ======================================================== */

    section[data-testid="stSidebar"] {
        background-color: #0F172A;
    }

    /* ========================================================
       INPUTS
       ======================================================== */

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
    "tickets": (
        "https://analysis.mismarapp.com/"
        "public/question/"
        "5f313cbe-6bb4-43bc-9b4d-70b8de7d17d4.json"
    ),

    "comments": (
        "https://analysis.mismarapp.com/"
        "public/question/"
        "82aba25f-d368-44e3-8392-dce163d78e23.json"
    ),

    "status_history": (
        "https://analysis.mismarapp.com/"
        "public/question/"
        "98fe13e6-298a-4775-8244-3015c9c720fe.json"
    ),

    "pricing": (
        "https://analysis.mismarapp.com/"
        "public/question/"
        "b0114e1f-8577-4faa-a790-eaa2412f39f6.json"
    ),
}


# ============================================================
# FETCH ORDER DATA
# ============================================================

def fetch_order_data(order_id: int) -> dict[str, Any]:
    """
    جلب بيانات الطلب من مصادر Metabase الأربعة.
    """

    payload: dict[str, Any] = {}

    for key, url in METABASE_ENDPOINTS.items():

        try:

            response = requests.get(
                url,
                params={
                    "order_id": order_id
                },
                timeout=20,
            )

            if response.status_code == 200:

                try:

                    payload[key] = response.json()

                except ValueError:

                    payload[key] = (
                        "Error: Metabase returned invalid JSON."
                    )

            else:

                payload[key] = (
                    f"Error HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                )

        except requests.Timeout:

            payload[key] = (
                "Error: Request timed out while "
                "connecting to Metabase."
            )

        except requests.RequestException as exc:

            payload[key] = (
                f"Connection Error: {str(exc)}"
            )

        except Exception as exc:

            payload[key] = (
                f"Unexpected Error: {str(exc)}"
            )

    return payload


# ============================================================
# BUILD AUDIT PROMPT
# ============================================================

def build_audit_prompt(
    order_id: int,
    order_data: dict[str, Any],
    ratings: dict[str, int],
) -> str:

    if ratings:

        ratings_context = (
            "تقييمات العميل المدخلة للطلب:\n"
            f"{json.dumps(ratings, ensure_ascii=False, indent=2)}\n"
        )

    else:

        ratings_context = ""

    tickets = json.dumps(
        order_data.get("tickets"),
        ensure_ascii=False,
        indent=2,
    )

    comments = json.dumps(
        order_data.get("comments"),
        ensure_ascii=False,
        indent=2,
    )

    status_history = json.dumps(
        order_data.get("status_history"),
        ensure_ascii=False,
        indent=2,
    )

    pricing = json.dumps(
        order_data.get("pricing"),
        ensure_ascii=False,
        indent=2,
    )

    return f"""
أنت كبير مدققي العمليات وتجربة العملاء
(Senior Operations & CX Forensic Auditor)
في شركة صيانة السيارات (مسمار - MisMar).

وظيفتك إجراء فحص ودراسة جنائية تشغيلية متكاملة
لبيانات الطلب رقم #{order_id}
للوصول للسبب الجذر المباشر خلف التقييم المنخفض.

{ratings_context}

==================================================
البيانات المتاحة للطلب
==================================================

1. 🎫 تذاكر الشكاوى والمتابعة

افحص:

- Description
- Result
- تواريخ الإنشاء والإغلاق
- اسم قسم التذكرة
- طبيعة الشكوى
- سبب فتح التذكرة
- سبب إغلاقها

البيانات:

{tickets}


==================================================

2. 💬 محادثات الشات والتعليقات الداخلية

افحص:

- نصوص المحادثات
- المفاوضات
- العميل
- مركز الصيانة
- التشغيل
- التوقيت
- هوية المرسل
- تفاصيل أجور اليد
- تفاصيل الأسعار
- اعتراضات العميل

البيانات:

{comments}


==================================================

3. ⏱️ التسلسل الزمني للحالات والمدد

افحص:

- جميع الحالات
- أوقات الانتقال
- مدة كل حالة
- مدة الانتظار
- نقاط التعطيل
- التأخير بين العمليات

البيانات:

{status_history}


==================================================

4. 💰 طلبات التسعير وعروض الأسعار

افحص:

- وقت طلب التسعير
- وقت رفع العرض
- الفارق الزمني
- قطع الغيار
- أجور اليد
- العروض المرفوضة
- العروض المقبولة
- فروق الأسعار
- أسباب الرفض

البيانات:

{pricing}


==================================================
🎯 تعليمات وقواعد الصياغة الصارمة
==================================================

قم بتقسيم الإجابة إلى قسمين يفصل بينهما السطر:

===SPLIT===


==================================================
القسم الأول
التبرير التشغيلي المباشر لمدير العمليات
==================================================

- فقرة واحدة متصلة ومباشرة فقط.
- من 4 إلى 5 سطور كحد أقصى.
- يُمنع تماماً البدء بذكر درجات التقييم.
- لا تقل:
  "العميل أعطى السعر 2/5 والوقت 3/5..."
- ابدأ مباشرة بالسبب الجذري الحقيقي.
- استخرج السبب من البيانات الفعلية.
- لا تستخدم أسباباً عامة أو فضفاضة.
- لا تقل:
  "بسبب كثرة عروض الأسعار والارتباك"
  بدون تحديد السبب الحقيقي.
- اربط اعتراض السعر بالنص الموجود في التذاكر أو المحادثات.
- حدد السبب الحقيقي وراء اعتراض السعر.
- حدد السبب الحقيقي وراء التأخير.
- حدد المتسبب في التأخير إذا كان ذلك مثبتاً بالأدلة.
- لا تخترع معلومات.
- لا تستخدم قوائم في القسم الأول.
- لا تستخدم عناوين داخل القسم الأول.
- لا تستخدم أرقام التذاكر أو أرقام العروض الداخلية.


==================================================
القسم الثاني
الأدلة والوقائع التفصيلية والربط الزمني
==================================================

اكتب بتفصيل كامل الأدلة التي أدت إلى الاستنتاج.

1. ⏱️ Timeline Deltas

احسب:

- الوقت بين طلب التسعير ورفع العرض.
- مدة أطول حالة انتظار.
- الفارق بين الحالات.
- أي نقاط تأخير واضحة.


2. 🎫 أدلة التذاكر

اذكر:

- Description
- Result
- التاريخ والتوقيت
- اسم القسم إذا كان متاحاً.

عند الاقتباس، حافظ على النص الأصلي كما هو.


3. 💬 أدلة الشات

اذكر:

- الرسائل المهمة.
- المفاوضات.
- اعتراضات العميل.
- ردود مركز الصيانة.
- التوقيت.
- هوية المرسل إذا كانت متاحة.


4. 💰 تحليل التسعير

حلل:

- فرق السعر.
- أجور اليد.
- قطع الغيار.
- القطع الاختيارية.
- العروض المرفوضة.
- العروض المقبولة.
- السبب المباشر للرفض.


==================================================
قواعد الدقة
==================================================

- لا تخترع أي معلومة.
- لا تفترض سبباً غير موجود في البيانات.
- إذا كانت معلومة غير متاحة، اذكر أنها غير متاحة.
- إذا لم يوجد دليل كافٍ على سبب معين، قل ذلك بوضوح.
- افصل بين الحقيقة والاستنتاج.
- استخدم البيانات الزمنية بدقة.
- لا تغيّر النصوص المقتبسة من التذاكر أو المحادثات.
- لا تذكر درجات التقييم في بداية التبرير التشغيلي.
- ركز على Root Cause وليس مجرد وصف المشكلة.
- جميع الاستنتاجات يجب أن تكون مبنية على البيانات المقدمة.
"""


# ============================================================
# CREATE GROQ CLIENT
# ============================================================

def create_groq_client(api_key: str) -> Groq:

    api_key = api_key.strip()

    if not api_key:

        raise ValueError(
            "Groq API Key غير موجود."
        )

    try:

        return Groq(
            api_key=api_key
        )

    except Exception as exc:

        raise Exception(
            f"فشل إنشاء Groq client: {str(exc)}"
        )


# ============================================================
# ANALYZE ORDER WITH GROQ
# ============================================================

def analyze_order_rating(
    api_key: str,
    order_id: int,
    ratings: dict[str, int],
) -> str:

    # --------------------------------------------------------
    # Fetch data
    # --------------------------------------------------------

    order_data = fetch_order_data(
        order_id
    )

    # --------------------------------------------------------
    # Build prompt
    # --------------------------------------------------------

    prompt = build_audit_prompt(
        order_id=order_id,
        order_data=order_data,
        ratings=ratings,
    )

    # --------------------------------------------------------
    # Create Groq client
    # --------------------------------------------------------

    client = create_groq_client(
        api_key
    )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    model_name = "llama-3.1-8b-instant"

    # --------------------------------------------------------
    # Groq API call
    # --------------------------------------------------------

    try:

        response = client.chat.completions.create(

            model=model_name,

            messages=[
                {
                    "role": "system",
                    "content": (
                        "أنت خبير Senior Operations & "
                        "CX Forensic Auditor. "
                        "حلل البيانات بدقة شديدة. "
                        "اعتمد فقط على البيانات المقدمة. "
                        "لا تخترع أي معلومات. "
                        "احسب الفروقات الزمنية عندما "
                        "تكون البيانات الزمنية متاحة."
                    ),
                },

                {
                    "role": "user",
                    "content": prompt,
                },
            ],

            temperature=0.3,

            top_p=0.9,

            max_tokens=12000,
        )

    except Exception as exc:

        raise Exception(
            f"خطأ في الاتصال بالذكاء الاصطناعي "
            f"عبر Groq ({model_name}):\n"
            f"{str(exc)}"
        )

    # --------------------------------------------------------
    # Validate response
    # --------------------------------------------------------

    if not response:

        raise Exception(
            "Groq لم يرجع أي response."
        )

    if not response.choices:

        raise Exception(
            "Groq لم يرجع أي choices."
        )

    message = response.choices[0].message

    if not message:

        raise Exception(
            "Groq لم يرجع message."
        )

    result = message.content

    if not result:

        raise Exception(
            "Groq رجع نتيجة فارغة."
        )

    return result.strip()


# ============================================================
# TEST GROQ CONNECTION
# ============================================================

def test_groq_connection(
    api_key: str,
) -> tuple[bool, str]:

    api_key = api_key.strip()

    if not api_key:

        return (
            False,
            "Groq API Key غير موجود."
        )

    try:

        client = create_groq_client(
            api_key
        )

        response = client.chat.completions.create(

            model="llama-3.3-70b-versatile",

            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly: GROQ_OK",
                }
            ],

            temperature=0,

            max_tokens=10,
        )

        if not response.choices:

            return (
                False,
                "Groq لم يرجع أي نتيجة."
            )

        text = (
            response
            .choices[0]
            .message
            .content
            or ""
        )

        return (
            True,
            text.strip()
        )

    except Exception as exc:

        return (
            False,
            str(exc)
        )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.image(
        "https://mismarapp.com/static/media/logo.f6cf70e4.svg",
        width=200,
    )

    st.markdown(
        "### ⚙️ إعدادات النظام"
    )

    # --------------------------------------------------------
    # Read API key from Streamlit Secrets
    # --------------------------------------------------------

    try:

        secret_key = st.secrets.get(
            "GROQ_API_KEY",
            ""
        )

    except Exception:

        secret_key = ""

    secret_key = str(
        secret_key
    ).strip()

    # --------------------------------------------------------
    # Manual API key input
    # --------------------------------------------------------

    api_key_input = st.text_input(
        "Groq API Key",

        value=secret_key,

        type="password",

        help=(
            "يتم تحميل المفتاح تلقائياً من "
            "Streamlit Secrets. "
            "يمكنك إدخال مفتاح مختلف مؤقتاً."
        ),
    )

    api_key = api_key_input.strip()

    # --------------------------------------------------------
    # API key status
    # --------------------------------------------------------

    if api_key:

        st.success(
            "🔐 تم تحميل Groq API Key"
        )

    else:

        st.warning(
            "⚠️ لم يتم العثور على GROQ_API_KEY.\n\n"
            "أضفه في Streamlit Cloud:\n"
            "Settings → Secrets"
        )

    # --------------------------------------------------------
    # Test API
    # --------------------------------------------------------

    if st.button(
        "🔌 اختبار اتصال Groq"
    ):

        if not api_key:

            st.error(
                "يرجى إدخال Groq API Key أولاً."
            )

        else:

            with st.spinner(
                "⏳ جاري اختبار Groq..."
            ):

                success, message = (
                    test_groq_connection(
                        api_key
                    )
                )

            if success:

                st.success(
                    "✅ Groq API يعمل بشكل صحيح."
                )

                if message:

                    st.caption(
                        f"Response: {message}"
                    )

            else:

                st.error(
                    "❌ فشل اتصال Groq"
                )

                st.code(
                    message,
                    language="text",
                )


# ============================================================
# MAIN HEADER
# ============================================================

# ============================================================
# MAIN COLUMNS
# ============================================================

col1, col2 = st.columns(
    [1, 1],
    gap="large",
)


# ============================================================
# INPUT COLUMN
# ============================================================

with col1:

    st.subheader(
        "📋 بيانات الطلب والتقييمات"
    )

    order_id = st.number_input(
        "رقم الطلب (Order ID)",

        min_value=1,

        value=1034406,

        step=1,
    )

    st.markdown(
        "##### ⭐️ تقييمات العميل المدخلة:"
    )

    col_r1, col_r2 = st.columns(2)

    with col_r1:

        time_rating = st.slider(
            "الوقت ⏱️",
            1,
            5,
            5,
        )

        price_rating = st.slider(
            "السعر 💰",
            1,
            5,
            3,
        )

        quality_rating = st.slider(
            "الجودة 🛠️",
            1,
            5,
            5,
        )

    with col_r2:

        cs_rating = st.slider(
            "خدمة العملاء 🎧",
            1,
            5,
            5,
        )

        overall_rating = st.slider(
            "التقييم العام ⭐️",
            1,
            5,
            5,
        )

    # --------------------------------------------------------
    # Ratings object
    # --------------------------------------------------------

    sample_ratings = {

        "الوقت":
            time_rating,

        "السعر":
            price_rating,

        "الجودة":
            quality_rating,

        "خدمة العملاء":
            cs_rating,

        "التقييم العام":
            overall_rating,
    }

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    analyze_btn = st.button(
        "🚀 بدء التدقيق العميق واستخراج التبرير"
    )


# ============================================================
# OUTPUT COLUMN
# ============================================================

with col2:

    st.subheader(
        "📊 مخرجات التقرير والتدقيق"
    )

    # --------------------------------------------------------
    # Run analysis
    # --------------------------------------------------------

    if analyze_btn:

        if not api_key:

            st.error(
                "⚠️ يرجى إدخال Groq API Key "
                "من القائمة الجانبية."
            )

        else:

            with st.spinner(
                "⏳ جاري الفحص الجنائي الرقمي "
                "لبيانات الطلب والتذاكر والمحادثات..."
            ):

                try:

                    full_response = (
                        analyze_order_rating(
                            api_key=api_key,
                            order_id=int(order_id),
                            ratings=sample_ratings,
                        )
                    )

                    # ------------------------------------------------
                    # Split response
                    # ------------------------------------------------

                    if "===SPLIT===" in full_response:

                        justification, evidence = (
                            full_response.split(
                                "===SPLIT===",
                                1,
                            )
                        )

                    else:

                        justification = (
                            full_response
                        )

                        evidence = (
                            "لم يتم تفكيك الأدلة بشكل منفصل."
                        )

                    # ------------------------------------------------
                    # Clean
                    # ------------------------------------------------

                    clean_justification = (
                        justification.strip()
                    )

                    clean_evidence = (
                        evidence.strip()
                    )

                    # ------------------------------------------------
                    # Store
                    # ------------------------------------------------

                    st.session_state[
                        "audit_result"
                    ] = {

                        "justification":
                            clean_justification,

                        "evidence":
                            clean_evidence,

                        "order_id":
                            int(order_id),
                    }

                    st.success(
                        "✅ اكتمل التدقيق بنجاح."
                    )

                except Exception as exc:

                    st.error(
                        f"❌ حدث خطأ أثناء التحليل:\n\n"
                        f"{str(exc)}"
                    )


    # ========================================================
    # DISPLAY RESULT
    # ========================================================

    if (
        "audit_result" in st.session_state
        and st.session_state["audit_result"]
    ):

        result = st.session_state[
            "audit_result"
        ]

        justification = result[
            "justification"
        ]

        evidence = result[
            "evidence"
        ]

        # ----------------------------------------------------
        # Justification
        # ----------------------------------------------------

        st.markdown(
            "### 📝 التبرير التشغيلي "
            "(جاهز للنسخ لمدير العمليات):"
        )

        safe_justification = html.escape(
            justification
        )

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

        # ----------------------------------------------------
        # Evidence
        # ----------------------------------------------------

        st.markdown(
            "### 🔍 الأدلة والوقائع التفصيلية "
            "ومحطات الربط الزمني:"
        )

        safe_evidence = html.escape(
            evidence
        )

        st.markdown(
            f"""
            <div class="evidence-card">
                {safe_evidence}
            </div>
            """,

            unsafe_allow_html=True,
        )

        # ----------------------------------------------------
        # Order ID
        # ----------------------------------------------------

        st.caption(
            f"Order ID: {result['order_id']}"
        )

    elif not analyze_btn:

        st.info(
            "👈 قم بإدخال رقم الطلب والضغط على زر "
            "التحليل لعرض النتائج هنا."
        )
