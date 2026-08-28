import json
import html
import os
from typing import Any

import requests
import streamlit as st
from google import genai
from google.genai import types


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

    @import url(
        'https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap'
    );

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
        background: linear-gradient(
            135deg,
            #064E3B 0%,
            #0F172A 100%
        );
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

    .status-card {
        background: #111827;
        border: 1px solid #374151;
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 15px;
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
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);
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
    جلب بيانات الطلب الكاملة من مصادر Metabase الأربعة.
    """

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
                    payload[key] = (
                        f"Error: Response from Metabase "
                        f"was not valid JSON."
                    )

            else:
                payload[key] = (
                    f"Error HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                )

        except requests.RequestException as exc:
            payload[key] = f"Connection Error: {str(exc)}"

        except Exception as exc:
            payload[key] = f"Unexpected Error: {str(exc)}"

    return payload


# ============================================================
# BUILD PROMPT
# ============================================================

def build_audit_prompt(
    order_id: int,
    order_data: dict[str, Any],
    ratings: dict[str, int],
) -> str:

    ratings_context = ""

    if ratings:
        ratings_context = (
            "تقييمات العميل المدخلة للطلب:\n"
            f"{json.dumps(ratings, ensure_ascii=False, indent=2)}\n"
        )

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
لبيانات الطلب رقم #{order_id} للوصول للسبب الجذر المباشر
خلف التقييم المنخفض.

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
🎯 قواعد التحليل الصارمة
==================================================

قم بتقسيم الإجابة إلى قسمين يفصل بينهما السطر:

===SPLIT===


==================================================
القسم الأول
التبرير التشغيلي المباشر لمدير العمليات
==================================================

- فقرة واحدة متصلة ومباشرة فقط.
- من 4 إلى 5 سطور كحد أقصى.
- لا تبدأ بذكر درجات التقييم.
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
- لا تستخدم قوائم.
- لا تستخدم عناوين داخل هذه الفقرة.
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
"""


# ============================================================
# GEMINI ANALYSIS - NEW GOOGLE GENAI SDK
# ============================================================

def analyze_order_rating(
    api_key: str,
    order_id: int,
    ratings: dict[str, int],
) -> str:

    api_key = api_key.strip()

    if not api_key:
        raise ValueError("Gemini API Key غير موجود.")

    # --------------------------------------------------------
    # Fetch data
    # --------------------------------------------------------

    order_data = fetch_order_data(order_id)

    # --------------------------------------------------------
    # Build prompt
    # --------------------------------------------------------

    prompt = build_audit_prompt(
        order_id=order_id,
        order_data=order_data,
        ratings=ratings,
    )

    # --------------------------------------------------------
    # Modern Google GenAI SDK
    #
    # Supports GEMINI_API_KEY / explicit API key.
    # --------------------------------------------------------

    try:
        client = genai.Client(
            api_key=api_key
        )

    except Exception as exc:
        raise Exception(
            f"فشل إنشاء Gemini client: {str(exc)}"
        )

    # --------------------------------------------------------
    # Current stable model
    # --------------------------------------------------------

    model_name = "gemini-2.5-flash"

    try:

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                top_p=0.9,
            ),
        )

    except Exception as exc:

        error_text = str(exc)

        # Make AQ authentication problem explicit
        if (
            "ACCESS_TOKEN_TYPE_UNSUPPORTED" in error_text
            or "UNAUTHENTICATED" in error_text
            or "401" in error_text
        ):
            raise Exception(
                "Gemini رفض بيانات المصادقة الخاصة بالمفتاح AQ.\n\n"
                "الـ AQ key تم تحميله بنجاح من التطبيق، "
                "لكن Gemini API رفضه أثناء المصادقة.\n\n"
                "هذا يشير إلى مشكلة في Authorization Key / "
                "Google project provisioning وليس في الـ prompt."
                f"\n\nتفاصيل Google:\n{error_text}"
            )

        raise Exception(
            f"خطأ أثناء الاتصال بـ Gemini ({model_name}): "
            f"{error_text}"
        )

    # --------------------------------------------------------
    # Validate response
    # --------------------------------------------------------

    if response is None:
        raise Exception(
            "Gemini لم يرجع response."
        )

    text = getattr(response, "text", None)

    if not text:
        raise Exception(
            "Gemini رجع response بدون نص."
        )

    return text.strip()


# ============================================================
# GEMINI CONNECTION TEST
# ============================================================

def test_gemini_connection(api_key: str) -> tuple[bool, str]:

    api_key = api_key.strip()

    if not api_key:
        return False, "API Key غير موجود."

    try:

        client = genai.Client(
            api_key=api_key
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with exactly: GEMINI_OK",
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=10,
            ),
        )

        text = getattr(response, "text", "") or ""

        return True, text.strip()

    except Exception as exc:

        error_text = str(exc)

        if "ACCESS_TOKEN_TYPE_UNSUPPORTED" in error_text:
            return (
                False,
                "AQ authentication rejected by Gemini API.\n\n"
                f"{error_text}"
            )

        return False, error_text


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.image(
        "https://mismarapp.com/static/media/logo.f6cf70e4.svg",
        width=200,
    )

    st.markdown("### ⚙️ إعدادات النظام")

    # --------------------------------------------------------
    # Streamlit Secret
    # --------------------------------------------------------

    try:
        secret_key = st.secrets.get(
            "GEMINI_API_KEY",
            "",
        )
    except Exception:
        secret_key = ""

    secret_key = str(secret_key).strip()

    # --------------------------------------------------------
    # Manual override
    # --------------------------------------------------------

    api_key_input = st.text_input(
        "Gemini API Key",
        value=secret_key,
        type="password",
        help=(
            "يتم تحميل المفتاح تلقائياً من Streamlit Secrets. "
            "يمكنك إدخال مفتاح مختلف مؤقتاً."
        ),
    )

    api_key = api_key_input.strip()

    # --------------------------------------------------------
    # Key status
    # --------------------------------------------------------

    if api_key:

        if api_key.startswith("AQ."):
            st.success(
                "🔐 تم اكتشاف Gemini Authorization Key (AQ.)"
            )

        elif api_key.startswith("AIza"):
            st.info(
                "🔑 تم اكتشاف Gemini Standard API Key"
            )

        else:
            st.warning(
                "⚠️ صيغة المفتاح غير معروفة. "
                "سيتم تجربته كما هو."
            )

    else:

        st.warning(
            "⚠️ لم يتم العثور على GEMINI_API_KEY.\n\n"
            "أضفه في Streamlit Cloud:\n"
            "Settings → Secrets"
        )

    # --------------------------------------------------------
    # Test Gemini
    # --------------------------------------------------------

    if st.button("🔌 اختبار اتصال Gemini"):

        if not api_key:

            st.error(
                "يرجى إدخال Gemini API Key أولاً."
            )

        else:

            with st.spinner(
                "⏳ جاري اختبار Gemini..."
            ):

                success, message = test_gemini_connection(
                    api_key
                )

            if success:

                st.success(
                    "✅ Gemini API يعمل بشكل صحيح."
                )

                if message:
                    st.caption(
                        f"Response: {message}"
                    )

            else:

                st.error(
                    "❌ فشل اتصال Gemini"
                )

                st.code(
                    message,
                    language="text",
                )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="mismar-header">

        <h1>
            🔍 نظام تدقيق الطلبات وتجربة العملاء
            (MisMar CX Audit)
        </h1>

        <p>
            استخراج التبريرات التشغيلية والأسباب الجذرية
            بدقة مدعومة بالذكاء الاصطناعي
        </p>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# MAIN LAYOUT
# ============================================================

col1, col2 = st.columns(
    [1, 1],
    gap="large",
)


# ============================================================
# INPUT SECTION
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

    sample_ratings = {
        "الوقت": time_rating,
        "السعر": price_rating,
        "الجودة": quality_rating,
        "خدمة العملاء": cs_rating,
        "التقييم العام": overall_rating,
    }

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    analyze_btn = st.button(
        "🚀 بدء التدقيق العميق واستخراج التبرير"
    )


# ============================================================
# OUTPUT SECTION
# ============================================================

with col2:

    st.subheader(
        "📊 مخرجات التقرير والتدقيق"
    )

    if analyze_btn:

        if not api_key:

            st.error(
                "⚠️ يرجى إدخال Gemini API Key "
                "من القائمة الجانبية."
            )

        else:

            with st.spinner(
                "⏳ جاري الفحص الجنائي الرقمي "
                "لبيانات الطلب والتذاكر والمحادثات..."
            ):

                try:

                    full_response = analyze_order_rating(
                        api_key=api_key,
                        order_id=int(order_id),
                        ratings=sample_ratings,
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

                        justification = full_response

                        evidence = (
                            "لم يتم تفكيك الأدلة بشكل منفصل."
                        )

                    clean_justification = (
                        justification.strip()
                    )

                    clean_evidence = evidence.strip()

                    # ------------------------------------------------
                    # Save result
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
                        f"❌ حدث خطأ أثناء التحليل:\n\n{str(exc)}"
                    )


    # ========================================================
    # DISPLAY SAVED RESULT
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
        # Order info
        # ----------------------------------------------------

        st.caption(
            f"Order ID: {result['order_id']}"
        )

    elif not analyze_btn:

        st.info(
            "👈 قم بإدخال رقم الطلب والضغط على زر "
            "التحليل لعرض النتائج هنا."
        )