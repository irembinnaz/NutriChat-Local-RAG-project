import re
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st

from food_search import search_all_foods

from food_selector import (
    needs_clarification,
    shorten_food_options
)

from nutrition_chat import (
    calculate_total_grams,
    create_meal_tables,
    display_unit,
    normalize_text,
    parse_food_part,
    save_meal,
    split_meal_into_parts
)

from rag_pipeline import RAGPipeline
st.set_page_config(
    page_title="NutriChat",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

PROJECT_DIRECTORY = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_DIRECTORY / "nutrition.db"

st.markdown(
    """
    <style>
    :root {
        --background: #0b1020;
        --surface: #151a32;
        --surface-light: #202746;

        --purple: #9b6dff;
        --pink: #ff5fa2;
        --cyan: #39d5d8;
        --green: #55d68b;
        --yellow: #ffc857;
        --orange: #ff914d;

        --text: #f7f5ff;
        --muted: #b9b6ce;
    }

    .stApp {
        background:
            radial-gradient(
                circle at 12% 8%,
                rgba(155, 109, 255, 0.24),
                transparent 28%
            ),
            radial-gradient(
                circle at 88% 10%,
                rgba(255, 95, 162, 0.18),
                transparent 25%
            ),
            linear-gradient(
                135deg,
                var(--background),
                #111831,
                #17102d
            );

        color: var(--text);
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(
                180deg,
                #0d1326,
                #15102b
            );

        border-right:
            1px solid rgba(155, 109, 255, 0.25);
    }

    [data-testid="stSidebar"] * {
        color: var(--text);
    }

    .main-title {
        font-size: 2.6rem;
        font-weight: 850;
        margin-bottom: 0.2rem;

        background:
            linear-gradient(
                90deg,
                #ffffff,
                var(--purple),
                var(--pink),
                var(--cyan)
            );

        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .subtitle {
        color: var(--muted);
        margin-bottom: 1.4rem;
        font-size: 1rem;
    }

    .welcome-card {
        padding: 1.4rem;
        margin-bottom: 1.2rem;
        border-radius: 22px;

        background:
            linear-gradient(
                135deg,
                rgba(155, 109, 255, 0.20),
                rgba(57, 213, 216, 0.08)
            );

        border:
            1px solid rgba(155, 109, 255, 0.28);

        box-shadow:
            0 12px 30px rgba(0, 0, 0, 0.25);
    }

    .welcome-card h3 {
        color: var(--text);
        margin: 0 0 0.5rem 0;
    }

    .welcome-card p {
        color: var(--muted);
        margin: 0;
    }

    .mode-badge {
        display: inline-block;

        padding: 0.38rem 0.8rem;
        margin: 0.4rem 0 1rem 0;

        border-radius: 999px;

        color: var(--cyan);

        background:
            rgba(57, 213, 216, 0.12);

        border:
            1px solid rgba(57, 213, 216, 0.32);
    }

    .metric-card {
        padding: 1rem;
        min-height: 110px;
        text-align: center;

        border-radius: 18px;

        background:
            linear-gradient(
                145deg,
                rgba(32, 39, 70, 0.96),
                rgba(19, 24, 48, 0.96)
            );

        border:
            1px solid rgba(155, 109, 255, 0.22);

        box-shadow:
            0 8px 22px rgba(0, 0, 0, 0.20);
    }

    .metric-icon {
        font-size: 1.4rem;
        margin-bottom: 0.2rem;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.82rem;
    }

    .metric-value {
        color: var(--text);
        font-size: 1.35rem;
        font-weight: 800;
    }

    div.stButton > button {
        width: 100%;
        min-height: 56px;

        border-radius: 16px;

        color: white;
        font-weight: 700;

        background:
            linear-gradient(
                135deg,
                rgba(155, 109, 255, 0.88),
                rgba(255, 95, 162, 0.76)
            );

        border:
            1px solid rgba(255, 255, 255, 0.10);

        transition:
            transform 0.15s ease,
            border-color 0.15s ease;
    }

    div.stButton > button:hover {
        transform: translateY(-1px);
        border-color: var(--cyan);
        color: white;
    }

    [data-testid="stChatMessage"] {
        padding: 0.4rem;
        border-radius: 18px;

        background:
            rgba(21, 26, 50, 0.74);

        border:
            1px solid rgba(155, 109, 255, 0.18);
    }

    [data-testid="stChatInput"] {
        border-radius: 18px;
    }

    .candidate-title {
        color: var(--yellow);
        font-weight: 750;
        margin-bottom: 0.6rem;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)

if "mode" not in st.session_state:
    st.session_state.mode = "Dashboard"

if "pending_meal" not in st.session_state:
    st.session_state.pending_meal = None

if "dashboard_messages" not in st.session_state:
    st.session_state.dashboard_messages = []

if "meal_messages" not in st.session_state:
    st.session_state.meal_messages = []

if "food_messages" not in st.session_state:
    st.session_state.food_messages = []

if "rag_messages" not in st.session_state:
    st.session_state.rag_messages = []

def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    create_meal_tables(connection)

    return connection


def get_today_records():
    today = datetime.now().date().isoformat()

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                meal_items.food_name,
                meal_items.quantity,
                meal_items.unit,
                meal_items.grams,
                meal_items.calories,
                meal_items.protein,
                meal_items.carbohydrates,
                meal_items.fat,
                meal_items.fiber,
                meal_logs.created_at
            FROM meal_items

            INNER JOIN meal_logs
                ON meal_items.meal_log_id =
                   meal_logs.id

            WHERE SUBSTR(
                meal_logs.created_at,
                1,
                10
            ) = ?

            ORDER BY
                meal_logs.created_at,
                meal_items.id
            """,
            (today,)
        )

        return cursor.fetchall()

    finally:
        connection.close()


def calculate_record_totals(records):
    totals = {
        "calories": 0.0,
        "protein": 0.0,
        "carbohydrates": 0.0,
        "fat": 0.0,
        "fiber": 0.0
    }

    for record in records:
        totals["calories"] += record[4]
        totals["protein"] += record[5]
        totals["carbohydrates"] += record[6]
        totals["fat"] += record[7]
        totals["fiber"] += record[8]

    return totals


def create_today_summary():
    records = get_today_records()

    if not records:
        return (
            "You have not recorded any meals today.\n\n"
            "Select **Calculate my meal** to add your "
            "first meal."
        )

    totals = calculate_record_totals(records)

    lines = [
        "### Foods recorded today"
    ]

    for record in records:
        (
            food_name,
            quantity,
            unit,
            grams,
            calories,
            protein,
            carbohydrates,
            fat,
            fiber,
            created_at
        ) = record

        unit_text = display_unit(
            unit,
            quantity
        )

        time_text = created_at[11:16]

        lines.append(
            (
                f"- **{quantity:g} {unit_text} of "
                f"{food_name}** — "
                f"{grams:.1f} g, "
                f"{calories:.1f} kcal "
                f"at {time_text}"
            )
        )

    lines.extend(
        [
            "",
            "### Today's nutritional total",
            "",
            f"🔥 **Calories:** {totals['calories']:.1f} kcal",
            f"💪 **Protein:** {totals['protein']:.2f} g",
            (
                f"🌾 **Carbohydrates:** "
                f"{totals['carbohydrates']:.2f} g"
            ),
            f"🟠 **Fat:** {totals['fat']:.2f} g",
            f"🌿 **Fiber:** {totals['fiber']:.2f} g"
        ]
    )

    return "\n".join(lines)

def get_active_message_list():

    if st.session_state.mode == "Meal calculation":
        return st.session_state.meal_messages

    if st.session_state.mode == "Single food":
        return st.session_state.food_messages

    if st.session_state.mode == "Nutrition RAG":
        return st.session_state.rag_messages

    return st.session_state.dashboard_messages


def add_message(role, content):
    get_active_message_list().append(
        {
            "role": role,
            "content": content
        }
    )


def is_greeting(text):
    normalized = normalize_text(text)

    return normalized in {
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening"
    }


def is_today_summary_question(text):
    normalized = normalize_text(text)

    phrases = [
        "what did i eat today",
        "what have i eaten today",
        "show today s nutrition",
        "show todays nutrition",
        "show today s total",
        "show todays total",
        "how many calories today",
        "calories today",
        "daily total",
        "my total today"
    ]

    return any(
        phrase in normalized
        for phrase in phrases
    )


def is_meal_message(text):
    normalized = normalize_text(text)

    meal_phrases = [
        "i ate",
        "i had",
        "i have eaten",
        "today i ate",
        "today i had",
        "for breakfast",
        "for lunch",
        "for dinner",
        "for snack"
    ]

    if any(
        phrase in normalized
        for phrase in meal_phrases
    ):
        return True

    return bool(
        re.search(
            (
                r"^(?:"
                r"\d+(?:\.\d+)?|"
                r"a|an|one|two|three|four|five|"
                r"six|seven|eight|nine|ten|half"
                r")\s+"
            ),
            normalized
        )
    )


def normalize_portion_words(text):

    text = re.sub(
        r"\bglasses\b",
        "cups",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\bglass\b",
        "cup",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\bcacik\b",
        "tzatziki",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\bcacık\b",
        "tzatziki",
        text,
        flags=re.IGNORECASE
    )

    return text


def clean_single_food_message(text):
    cleaned = text.strip()

    patterns = [
        r"^how many calories are in\s+",
        r"^how many calories in\s+",
        r"^what are the calories in\s+",
        r"^calories in\s+",
        r"^check\s+"
    ]

    for pattern in patterns:
        cleaned = re.sub(
            pattern,
            "",
            cleaned,
            flags=re.IGNORECASE
        )

    return cleaned.strip(" ?.")

def calculate_selected_food(
    cursor,
    parsed_food,
    selected_food
):
    food_query = parsed_food["food_query"]
    quantity = parsed_food["quantity"]
    unit = parsed_food["unit"]

    total_grams, portion_source = (
        calculate_total_grams(
            cursor,
            selected_food,
            food_query,
            quantity,
            unit
        )
    )

    ratio = total_grams / 100

    return {
        "food_query": food_query,
        "database_name": selected_food["name"],
        "quantity": quantity,
        "unit": unit,
        "grams": total_grams,

        "calories": (
            selected_food["calories_per_100g"]
            * ratio
        ),

        "protein": (
            selected_food["protein_per_100g"]
            * ratio
        ),

        "carbohydrates": (
            selected_food[
                "carbohydrates_per_100g"
            ]
            * ratio
        ),

        "fat": (
            selected_food["fat_per_100g"]
            * ratio
        ),

        "fiber": (
            selected_food["fiber_per_100g"]
            * ratio
        ),

        "source": selected_food["source"],
        "portion_source": portion_source
    }


def calculate_meal_totals(results):
    totals = {
        "calories": 0.0,
        "protein": 0.0,
        "carbohydrates": 0.0,
        "fat": 0.0,
        "fiber": 0.0
    }

    for result in results:
        totals["calories"] += result["calories"]
        totals["protein"] += result["protein"]

        totals["carbohydrates"] += (
            result["carbohydrates"]
        )

        totals["fat"] += result["fat"]
        totals["fiber"] += result["fiber"]

    return totals


def format_meal_result(
    results,
    saved_to_log,
    incomplete_meal=False
):
    totals = calculate_meal_totals(results)

    if not saved_to_log and not incomplete_meal:
        result_title = "### I understood the following food"
    else:
        result_title = "### I understood the following meal"

    lines = [result_title]

    for result in results:
        unit_text = display_unit(
            result["unit"],
            result["quantity"]
        )

        lines.append(
            (
                f"- **{result['quantity']:g} "
                f"{unit_text} of "
                f"{result['food_query']}**"
            )
        )

        lines.append(
            (
                f"  - Matched food: "
                f"{result['database_name']}"
            )
        )

        lines.append(
            (
                f"  - Estimated weight: "
                f"{result['grams']:.1f} g"
            )
        )

    lines.extend(
        [
            "",
            "### Estimated nutrition",
            "",
            f"🔥 **Calories:** {totals['calories']:.1f} kcal",
            f"💪 **Protein:** {totals['protein']:.2f} g",
            (
                f"🌾 **Carbohydrates:** "
                f"{totals['carbohydrates']:.2f} g"
            ),
            f"🟠 **Fat:** {totals['fat']:.2f} g",
            f"🌿 **Fiber:** {totals['fiber']:.2f} g"
        ]
    )

    if saved_to_log:
        lines.extend(
            [
                "",
                "✅ This meal was saved to today's log."
            ]
        )

    elif incomplete_meal:
        lines.extend(
            [
                "",
                "⚠️ This meal was not saved to today's log "
                "because one or more foods could not be calculated.",
                "Please correct the missing foods and try again."
            ]
        )

    else:
        lines.extend(
            [
                "",
                "This single-food calculation was not "
                "added to today's log."
            ]
        )

    return "\n".join(lines)


def finish_pending_meal():
    pending = st.session_state.pending_meal

    if pending is None:
        return

    results = pending["results"]
    original_message = pending["original_message"]
    save_to_log = pending["save_to_log"]
    has_errors = bool(pending["errors"])

    if not results:
        add_message(
            "assistant",
            "I could not calculate this food or meal."
        )

        st.session_state.pending_meal = None
        return

    actually_saved = (
        save_to_log
        and not has_errors
    )

    if actually_saved:
        connection = get_connection()

        try:
            save_meal(
                connection,
                original_message,
                results
            )

        finally:
            connection.close()

    result_message = format_meal_result(
        results,
        saved_to_log=actually_saved,
        incomplete_meal=(
            save_to_log
            and has_errors
        )
    )

    add_message(
        "assistant",
        result_message
    )

    st.session_state.pending_meal = None


def continue_pending_meal():
    pending = st.session_state.pending_meal

    if pending is None:
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        while (
            pending["current_index"]
            < len(pending["parsed_foods"])
        ):
            parsed_food = pending["parsed_foods"][
                pending["current_index"]
            ]

            food_query = parsed_food["food_query"]

            candidates = search_all_foods(
                cursor,
                food_query,
                limit=10
            )

            if not candidates:
                pending["errors"].append(
                    (
                        f"No matching food was found for "
                        f"'{food_query}'."
                    )
                )

                pending["current_index"] += 1
                continue

            if needs_clarification(
                food_query,
                candidates
            ):
                options = shorten_food_options(
                    candidates,
                    limit=5
                )

                pending["current_candidates"] = options

                add_message(
                    "assistant",
                    (
                        f"I found several possible matches "
                        f"for **{food_query}**.\n\n"
                        "Choose the food you meant below."
                    )
                )

                st.session_state.pending_meal = pending
                return

            selected_food = candidates[0]

            result = calculate_selected_food(
                cursor,
                parsed_food,
                selected_food
            )

            pending["results"].append(result)
            pending["current_index"] += 1

        st.session_state.pending_meal = pending

    finally:
        connection.close()

    if pending["errors"]:
        error_message = "\n".join(
            f"- {error}"
            for error in pending["errors"]
        )

        add_message(
            "assistant",
            (
                "Some foods could not be calculated:\n\n"
                f"{error_message}"
            )
        )

    finish_pending_meal()


def start_food_calculation(
    user_message,
    save_to_log
):
    prepared_message = normalize_portion_words(
        user_message
    )

    if not save_to_log:
        prepared_message = clean_single_food_message(
            prepared_message
        )

    meal_parts = split_meal_into_parts(
        prepared_message
    )

    parsed_foods = [
        parse_food_part(part)
        for part in meal_parts
    ]

    if not parsed_foods:
        add_message(
            "assistant",
            (
                "I could not identify a food in that "
                "message. Try writing the quantity and "
                "food name together."
            )
        )

        return

    st.session_state.pending_meal = {
        "original_message": user_message,
        "parsed_foods": parsed_foods,
        "current_index": 0,
        "results": [],
        "errors": [],
        "current_candidates": [],
        "save_to_log": save_to_log
    }

    continue_pending_meal()


def choose_candidate(candidate):
    pending = st.session_state.pending_meal

    if pending is None:
        return

    parsed_food = pending["parsed_foods"][
        pending["current_index"]
    ]

    connection = get_connection()
    cursor = connection.cursor()

    try:
        result = calculate_selected_food(
            cursor,
            parsed_food,
            candidate
        )

    finally:
        connection.close()

    pending["results"].append(result)
    pending["current_index"] += 1
    pending["current_candidates"] = []

    st.session_state.pending_meal = pending

    continue_pending_meal()

@st.cache_resource(show_spinner=False)
def get_rag_pipeline(database_path_text):

    database_path = Path(database_path_text)

    pipeline = RAGPipeline(
        database_path=database_path
    )

    pipeline.start()

    return pipeline


def process_rag_question(question):

    try:
        with st.spinner(
            "Thinking about your nutrition question..."
        ):
            pipeline = get_rag_pipeline(
                str(DATABASE_PATH)
            )

            result = pipeline.answer_question(
                question,
                top_k=3
            )

        answer = str(
            result.get("answer", "")
        ).strip()

        if not answer:
            answer = (
                "I could not create an answer right now. "
                "Please try asking the question again."
            )

        add_message(
            "assistant",
            answer
        )

    except Exception as error:
        print(
            "RAG error:",
            type(error).__name__ + ":",
            error
        )

        add_message(
            "assistant",
            (
                "I could not answer that question right now. "
                "Please try again."
            )
        )

def ensure_screen_intro(mode):

    if mode == "Meal calculation":
        if not st.session_state.meal_messages:
            st.session_state.meal_messages = [
                {
                    "role": "assistant",
                    "content": (
                        "Tell me everything you ate in one message.\n\n"
                        "Example: `I ate two eggs, one raw apple and "
                        "150 grams of skinless chicken breast.`"
                    )
                }
            ]

    elif mode == "Single food":
        if not st.session_state.food_messages:
            st.session_state.food_messages = [
                {
                    "role": "assistant",
                    "content": (
                        "Write the food and amount you would like to "
                        "calculate.\n\n"
                        "Example: `one banana` or `150 grams of yogurt`."
                    )
                }
            ]

    elif mode == "Nutrition RAG":
        if not st.session_state.rag_messages:
            st.session_state.rag_messages = [
                {
                    "role": "assistant",
                    "content": (
                        "Ask me a nutrition question. I will use my local "
                        "nutrition knowledge to answer it.\n\n"
                        "Example: `Why is water important for the body?`"
                    )
                }
            ]


def open_screen(mode):

    st.session_state.pending_meal = None
    st.session_state.mode = mode
    ensure_screen_intro(mode)
    st.rerun()


def back_to_dashboard():
    st.session_state.pending_meal = None
    st.session_state.mode = "Dashboard"
    st.rerun()


def render_mode_badge():
    st.markdown(
        (
            '<div class="mode-badge">'
            f'Current mode: {st.session_state.mode}'
            '</div>'
        ),
        unsafe_allow_html=True
    )


def render_today_metric_cards():
    records = get_today_records()
    totals = calculate_record_totals(records)

    st.markdown("### Today's nutrition total")

    metric_columns = st.columns(5)

    metric_information = [
        (
            "🔥",
            "Today's Calories",
            f"{totals['calories']:.0f} kcal"
        ),
        (
            "💪",
            "Today's Protein",
            f"{totals['protein']:.1f} g"
        ),
        (
            "🌾",
            "Today's Carbohydrates",
            f"{totals['carbohydrates']:.1f} g"
        ),
        (
            "🟠",
            "Today's Fat",
            f"{totals['fat']:.1f} g"
        ),
        (
            "🌿",
            "Today's Fiber",
            f"{totals['fiber']:.1f} g"
        )
    ]

    for column, information in zip(
        metric_columns,
        metric_information
    ):
        icon, label, value = information

        with column:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon">{icon}</div>
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True
            )


def render_chat_messages(messages):
    for message in messages:
        avatar = (
            "🤖"
            if message["role"] == "assistant"
            else "🧑"
        )

        with st.chat_message(
            message["role"],
            avatar=avatar
        ):
            st.markdown(message["content"])


def render_food_candidates():
    pending = st.session_state.pending_meal

    if (
        pending is None
        or not pending["current_candidates"]
    ):
        return

    current_food = pending["parsed_foods"][
        pending["current_index"]
    ]

    st.markdown(
        (
            '<div class="candidate-title">'
            f"Choose the correct match for "
            f"{current_food['food_query']}:"
            '</div>'
        ),
        unsafe_allow_html=True
    )

    candidates = pending["current_candidates"]

    for index, candidate in enumerate(candidates):
        button_label = (
            f"{candidate['name']} — "
            f"{candidate['calories_per_100g']:.1f} "
            f"kcal / 100 g"
        )

        if st.button(
            button_label,
            key=(
                f"candidate_"
                f"{pending['current_index']}_"
                f"{index}_"
                f"{candidate.get('fdc_id')}_"
                f"{candidate.get('food_id')}"
            )
        ):
            choose_candidate(candidate)
            st.rerun()

    if st.button(
        "None of these",
        key="none_of_candidates"
    ):
        add_message(
            "assistant",
            (
                "Please describe the food in more detail "
                "and send it again."
            )
        )

        st.session_state.pending_meal = None
        st.rerun()

with st.sidebar:
    st.markdown("## 🥗 NutriChat")

    st.caption(
        "Local nutrition and RAG assistant"
    )

    st.divider()

    st.markdown("### Navigation")

    if st.button(
        "💬 Chat",
        use_container_width=True
    ):
        back_to_dashboard()

    if st.button(
        "📋 Today's Log",
        use_container_width=True
    ):
        open_screen("Today's nutrition")

    if st.button(
        "📚 Nutrition Knowledge",
        use_container_width=True
    ):
        open_screen("Nutrition RAG")

    st.divider()

    st.markdown("### System Status")

    if DATABASE_PATH.exists():
        st.success("SQLite connected")
    else:
        st.error("Database missing")

    st.success("FNDDS ready")
    st.success("Local RAG ready")

    st.divider()

    if st.button(
        "🗑️ Clear conversations",
        use_container_width=True
    ):
        st.session_state.dashboard_messages = []
        st.session_state.meal_messages = []
        st.session_state.food_messages = []
        st.session_state.rag_messages = []
        st.session_state.pending_meal = None
        st.session_state.mode = "Dashboard"
        st.rerun()

if st.session_state.mode == "Dashboard":
    st.markdown(
        (
            '<div class="main-title">'
            'NutriChat Assistant'
            '</div>'
        ),
        unsafe_allow_html=True
    )

    st.markdown(
        (
            '<div class="subtitle">'
            'Meal calculation, daily tracking, and local '
            'nutrition knowledge in one place.'
            '</div>'
        ),
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="welcome-card">
            <h3>Hello! How can I help you today?</h3>
            <p>
                Choose one of the features below to get started.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    render_today_metric_cards()

    st.write("")

    suggestion_column_1, suggestion_column_2 = (
        st.columns(2)
    )

    with suggestion_column_1:
        if st.button(
            "🔥 Calculate my meal",
            key="dashboard_calculate_meal"
        ):
            open_screen("Meal calculation")

        if st.button(
            "📊 Show today's nutrition",
            key="dashboard_today_summary"
        ):
            open_screen("Today's nutrition")

    with suggestion_column_2:
        if st.button(
            "🍌 Check a food's calories",
            key="dashboard_single_food"
        ):
            open_screen("Single food")

        if st.button(
            "💡 Ask a nutrition question",
            key="dashboard_nutrition_rag"
        ):
            open_screen("Nutrition RAG")

    render_mode_badge()

    st.info(
        "Choose a feature above. Each feature opens in its own "
        "workspace so the conversations do not get mixed together."
    )

elif st.session_state.mode == "Meal calculation":
    if st.button(
        "← Back to dashboard",
        key="meal_back"
    ):
        back_to_dashboard()

    st.markdown("# 🔥 Meal Calculator")
    st.caption(
        "Calculate one meal at a time. Successful meals are added "
        "to today's nutrition total."
    )

    render_mode_badge()
    render_chat_messages(st.session_state.meal_messages)
    render_food_candidates()

    if st.session_state.pending_meal is None:
        user_message = st.chat_input(
            "Tell me everything you ate...",
            key="meal_chat_input"
        )

        if user_message:
            add_message("user", user_message)
            start_food_calculation(
                user_message,
                save_to_log=True
            )
            st.rerun()
    else:
        st.info(
            "Choose one of the food options above to continue."
        )

elif st.session_state.mode == "Single food":
    if st.button(
        "← Back to dashboard",
        key="food_back"
    ):
        back_to_dashboard()

    st.markdown("# 🍌 Food Calorie Checker")
    st.caption(
        "Check a food without adding it to today's log."
    )

    render_mode_badge()
    render_chat_messages(st.session_state.food_messages)
    render_food_candidates()

    if st.session_state.pending_meal is None:
        user_message = st.chat_input(
            "Example: one banana or 150 grams of yogurt...",
            key="food_chat_input"
        )

        if user_message:
            add_message("user", user_message)
            start_food_calculation(
                user_message,
                save_to_log=False
            )
            st.rerun()
    else:
        st.info(
            "Choose one of the food options above to continue."
        )

elif st.session_state.mode == "Nutrition RAG":
    ensure_screen_intro("Nutrition RAG")

    if st.button(
        "← Back to dashboard",
        key="rag_back"
    ):
        back_to_dashboard()

    st.markdown("# 💡 Nutrition Assistant")
    st.caption(
        "Ask nutrition questions using the local RAG knowledge base."
    )

    render_mode_badge()
    render_chat_messages(st.session_state.rag_messages)

    question = st.chat_input(
        "Ask a nutrition question...",
        key="rag_chat_input"
    )

    if question:
        add_message("user", question)
        process_rag_question(question)
        st.rerun()

elif st.session_state.mode == "Today's nutrition":
    if st.button(
        "← Back to dashboard",
        key="today_back"
    ):
        back_to_dashboard()

    st.markdown("# 📊 Today's Nutrition")
    st.caption(
        "Your meals and nutrition totals recorded for today."
    )

    render_mode_badge()
    render_today_metric_cards()
    st.write("")

    st.markdown(create_today_summary())