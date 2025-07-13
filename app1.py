
# ─── Meal Suggestion Logic ───
import random

def suggest_meal(df, targets, trials=2000, portion_sizes=[0.5, 1.0, 1.5], max_items=3):
    def score(meal, targets):
        return sum(abs(meal[m].sum() - targets[m]) / (targets[m] + 1e-6) for m in targets)

    best_score = float('inf')
    best_combo = None

    for _ in range(trials):
        sampled = df.sample(n=random.randint(2, max_items))
        portions = np.random.choice(portion_sizes, size=len(sampled))
        meal = sampled.copy()
        meal["Quantity"] = portions
        meal["Calories"] = meal["Calories (kcal)"] * portions
        meal["Protein"] = meal["Protein (g)"] * portions
        meal["Carbs"] = meal["Carbs (g)"] * portions
        meal["Fats"] = meal["Fats (g)"] * portions
        s = score(meal, targets)
        if s < best_score:
            best_score = s
            best_combo = meal
    return best_combo


# Final version of app.py for Nutrition Tracker with macronutrient targets and visual feedback

# To run: streamlit run app.py

try:
    import streamlit as st
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime
    import os
    from collections import defaultdict
except ModuleNotFoundError as e:
    print("\n[ERROR] Required module not found:", e)
    print("Please install the missing package(s) using: pip install streamlit pandas plotly")
    exit()

# ─── Session State Setup ───
if "reset_trigger" not in st.session_state:
    st.session_state.reset_trigger = False

if "targets" not in st.session_state:
    st.session_state.targets = {
        "Calories": 2500,
        "Protein": 150,
        "Carbs": 200,
        "Fats": 70
    }

# ─── File Paths ───
log_file = "nutrition_log.csv"
food_file = "calorie_calculator.csv"

# ─── Load Food Data ───
@st.cache_data
def load_data():
    df = pd.read_csv(food_file)
    columns = ['Food Item', 'Serving Size', 'Calories (kcal)', 'Protein (g)', 'Carbs (g)', 'Fats (g)', 'Quantity']
    return df[columns].dropna(subset=["Food Item"]).reset_index(drop=True)

df = load_data()

# ─── Sidebar ───
with st.sidebar:
    st.header("🏋️ Macronutrient Targets")
    for macro in ["Calories", "Protein", "Carbs", "Fats"]:
        default = st.session_state.targets[macro]
        step = 50 if macro == "Calories" else 5
        st.session_state.targets[macro] = st.number_input(macro, value=default, step=step)

    st.header("📅 Log Options")
    if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
        if st.button("🧹 Clear Nutrition Log"):
            os.remove(log_file)
            st.success("Log cleared!")

        with open(log_file, "rb") as f:
            st.download_button(
                label="📅 Download Full Log (CSV)",
                data=f,
                file_name="nutrition_log.csv",
                mime="text/csv"
            )

# ─── Title + Reset Button ───
st.title("🥗 Multi-Food Nutrition Calculator")
if st.button("🔄 Reset Selection"):
    st.session_state.reset_trigger = True
    st.rerun()

# ─── Meal Selection ───
if st.session_state.reset_trigger:
    meal_tag = st.text_input("📝 Meal Tag", value="", key="tag_reset")
    selected_items = st.multiselect("Select food items:", df["Food Item"].unique(), default=[], key="select_reset")
    st.session_state.reset_trigger = False
else:
    meal_tag = st.text_input("📝 Meal Tag", key="tag")
    selected_items = st.multiselect("Select food items:", df["Food Item"].unique(), key="select")

results = []
if selected_items:
    st.write("### 🍽️ Set Quantities")
    for item in selected_items:
        row = df[df["Food Item"] == item].iloc[0]
        st.markdown(f"**{item}** — *{row['Serving Size']}*")
        qty = st.number_input(
            f"Quantity for {item}", min_value=0.0, step=0.1, value=float(row["Quantity"]), key=item
        )
        results.append({
            "Food Item": item,
            "Quantity": qty,
            "Calories": round(row["Calories (kcal)"] * qty, 2),
            "Protein": round(row["Protein (g)"] * qty, 2),
            "Carbs": round(row["Carbs (g)"] * qty, 2),
            "Fats": round(row["Fats (g)"] * qty, 2)
        })

# ─── Summary + Save ───
if results:
    df_summary = pd.DataFrame(results)
    total = df_summary[["Calories", "Protein", "Carbs", "Fats"]].sum()
    total["Food Item"] = "Total"
    total["Quantity"] = ""
    df_summary = pd.concat([df_summary, pd.DataFrame([total])], ignore_index=True)

    st.write("### 📊 Nutrition Summary")
    st.dataframe(df_summary, use_container_width=True)

    prot_kcal = total["Protein"] * 4
    carb_kcal = total["Carbs"] * 4
    fat_kcal = total["Fats"] * 9
    total_kcal = prot_kcal + carb_kcal + fat_kcal

    st.markdown("### 🥧 Macronutrient Breakdown")
    fig = go.Figure(data=[go.Pie(
        labels=[
            f"Protein ({total['Protein']:.1f}g)",
            f"Carbs ({total['Carbs']:.1f}g)",
            f"Fats ({total['Fats']:.1f}g)"
        ],
        values=[prot_kcal, carb_kcal, fat_kcal],
        textinfo="label+percent",
        hoverinfo="label+value+percent",
        hole=0.3
    )])
    fig.update_layout(title=f"Total: {int(total_kcal)} kcal")
    st.plotly_chart(fig, use_container_width=True)

    if st.button("✅ Save Meal to Log"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tag = meal_tag if meal_tag else "Untitled"

        meal_data = df_summary[df_summary["Food Item"] != "Total"].copy()
        meal_data["Timestamp"] = ""
        meal_data["Meal Tag"] = ""

        summary_row = {
            "Food Item": "Meal Logged",
            "Quantity": "",
            "Calories": total["Calories"],
            "Protein": total["Protein"],
            "Carbs": total["Carbs"],
            "Fats": total["Fats"],
            "Timestamp": timestamp,
            "Meal Tag": tag
        }

        divider_row = {k: "" for k in summary_row}
        divider_row["Food Item"] = "---"

        log_df = pd.concat([
            meal_data,
            pd.DataFrame([summary_row]),
            pd.DataFrame([divider_row])
        ], ignore_index=True)

        if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
            try:
                existing = pd.read_csv(log_file)
                full_log = pd.concat([existing, log_df], ignore_index=True)
            except pd.errors.EmptyDataError:
                full_log = log_df
        else:
            full_log = log_df

        full_log.to_csv(log_file, index=False)
        st.success("Meal saved to log!")
        st.session_state.reset_trigger = True
        st.rerun()

# ─── Preview Log with Day-wise Grouping ───
st.markdown("### 📖 Meal Log Preview (Grouped by Day)")

if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
    log_df = pd.read_csv(log_file).fillna("")
    meals = log_df[log_df["Food Item"] == "Meal Logged"]
    day_groups = defaultdict(list)

    for i in meals.index:
        day = log_df.loc[i, "Timestamp"].split()[0]
        day_groups[day].append(i)

    def color_macro(actual, target):
        if actual >= 1.1 * target:
            return "red"
        elif actual >= 0.9 * target:
            return "green"
        else:
            return "orange"

    for day, indices in day_groups.items():
        st.markdown(f"## 📅 {day}")
        cols = st.columns(2)
        col_idx = 0

        daily_p = daily_c = daily_f = daily_kcal = 0

        for i in indices:
            meal_row = log_df.loc[i]
            tag = meal_row["Meal Tag"]
            ts = meal_row["Timestamp"]

            start = i - 1
            while start >= 0 and log_df.loc[start, "Food Item"] not in ["Meal Logged", "---"]:
                start -= 1
            data = log_df.iloc[start+1:i]

            p = data["Protein"].sum()
            c = data["Carbs"].sum()
            f = data["Fats"].sum()
            kcal = p*4 + c*4 + f*9

            daily_p += p
            daily_c += c
            daily_f += f
            daily_kcal += kcal

            pie = go.Figure(data=[go.Pie(
                labels=[f"Protein ({p:.1f}g)", f"Carbs ({c:.1f}g)", f"Fats ({f:.1f}g)"],
                values=[p*4, c*4, f*9],
                textinfo="label+percent",
                hole=0.3
            )])
            pie.update_layout(title=f"Total: {int(kcal)} kcal")

            with cols[col_idx]:
                st.plotly_chart(pie, use_container_width=True)
                st.markdown(f"**🕒 {ts}** | 🏷️ **{tag}**")
            col_idx = (col_idx + 1) % 2

        st.markdown("#### 📊 Daily Totals vs Targets")
        for macro, actual, target in zip(
            ["Calories", "Protein", "Carbs", "Fats"],
            [daily_kcal, daily_p, daily_c, daily_f],
            [st.session_state.targets["Calories"], st.session_state.targets["Protein"], st.session_state.targets["Carbs"], st.session_state.targets["Fats"]]
        ):
            color = color_macro(actual, target)
            st.markdown(
                f"**{macro}:** {actual:.1f} / {target}  ➜  <span style='color:{color}'>Remaining: {max(0, target - actual):.1f}</span>",
                unsafe_allow_html=True
            )
            pct = min(actual / target, 1.0)
            st.progress(pct)
        st.markdown("---")

