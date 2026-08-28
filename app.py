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

    .model-card {
        background-color: #111827;

        border: 1px solid #374151;

        padding: 12px 16px;

        border-radius: 10px;

        margin-bottom: 10px;

        direction: ltr;

        text-align: left;

        color: #D1D5DB;
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
# GROQ MODELS API
# ============================================================

GROQ_MODELS_URL = (
    "https://api.groq.com/openai/v1/models"
)


def get_groq_models(
    api_key: str,
) -> list[dict[str, Any]]:

    """
    جلب كل الموديلات التي يستطيع مفتاح Groq الحالي
    الوصول إليها فعلياً.
    """

    api_key = api_key.strip()

    if not api_key:

        raise ValueError(
            "Groq API Key غير موجود."
        )

    response = requests.get(
        GROQ_MODELS_URL,

        headers={
            "Authorization":
                f"Bearer {api_key}",

            "Content-Type":
                "application/json",
        },

        timeout=20,
    )

    if response.status_code != 200:

        raise Exception(
            "فشل جلب موديلات Groq.\n\n"
            f"HTTP {response.status_code}\n"
            f"{response.text}"
        )

    data = response.json()

    models = data.get(
        "data",
        [],
    )

    if not isinstance(
        models,
        list,
    ):

        raise Exception(
            "Groq returned an unexpected models response."
        )

    return models


# ============================================================
# GET MODEL IDS
# ============================================================

def get_model_ids(
    api_key: str,
) -> list[str]:

    models = get_groq_models(
        api_key
    )

    model_ids = []

    for model in models:

        model_id = model.get(
            "id"
        )

        if model_id:

            model_ids.append(
                model_id
            )

    return sorted(
        set(model_ids)
    )


# ============================================================
# CHOOSE BEST MODEL
# ============================================================

def choose_best_model(
    model_ids: list[str],
) -> str | None:

    """
    ترتيب تفضيل للموديلات.

    إذا كان أي موديل من القائمة موجوداً،
    يتم استخدامه.

    وإذا لم يوجد أي منها،
    يتم استخدام أول موديل متاح.
    """

    preferred_models = [

        # OpenAI OSS
        "openai/gpt-oss-120b",

        "openai/gpt-oss-20b",

        # Qwen
        "qwen/qwen3.6-27b",

        "qwen/qwen3.8-27b",

        # Llama
        "llama-3.3-70b-versatile",

        "llama-3.1-8b-instant",

        # Groq compound
        "groq/compound",

        "groq/compound-mini",
    ]

    available = set(
        model_ids
    )

    for preferred in preferred_models:

        if preferred in available:

            return preferred

    if model_ids:

        return model_ids[0]

    return None


# ============================================================
# FETCH ORDER DATA
# ============================================================

def fetch_order_data(
    order_id: int,
) -> dict[str, Any]:

    payload = {}

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

                    payload[key] = (
                        response.json()
                    )

                except ValueError:

                    payload[key] = (
                        "Error: Invalid JSON "
                        "returned by Metabase."
                    )

            else:

                payload[key] = (
                    f"Error HTTP "
                    f"{response.status_code}: "
                    f"{response.text[:500]}"
                )

        except requests.Timeout:

            payload[key] = (
                "Error: Metabase request timed out."
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

    # --------------------------------------------------------
    # Convert ratings to JSON BEFORE building the f-string
    # --------------------------------------------------------

    ratings_json = json.dumps(
        ratings,
        ensure_ascii=False,
        indent=2,
    )

    # --------------------------------------------------------
    # Convert all order data to readable JSON
    # --------------------------------------------------------

    tickets_json = json.dumps(
        order_data.get("tickets"),
        ensure_ascii=False,
        indent=2,
    )

    comments_json = json.dumps(
        order_data.get("comments"),
        ensure_ascii=False,
        indent=2,
    )

    status_history_json = json.dumps(
        order_data.get("status_history"),
        ensure_ascii=False,
        indent=2,
    )

    pricing_json = json.dumps(
        order_data.get("pricing"),
        ensure_ascii=False,
        indent=2,
    )

    # --------------------------------------------------------
    # Build prompt
    # --------------------------------------------------------

    prompt = f"""
أنت كبير مدققي العمليات وتجربة العملاء
(Senior Operations & CX Forensic Auditor)
في شركة صيانة السيارات (مسمار - MisMar).

مهمتك إجراء فحص جنائي تشغيلي متكامل
لبيانات الطلب رقم #{order_id}.

الهدف:

استخراج السبب الجذري الحقيقي
(Root Cause)
خلف تجربة العميل أو التقييم المنخفض.


==================================================
⭐ تقييمات العميل
==================================================

{ratings_json}


==================================================
1. 🎫 تذاكر الشكاوى والمتابعة
==================================================

افحص:

- Description
- Result
- تاريخ الإنشاء
- تاريخ الإغلاق
- اسم القسم
- طبيعة الشكوى
- سبب فتح التذكرة
- سبب الإغلاق

البيانات:

{tickets_json}


==================================================
2. 💬 المحادثات والتعليقات
==================================================

افحص:

- المحادثات
- المفاوضات
- العميل
- مركز الصيانة
- التشغيل
- التوقيت
- هوية المرسل
- أجور اليد
- الأسعار
- اعتراضات العميل

البيانات:

{comments_json}


==================================================
3. ⏱️ Status History
==================================================

حلل:

- الحالات
- أوقات الانتقال
- مدة كل حالة
- مدة الانتظار
- نقاط التعطيل
- التأخير
- المسؤول عن التأخير إذا كان واضحاً

البيانات:

{status_history_json}


==================================================
4. 💰 Pricing
==================================================

حلل:

- وقت طلب التسعير
- وقت رفع العرض
- الفرق الزمني
- قطع الغيار
- أجور اليد
- العروض المرفوضة
- العروض المقبولة
- فروق الأسعار
- أسباب الرفض

البيانات:

{pricing_json}


==================================================
🎯 قواعد التبرير التشغيلي
==================================================

قسم الإجابة إلى قسمين.

افصل بينهما بالسطر:

===SPLIT===


==================================================
القسم الأول
التبرير التشغيلي المباشر لمدير العمليات
==================================================

اكتب فقرة واحدة فقط.

من 4 إلى 5 سطور كحد أقصى.

ابدأ مباشرة بالسبب الجذري الحقيقي.

ممنوع البدء بدرجات التقييم.

لا تقل:

"العميل أعطى السعر 2/5..."

لا تستخدم أسباباً عامة.

لا تقل:

"بسبب كثرة عروض الأسعار والارتباك"

إلا إذا كان لديك دليل فعلي يثبت ذلك.

اربط اعتراض السعر بالنص الموجود
في التذاكر أو المحادثات.

حدد سبب التأخير الحقيقي.

حدد المتسبب في التأخير إذا كان مثبتاً.

لا تخترع معلومات.

لا تستخدم قوائم.

لا تستخدم أرقام التذاكر الداخلية.

لا تستخدم أرقام العروض الداخلية.


==================================================
القسم الثاني
الأدلة والوقائع التفصيلية
==================================================

اشرح الأدلة التي أدت للاستنتاج.


1. ⏱️ Timeline Deltas

احسب:

- مدة طلب التسعير إلى رفع العرض.
- أطول حالة انتظار.
- مدة كل مرحلة مهمة.
- نقاط التعطيل.


2. 🎫 أدلة التذاكر

اذكر:

- Description
- Result
- التاريخ
- التوقيت
- القسم

واقتبس النصوص المهمة كما هي.


3. 💬 أدلة الشات

اذكر:

- الرسائل المهمة.
- المفاوضات.
- اعتراضات العميل.
- ردود المركز.
- التوقيت.
- هوية المرسل.


4. 💰 تحليل التسعير

حلل:

- فروق الأسعار.
- أجور اليد.
- قطع الغيار.
- القطع الاختيارية.
- العروض المرفوضة.
- العروض المقبولة.
- سبب الرفض.


==================================================
قواعد الدقة
==================================================

- لا تخترع أي معلومة.
- اعتمد فقط على البيانات.
- إذا كانت البيانات غير كافية قل ذلك.
- لا تفترض.
- افصل الحقيقة عن الاستنتاج.
- احسب الزمن بدقة عند توفر timestamps.
- حافظ على النصوص المقتبسة.
- ركز على Root Cause.
"""

    return prompt



# ============================================================
# GROQ ANALYSIS
# ============================================================

def analyze_order_rating(
    api_key: str,
    order_id: int,
    ratings: dict[str, int],
    model_name: str,
) -> str:

    # --------------------------------------------------------
    # Fetch order data
    # --------------------------------------------------------

    order_data = fetch_order_data(
        order_id
    )

    # --------------------------------------------------------
    # Build prompt
    # --------------------------------------------------------

    prompt = build_audit_prompt(
        order_id,
        order_data,
        ratings,
    )

    # --------------------------------------------------------
    # Client
    # --------------------------------------------------------

    client = Groq(
        api_key=api_key.strip()
    )

    # --------------------------------------------------------
    # Call Groq
    # --------------------------------------------------------

    try:

        response = (
            client
            .chat
            .completions
            .create(

                model=model_name,

                messages=[

                    {
                        "role": "system",

                        "content": (
                            "أنت Senior Operations "
                            "وCX Forensic Auditor. "
                            "حلل البيانات بدقة. "
                            "لا تخترع أي معلومات. "
                            "اعتمد فقط على البيانات "
                            "المقدمة."
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
        )

    except Exception as exc:

        raise Exception(
            "خطأ في الاتصال بالذكاء الاصطناعي "
            f"عبر Groq ({model_name}):\n"
            f"{str(exc)}"
        )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if not response:

        raise Exception(
            "Groq returned an empty response."
        )

    if not response.choices:

        raise Exception(
            "Groq returned no choices."
        )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    if not content:

        raise Exception(
            "Groq returned empty content."
        )

    return content.strip()


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
    # API KEY
    # --------------------------------------------------------

    try:

        secret_key = st.secrets.get(
            "GROQ_API_KEY",
            "",
        )

    except Exception:

        secret_key = ""

    secret_key = str(
        secret_key
    ).strip()

    api_key_input = st.text_input(
        "Groq API Key",

        value=secret_key,

        type="password",

        help=(
            "يمكن تحميل المفتاح من "
            "Streamlit Secrets."
        ),
    )

    api_key = api_key_input.strip()

    if api_key:

        st.success(
            "🔐 Groq API Key موجود"
        )

    else:

        st.warning(
            "⚠️ أضف GROQ_API_KEY في Secrets "
            "أو أدخله يدوياً."
        )


    # ========================================================
    # MODEL DISCOVERY
    # ========================================================

    available_models = []

    selected_model = None

    if api_key:

        try:

            available_models = get_model_ids(
                api_key
            )

            if available_models:

                recommended_model = (
                    choose_best_model(
                        available_models
                    )
                )

                # --------------------------------------------
                # Select model
                # --------------------------------------------

                default_index = 0

                if (
                    recommended_model
                    in available_models
                ):

                    default_index = (
                        available_models.index(
                            recommended_model
                        )
                    )

                selected_model = st.selectbox(
                    "🤖 اختر موديل Groq",

                    options=available_models,

                    index=default_index,

                    help=(
                        "هذه هي الموديلات التي "
                        "يراها مفتاح Groq الحالي فعلياً."
                    ),
                )

                st.success(
                    f"✅ تم العثور على "
                    f"{len(available_models)} موديل"
                )

                st.caption(
                    "الموديل المختار:"
                )

                st.code(
                    selected_model,
                    language="text",
                )

            else:

                st.error(
                    "لم يتم العثور على أي موديلات."
                )

        except Exception as exc:

            st.error(
                "❌ فشل اكتشاف موديلات Groq"
            )

            st.code(
                str(exc),
                language="text",
            )


    # ========================================================
    # SHOW ALL MODELS
    # ========================================================

    if available_models:

        with st.expander(
            f"📚 كل الموديلات المتاحة "
            f"({len(available_models)})"
        ):

            for index, model in enumerate(
                available_models,
                start=1,
            ):

                st.write(
                    f"{index}. `{model}`"
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
# MAIN COLUMNS
# ============================================================

col1, col2 = st.columns(
    [1, 1],
    gap="large",
)


# ============================================================
# INPUTS
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
# OUTPUT
# ============================================================

with col2:

    st.subheader(
        "📊 مخرجات التقرير والتدقيق"
    )

    if analyze_btn:

        if not api_key:

            st.error(
                "⚠️ يرجى إدخال Groq API Key."
            )

        elif not selected_model:

            st.error(
                "⚠️ لم يتم العثور على موديل "
                "متاح في Groq."
            )

        else:

            with st.spinner(
                "⏳ جاري الفحص الجنائي الرقمي "
                "لبيانات الطلب والتذاكر "
                "والمحادثات..."
            ):

                try:

                    full_response = (
                        analyze_order_rating(

                            api_key=api_key,

                            order_id=int(
                                order_id
                            ),

                            ratings=sample_ratings,

                            model_name=selected_model,
                        )
                    )

                    # ------------------------------------------------
                    # Split
                    # ------------------------------------------------

                    if (
                        "===SPLIT==="
                        in full_response
                    ):

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
                            "لم يتم تفكيك الأدلة "
                            "بشكل منفصل."
                        )

                    # ------------------------------------------------
                    # Save
                    # ------------------------------------------------

                    st.session_state[
                        "audit_result"
                    ] = {

                        "justification":
                            justification.strip(),

                        "evidence":
                            evidence.strip(),

                        "order_id":
                            int(order_id),

                        "model":
                            selected_model,
                    }

                    st.success(
                        "✅ اكتمل التدقيق بنجاح."
                    )

                except Exception as exc:

                    st.error(
                        "❌ حدث خطأ أثناء التحليل:"
                    )

                    st.code(
                        str(exc),
                        language="text",
                    )


# ============================================================
# DISPLAY RESULT
# ============================================================

if (
    "audit_result"
    in st.session_state
    and st.session_state[
        "audit_result"
    ]
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

    # --------------------------------------------------------
    # Justification
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    st.caption(
        f"Order ID: {result['order_id']} "
        f"| Model: {result['model']}"
    )

else:

    if not analyze_btn:

        st.info(
            "👈 قم بإدخال رقم الطلب والضغط "
            "على زر التحليل لعرض النتائج هنا."
        )