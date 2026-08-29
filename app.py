import json
import html
import re
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
        padding: 30px;
        border-radius: 20px;
        border: 1px solid rgba(16, 185, 129, 0.25);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        margin-bottom: 30px;
        text-align: center;
        direction: rtl;
    }

    .mismar-header h1 {
        color: #10B981;
        font-weight: 800;
        font-size: 2.2rem;
        margin: 0 0 10px 0;
    }

    .mismar-header p {
        color: #9CA3AF;
        font-size: 1.05rem;
        margin: 0;
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

    .stButton > button:hover {
        background: linear-gradient(90deg, #059669 0%, #047857 100%);
        transform: translateY(-2px);
    }

    section[data-testid="stSidebar"] {
        background-color: #0F172A;
    }

    input, textarea {
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

# التصنيفات المسموح بها فقط - أي رد لا ينتهي بواحد منها يعتبر غير صالح
VALID_CLASSIFICATIONS = [
    "التصنيف: قطع الغيار او التشغيل",
    "التصنيف: قطع الغيار او المركز",
    "التصنيف: تشغيل او المركز",
    "التصنيف: نقل مركز اخر",
    "التصنيف: لا يوجد تاخير وفق خطه العميل",
    "التصنيف: قطع الغيار",
    "التصنيف: التشغيل",
    "التصنيف: العميل",
    "التصنيف: مركز",
    "التصنيف: يوم الجمعه",
    "التصنيف: مكرر",
]


def get_groq_models(api_key: str) -> list[dict[str, Any]]:
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("Groq API Key غير موجود.")

    response = requests.get(
        GROQ_MODELS_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=20,
    )

    if response.status_code != 200:
        raise Exception(f"فشل جلب موديلات Groq.\n\nHTTP {response.status_code}\n{response.text}")

    data = response.json()
    models = data.get("data", [])
    if not isinstance(models, list):
        raise Exception("Groq returned an unexpected models response.")

    return models


def get_model_ids(api_key: str) -> list[str]:
    models = get_groq_models(api_key)
    model_ids = [model.get("id") for model in models if model.get("id")]
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
    return model_ids[0] if model_ids else None


def fetch_order_data(order_id: int) -> dict[str, Any]:
    payload = {}
    for key, url in METABASE_ENDPOINTS.items():
        try:
            response = requests.get(url, params={"order_id": order_id}, timeout=20)
            if response.status_code == 200:
                try:
                    payload[key] = response.json()
                except ValueError:
                    payload[key] = "Error: Invalid JSON returned by Metabase."
            else:
                payload[key] = f"Error HTTP {response.status_code}: {response.text[:500]}"
        except Exception as exc:
            payload[key] = f"Error: {str(exc)}"
    return payload


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
# BUILD PROMPT WITH STRICT SHORT & FOCUSED INSTRUCTIONS
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

    prompt_text = f"""
أنت Senior Operations & CX Forensic Auditor في شركة (مسمار - MisMar).
مهمتك كتابة تبرير تشغيلي مباشر جداً لمدير العمليات للطلب رقم #{order_id} بناءً على بيانات المرحلة: [{audit_type}].

البيانات المتاحة للطلب:
1. 🎫 تذاكر الشكاوى والمتابعة: {tickets_str}
2. 💬 محادثات الشات والتعليقات الداخلية: {comments_str}
3. ⏱️ التسلسل الزمني للحالات والمدد: {status_history_str}
4. 💰 طلبات التسعير وعروض الأسعار: {pricing_str}

=== 🛑 قواعد صارمة يجب تطبيقها حرفياً بدون أي استثناء ===

1) **الجملة الأولى = السبب نفسه مباشرة.**
   ممنوع منعاً باتاً أي جملة افتتاحية أو وصفية قبل ذكر السبب، حتى لو كانت قصيرة.
   ❌ ممنوع كتابة: "تأخر مرحلة كذا يعود إلى..." / "يعود سبب التأخير إلى..." / "بعد مراجعة السجلات..." / "أظهرت البيانات أن...".
   ✅ ابدأ الجملة الأولى بالسبب الجذري ذاته كأنك تجاوب سؤال "ليه اتأخر؟" مباشرة.
   مثال صحيح للصياغة (الشكل فقط، مش المحتوى): "انتظار توريد قطعة الغيار من المورد استغرق X يوم قبل بدء الصيانة، حيث لم يتم تأكيد توفر القطعة إلا بعد متابعات متكررة من التشغيل."

2) **سبب جذري واحد فقط - ممنوع تعداد أسباب.**
   اختر السبب الأقوى والأكثر تفسيراً للتأخير من البيانات، واكتب عنه فقط.
   حتى لو وجدت في البيانات أسباب ثانوية أخرى (تأخر رد، تكرار تسعير، تعديل موعد، إلخ) — **تجاهلها تماماً ولا تذكرها إطلاقاً**، لا كسبب ولا كتفصيل إضافي. التقرير يجب أن يقرأ كأن هذا هو السبب الوحيد الذي حدث.
   ❌ ممنوع صيغ مثل: "بالإضافة إلى ذلك..." / "كما تكرر..." / "ما أضاف أياماً إضافية...".

3) **ممنوع نهائياً ذكر أي اسم شخص** ظاهر في البيانات (اسم فني، ممثل مركز، موظف تشغيل، عميل...) - سواء بالاسم الكامل أو الأول فقط، وسواء داخل النص أو بين قوسين.
   استبدل أي إشارة لشخص بصفته فقط:
   - أي موظف أو ممثل تابع لمسمار → **(التشغيل)**
   - أي فني أو ممثل تابع لورشة/مركز الصيانة → **(المركز)**
   - العميل صاحب الطلب → **(العميل)**
   لا تكتب الاسم الأصلي أبداً حتى كتوضيح، مثال: اكتب "تأخر رد المركز" وليس "تأخر رد المركز (فلان الفلاني)".

4) **آخر سطر في التبرير فقط** يجب أن يكون سطراً منفصلاً بأحد التصنيفات التالية بالنص الحرفي بدون أي إضافة:
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

5) الطول: فقرة واحدة مركزة، 3-5 جمل بحد أقصى، بدون تكرار.

===SPLIT===

القسم الثاني: [الأدلة والوقائع التفصيلية والربط الزمني]
اكتب باختصار الأدلة والحقائق المساندة للسبب الرئيسي فقط (مواعيد، فوارق زمنية، نصوص محادثات)، مع الالتزام التام باستخدام (التشغيل) / (المركز) / (العميل) بدلاً من أي اسم شخصي.
"""
    return prompt_text


# ============================================================
# POST-PROCESSING SAFETY NET
# ============================================================

# قائمة كلمات دالة على أن اللي بعدها اسم شخص محتمل، عشان نمسحه لو الموديل هرب
NAME_TRIGGER_PATTERN = re.compile(
    r"\((?:الفني|المشغل|ممثل\s*المركز|موظف\s*التشغيل|العميل)\s*[:：]?\s*[^)]{2,40}\)"
)


def sanitize_names(text: str) -> str:
    """طبقة حماية إضافية: تشيل أي أسماء متسربة داخل أقواس بعد كلمات دالة."""
    return NAME_TRIGGER_PATTERN.sub("", text)


def ensure_single_classification_line(text: str) -> str:
    """يتأكد إن آخر سطر غير فارغ هو تصنيف صالح، بدون تعديل باقي النص."""
    lines = [line for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return text
    last_line = lines[-1].strip()
    if not any(last_line.startswith(c.split(":")[0] + ":") or last_line == c for c in VALID_CLASSIFICATIONS):
        # لو آخر سطر مش تصنيف صريح، سيبه زي ما هو (تنبيه بصري في الواجهة كفاية)
        pass
    return text


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
                    "content": (
                        "أنت Senior Operations وCX Forensic Auditor. اكتب التبرير كجملة سبب مباشرة "
                        "بدون أي مقدمة أو ديباجة، بسبب جذري واحد فقط بدون ذكر أي أسباب ثانوية، "
                        "وبدون ذكر أي اسم شخص إطلاقاً (استخدم فقط: التشغيل / المركز / العميل)، "
                        "وأنهِ الرد بسطر تصنيف واحد فقط من القائمة المحددة بالنص الحرفي."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            top_p=0.9,
            max_tokens=2000,
        )
    except Exception as exc:
        raise Exception(f"خطأ في الاتصال بالذكاء الاصطناعي عبر Groq ({model_name}):\n{str(exc)}")

    if not response or not response.choices:
        raise Exception("Groq returned an empty response.")

    content = response.choices[0].message.content
    content = content.strip() if content else ""
    content = sanitize_names(content)
    content = ensure_single_classification_line(content)
    return content


# ============================================================
# SIDEBAR UI
# ============================================================

with st.sidebar:
    st.image("https://mismarapp.com/static/media/logo.f6cf70e4.svg", width=200)
    st.markdown("### ⚙️ إعدادات النظام")

    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secret_key = ""

    api_key_input = st.text_input("Groq API Key", value=str(secret_key).strip(), type="password")
    api_key = api_key_input.strip()

    available_models = []
    selected_model = None

    if api_key:
        try:
            available_models = get_model_ids(api_key)
            if available_models:
                recommended_model = choose_best_model(available_models)
                default_index = available_models.index(recommended_model) if recommended_model in available_models else 0
                selected_model = st.selectbox("🤖 اختر موديل Groq", options=available_models, index=default_index)
        except Exception as exc:
            st.error("❌ فشل اكتشاف الموديلات")

# ============================================================
# MAIN LAYOUT & INPUTS
# ============================================================

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📋 بيانات الطلب ونوع التدقيق")

    order_id = st.number_input("رقم الطلب (Order ID)", min_value=1, value=1000006, step=1)

    audit_type = st.radio(
        "🔍 اختر المرحلة المطلوب تدقيقها:",
        options=[
            "تأخير مرحلة [جاري الفحص والتشخيص]",
            "تأخير مرحلة [جاري التسعير]",
            "تأخير مرحلة [جاري العمل / الصيانة]",
            "تدقيق التقييمات المنخفضة (عام)"
        ],
        index=2,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🚀 بدء التدقيق واستخراج التبرير المباشر")

# ============================================================
# OUTPUT & RENDERING
# ============================================================

with col2:
    st.subheader("📊 مخرجات التقرير والتدقيق")

    if analyze_btn:
        if not api_key:
            st.error("⚠️ يرجى إدخال Groq API Key.")
        elif not selected_model:
            st.error("⚠️ لم يتم العثور على موديل متاح.")
        else:
            with st.spinner(f"⏳ جاري استخراج التبرير المباشر لـ ({audit_type})..."):
                try:
                    full_response = analyze_order_rating(
                        api_key=api_key,
                        order_id=int(order_id),
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

    st.markdown(f"### 📝 التبرير التشغيلي المباشر:")
    safe_justification = html.escape(justification)

    st.markdown(f'<div class="justification-card">{safe_justification}</div>', unsafe_allow_html=True)

    st.text_area("📋 اضغط Ctrl+A ثم Ctrl+C للنسخ المباشر:", value=justification, height=150)

    st.markdown("### 🔍 الأدلة والوقائع التفصيلية:")
    safe_evidence = html.escape(evidence)

    st.markdown(f'<div class="evidence-card">{safe_evidence}</div>', unsafe_allow_html=True)
else:
    if not analyze_btn:
        st.info("👈 اختر نوع المرحلة ثم اضغط على زر التحليل.")
