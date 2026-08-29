import json
import html
from typing import Any

import requests
import streamlit as st
from groq import Groq

# ============================================================
# DYNAMIC PROMPT BUILDER WITH MATCHING CLASSIFICATIONS
# ============================================================

def build_audit_prompt(
    order_id: int,
    order_data: dict[str, Any],
    audit_type: str,
) -> str:

    tickets_str = clean_and_minify(order_data.get("tickets"), max_items=10, max_chars=2000)
    comments_str = clean_and_minify(order_data.get("comments"), max_items=20, max_chars=3500)
    status_history_str = clean_and_minify(order_data.get("status_history"), max_items=15, max_chars=2000)
    pricing_str = clean_and_minify(order_data.get("pricing"), max_items=10, max_chars=2000)

    # 🛑 حصر قوائم التصنيفات حسب المرحلة بالضبط
    if audit_type == "تأخير مرحلة [جاري التسعير]":
        allowed_categories = """
- التصنيف: قطع الغيار
- التصنيف: تشغيل
- التصنيف: لا يوجد تاخير
- التصنيف: المركز
- التصنيف: مكرر
- التصنيف: يوم الجمعه
- التصنيف: العميل
- التصنيف: الوكاله
- التصنيف: المركز والتشغيل
- التصنيف: نقل بين مركزين
- التصنيف: المركز وقطع الغيار
- التصنيف: قطع الغيار والتشغيل
- التصنيف: المركز والوكاله
"""
    else:  # الفحص والتشخيص + جاري العمل / الصيانة + العام
        allowed_categories = """
- التصنيف: قطع الغيار
- التصنيف: التشغيل
- التصنيف: العميل
- التصنيف: مركز
- التصنيف: لا يوجد تاخير وفق خطه العميل
- التصنيف: يوم الجمعه
- التصنيف: مكرر
- التصنيف: قطع الغيار او المركز
- التصنيف: نقل مركز اخر
- التصنيف: تشغيل او المركز
- التصنيف: قطع الغيار او التشغيل
"""

    prompt_text = f"""
أنت Senior Operations & CX Forensic Auditor في شركة (مسمار - MisMar).
مهمتك كتابة تبرير تشغيلي مباشر وموجز لمدير العمليات للطلب رقم #{order_id} بناءً على بيانات المرحلة: [{audit_type}].

البيانات المتاحة للطلب:
1. 🎫 تذاكر الشكاوى والمتابعة: {tickets_str}
2. 💬 محادثات الشات والتعليقات الداخلية: {comments_str}
3. ⏱️ التسلسل الزمني للحالات والمدد: {status_history_str}
4. 💰 طلبات التسعير وعروض الأسعار: {pricing_str}

=== 🛑 القواعد الصارمة والتنسيق المطلوبة ===
اقسم إجابتك لقسمين بينهما الكلمة المفتاحية `===SPLIT===`:

القسم الأول:
اكتب السبب الرئيسي مباشرة دون أي عناوين أو تكرار أو ديباجات، متبوعاً بالتصنيف في السطر الأخير فقط.

📌 **مثال للنسق المطلوب للقسم الأول (التزم بالنموذج حرفياً):**
تأخير في توريد قطع الغيار اللازمة للعملية وإتمام الفحص النهائي من جهة المورد، مما تسبب في توقف الطلب لمدة تزيد عن 115 ساعة قبل بدء الصيانة الفعلية دون متابعة لتسريع الاستلام.
التصنيف: قطع الغيار

🛑 **شروط القسم الأول:**
- اكتب فقرة واحدة فقط من 2-4 سطور تمثل السبب الرئيسي والأقوى فقط.
- ممنوع كتابة أي عناوين مثل "التبرير التشغيلي المباشر" وممنوع تكرار سطر التصنيف أكثر من مرة.
- يُمنع ذكر أسامي أفراد (استخدم الألقاب: التشغيل / المركز).
- السطر الأخير يجب أن يحتوي على خيار واحد فقط من القائمة التالية:
{allowed_categories}

===SPLIT===

القسم الثاني:
أدلة وقائع تفصيلية وحساب التوقيتات والأدلة من التذاكر والشات باختصار.
"""
    return prompt_text

# ============================================================
# GROQ ANALYSIS RUNNER
# ============================================================

def analyze_order_rating(
    api_key: str,
    order_id: int,
    audit_type: str,
    model_name: str,
) -> str:

    order_data = fetch_order_data(order_id)
    prompt = build_audit_prompt(order_id, order_data, audit_type)

    client = Groq(api_key=api_key.strip())

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "أنت Senior Operations وCX Forensic Auditor. اكتب تبريراً واحداً حاسماً دون تكرار أو عناوين فرعية ملتزماً بالتصنيف المحدد فقط.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # درجة منخفضة جداً لمنع التكرار والتشتت
            top_p=0.9,
            max_tokens=1500,
        )
    except Exception as exc:
        raise Exception(f"خطأ في الاتصال بالذكاء الاصطناعي عبر Groq ({model_name}):\n{str(exc)}")

    if not response or not response.choices:
        raise Exception("Groq returned an empty response.")

    content = response.choices[0].message.content
    return content.strip() if content else ""

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

GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

# ============================================================
# GROQ MODELS API
# ============================================================

def get_groq_models(api_key: str) -> list[dict[str, Any]]:
    """جلب كل الموديلات التي يستطيع مفتاح Groq الحالي الوصول إليها فعلياً."""
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
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.6-27b",
        "qwen/qwen3.8-27b",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "groq/compound",
        "groq/compound-mini",
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

def clean_and_minify(data: Any, max_items: int = 10, max_chars: int = 1500) -> str:
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
                    if "id" in key_lower or "url" in key_lower or "uuid" in key_lower or "token" in key_lower:
                        continue
                    cleaned_dict[k] = v
                cleaned_list.append(cleaned_dict)
            else:
                cleaned_list.append(item)
                
        result_str = json.dumps(cleaned_list, ensure_ascii=False, separators=(',', ':'))
    else:
        result_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        
    if len(result_str) > max_chars:
        result_str = result_str[-max_chars:]
        
    return result_str

# ============================================================
# BUILD AUDIT PROMPT (ENHANCED FORENSIC AUDIT PROMPT)
# ============================================================

def build_audit_prompt(
    order_id: int,
    order_data: dict[str, Any],
    ratings: dict[str, int],
) -> str:

    ratings_json = json.dumps(ratings, ensure_ascii=False, separators=(',', ':'))

    tickets_json = clean_and_minify(order_data.get("tickets"), max_items=5, max_chars=1200)
    comments_json = clean_and_minify(order_data.get("comments"), max_items=15, max_chars=2500)
    status_history_json = clean_and_minify(order_data.get("status_history"), max_items=10, max_chars=1200)
    pricing_json = clean_and_minify(order_data.get("pricing"), max_items=5, max_chars=1200)

    prompt = f"""
أنت Senior Operations & CX Forensic Auditor في منصة "مسمار - MisMar" لصيانة السيارات.
مهمتك إجراء تدقيق جنائي تشغيلي لبيانات الطلب #{order_id} واستخراج التبرير التشغيلي المباشر والدقيق لمدير العمليات.

تقييمات العميل المدخلة للطلب:
{ratings_json}

بيانات الطلب النيئة المستخرجة من النظام:
1. 🎫 تذاكر الشكاوى والمتابعة (اقرأ وصف الشكوى Description والنتيجة Result وقسم التذكرة):
{tickets_json}

2. 💬 محادثات الشات والتعليقات الداخلية (افحص نصوص المحادثات بين التشغيل والمركز والعميل، التواقيت، وهوية المُرسل):
{comments_json}

3. ⏱️ التسلسل الزمني للحالات والمدد (احسب أوقات الانتظار والتأخير بين الحالات المختلفة):
{status_history_json}

4. 💰 طلبات التسعير وعروض الأسعار (افحص الفارق الزمني للتسعير، أجور اليد مقارنة بأسعار القطع، والرفض/القبول):
{pricing_json}

=== 🎯 تعليمات الصياغة والتحليل الجنائي الصارمة ===
قم بتقسيم إجابتك إلى قسمين تفصل بينهما الكلمة المفتاحية `===SPLIT===`:

القسم الأول: [التبرير التشغيلي المباشر لمدير العمليات]
- اكتب فقرة واحدة فقط متصلة من 3 إلى 5 سطور (جاهزة للنسخ واللصق فوراً لمدير العمليات).
- 🛑 ممنوع نهائياً البدء بسرد الدرجات أو التقييمات (مثل: "يعود سبب تقييم العميل 2/5 للسعر...").
- 🛑 ممنوع استخدام العبارات العامة والفضفاضة (مثل "بسبب التأخير والأخطاء التشغيلية").
- 🟢 ابدأ فوراً بالسبب التشغيلي المباشر والجذري (مثال: "يعود سبب اعتراض العميل على السعر إلى...").
- 🔍 في أسباب السعر: ابحث عن السبب الحقيقي من الشات والتذاكر (مثل: المبالغة في أجور يد الفحص، إضافة القطع الاستهلاكية بدون موافقة مبدئية، أو الخلاف على تسعير قطع التشليح).
- 🔍 في أسباب الوقت: حدد الطرف المتسبب بالتأخير بدقة من واقع التوقيتات (مثل: تأخر مركز الصيانة 6 ساعات في التشخيص، أو تأخر المورد في توفير القطع).
- يُمنع استخدام القوائم أو العناوين أو أرقام التذاكر والعروض الداخليّة في هذا القسم.

===SPLIT===

القسم الثاني: [الأدلة والوقائع التفصيلية والربط الزمني]
اكتب بتفصيل كامل كافة الحقائق والأدلة المساندة المستخرجة من البيانات:
1. ⏱️ التحليل الزمني (Timeline Deltas): احسب المدة الدقيقة بين طلب التسعير ورفع العرض، وأطول حالة تعطيل بالدقيقة/الساعة.
2. 🎫 أدلة التذاكر: اقتبس نص الشكوى (Description) والنتيجة (Result) بالنص.
3. 💬 أدلة الشات: اقتبس نصوص المفاوضات والرسائل الهامة مع التوقيتات والمُرسل.
4. 💰 تحليل التسعير: فكّك اعتراضات العميل على أجور اليد مقابل قطع الغيار، وسبب رفض العروض المبدئية.
"""
    return prompt

# ============================================================
# GROQ ANALYSIS RUNNER
# ============================================================

def analyze_order_rating(
    api_key: str,
    order_id: int,
    ratings: dict[str, int],
    model_name: str,
) -> str:

    order_data = fetch_order_data(order_id)
    prompt = build_audit_prompt(order_id, order_data, ratings)

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
            max_tokens=2000,
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
                    help="هذه هي الموديلات التي يراها مفتاح Groq الحالي فعلياً.",
                )

                st.success(f"✅ تم العثور على {len(available_models)} موديل")
                st.caption("الموديل المختار:")
                st.code(selected_model, language="text")
            else:
                st.error("لم يتم العثور على أي موديلات.")
        except Exception as exc:
            st.error("❌ فشل اكتشاف موديلات Groq")
            st.code(str(exc), language="text")

    if available_models:
        with st.expander(f"📚 كل الموديلات المتاحة ({len(available_models)})"):
            for index, model in enumerate(available_models, start=1):
                st.write(f"{index}. `{model}`")

# ============================================================
# MAIN LAYOUT & INPUTS
# ============================================================

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📋 بيانات الطلب والتقييمات")

    order_id = st.number_input(
        "رقم الطلب (Order ID)",
        min_value=1,
        value=1034406,
        step=1,
    )

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
        "التقييم العام": overall_rating,
    }

    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🚀 بدء التدقيق العميق واستخراج التبرير")

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
            with st.spinner("⏳ جاري الفحص الجنائي الرقمي لبيانات الطلب والتذاكر والمحادثات..."):
                try:
                    full_response = analyze_order_rating(
                        api_key=api_key,
                        order_id=int(order_id),
                        ratings=sample_ratings,
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

    st.markdown("### 📝 التبرير التشغيلي (جاهز للنسخ لمدير العمليات):")
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

    st.caption(f"Order ID: {result['order_id']} | Model: {result['model']}")
else:
    if not analyze_btn:
        st.info("👈 قم بإدخال رقم الطلب والضغط على زر التحليل لعرض النتائج هنا.")
