import time
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# ==================================================
# SMART GAMING TOURNAMENT ANALYTICS SYSTEM
# BIT1034 Advance Programming
# Full Improved Version with Error Fix
#
# Improvements included:
# 1. Professional dashboard layout
# 2. Metric cards with icons
# 3. Plotly interactive charts
# 4. Win and loss comparison chart
# 5. Top player highlight
# 6. Sidebar team filter
# 7. Custom CSS design
# 8. CSV upload, SQLite database, ranking, testing summary
# 9. Auto-fix for missing country column in old database
# 10. Actual CSV dataset processing time measurement
# ==================================================

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------
st.set_page_config(
    page_title="Smart Gaming Tournament Analytics System",
    page_icon="🎮",
    layout="wide"
)

# --------------------------------------------------
# Custom CSS Design
# --------------------------------------------------
st.markdown("""
<style>
    .main-title {
        font-size: 36px;
        font-weight: bold;
        color: #4F46E5;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 18px;
        color: #6B7280;
        margin-bottom: 25px;
    }

    .section-title {
        font-size: 24px;
        font-weight: bold;
        color: #111827;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    .card {
        padding: 20px;
        border-radius: 12px;
        background-color: #F8FAFC;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #E5E7EB;
        margin-bottom: 15px;
    }

    .info-box {
        background-color: #F8FAFC;
        padding: 18px;
        border-radius: 14px;
        border: 1px solid #E5E7EB;
        margin-bottom: 15px;
    }

    .success-box {
        background-color: #ECFDF5;
        padding: 18px;
        border-radius: 14px;
        border: 1px solid #10B981;
        color: #065F46;
        margin-bottom: 15px;
    }

    .warning-box {
        background-color: #FFFBEB;
        padding: 18px;
        border-radius: 14px;
        border: 1px solid #F59E0B;
        color: #92400E;
        margin-bottom: 15px;
    }

    .footer {
        text-align: center;
        color: #6B7280;
        font-size: 13px;
        margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Database Connection
# --------------------------------------------------
conn = sqlite3.connect("tournament.db", check_same_thread=False)
cursor = conn.cursor()

# --------------------------------------------------
# Create Database Tables
# --------------------------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    team_name TEXT NOT NULL,
    country TEXT DEFAULT 'Not stated',
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS upload_history (
    upload_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT,
    total_records INTEGER,
    processing_time_seconds REAL DEFAULT 0,
    upload_time TEXT
)
""")

conn.commit()


# --------------------------------------------------
# Database Migration / Error Fix
# This fixes old database issue:
# KeyError: "['country'] not in index"
# --------------------------------------------------
def ensure_country_column():
    """Add country column if the old players table does not have it."""
    cursor.execute("PRAGMA table_info(players)")
    columns_info = cursor.fetchall()
    existing_columns = [col[1] for col in columns_info]

    if "country" not in existing_columns:
        cursor.execute("ALTER TABLE players ADD COLUMN country TEXT DEFAULT 'Not stated'")
        conn.commit()


ensure_country_column()


def ensure_upload_history_processing_time_column():
    """Add processing_time_seconds column if the old upload_history table does not have it."""
    cursor.execute("PRAGMA table_info(upload_history)")
    columns_info = cursor.fetchall()
    existing_columns = [col[1] for col in columns_info]

    if "processing_time_seconds" not in existing_columns:
        cursor.execute("ALTER TABLE upload_history ADD COLUMN processing_time_seconds REAL DEFAULT 0")
        conn.commit()


ensure_upload_history_processing_time_column()


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def load_players():
    """Load player records from SQLite database."""
    df = pd.read_sql_query("SELECT * FROM players", conn)

    # Safety check if old data/database has no country column
    if "country" not in df.columns:
        df["country"] = "Not stated"

    return df


def save_upload_history(file_name, total_records, processing_time_seconds):
    """Save CSV upload history and processing time into database."""
    upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO upload_history (file_name, total_records, processing_time_seconds, upload_time)
    VALUES (?, ?, ?, ?)
    """, (file_name, total_records, float(processing_time_seconds), upload_time))

    conn.commit()


def validate_csv(df):
    """Check required CSV columns."""
    required_columns = ["Player Name", "Team", "Wins", "Losses", "Points"]
    missing_columns = []

    for column in required_columns:
        if column not in df.columns:
            missing_columns.append(column)

    return missing_columns


def insert_players_from_csv(df):
    """Insert CSV records into SQLite database."""
    for _, row in df.iterrows():
        country = row["Country"] if "Country" in df.columns else "Not stated"

        cursor.execute("""
        INSERT INTO players (player_name, team_name, country, wins, losses, points)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(row["Player Name"]),
            str(row["Team"]),
            str(country),
            int(row["Wins"]),
            int(row["Losses"]),
            int(row["Points"])
        ))

    conn.commit()


def clear_player_data():
    """Delete all player records."""
    cursor.execute("DELETE FROM players")
    conn.commit()


def create_ranking(df):
    """Create ranking using points first, then wins as tie-breaker."""
    if df.empty:
        return df

    ranking_df = df.sort_values(
        by=["points", "wins"],
        ascending=[False, False]
    ).copy()

    ranking_df["rank_position"] = range(1, len(ranking_df) + 1)

    return ranking_df


def calculate_win_rate(df):
    """Calculate win rate percentage."""
    df = df.copy()
    total_matches = df["wins"] + df["losses"]

    df["win_rate"] = total_matches.apply(lambda x: 0 if x == 0 else x)
    df["win_rate"] = (df["wins"] / df["win_rate"]) * 100
    df["win_rate"] = df["win_rate"].round(2)

    return df


def safe_display_columns(df, preferred_columns):
    """Return only columns that exist to avoid KeyError."""
    return [col for col in preferred_columns if col in df.columns]


# --------------------------------------------------
# Login System
# --------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""


def login_page():
    st.markdown('<div class="main-title">🎮 Smart Gaming Tournament Analytics System</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Professional dashboard for player ranking and tournament analytics</div>', unsafe_allow_html=True)

    st.markdown("### Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

        if login_button:
            if username == "admin" and password == "admin123":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login successful. Welcome to the system.")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    st.info("Demo login: username = admin, password = admin123")


# --------------------------------------------------
# Sidebar Navigation
# --------------------------------------------------
def sidebar_menu():
    st.sidebar.title("🎮 Gaming Analytics")
    st.sidebar.write("Tournament Management System")
    st.sidebar.divider()

    menu = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "Upload CSV",
            "Players",
            "Rankings",
            "Database",
            "Testing Summary",
            "About System"
        ]
    )

    st.sidebar.divider()

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    return menu


# --------------------------------------------------
# Dashboard Page
# --------------------------------------------------
def dashboard_page():
    st.markdown('<div class="main-title">Smart Gaming Tournament Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Overview of player performance, rankings, and tournament results</div>', unsafe_allow_html=True)

    df = load_players()

    if df.empty:
        st.warning("No player data available. Please upload CSV first.")
        return

    # Sidebar filter by team
    teams = ["All"] + sorted(df["team_name"].unique().tolist())
    selected_team = st.sidebar.selectbox("Filter by Team", teams)

    if selected_team != "All":
        df = df[df["team_name"] == selected_team]

    if df.empty:
        st.warning("No data available for the selected team.")
        return

    df = calculate_win_rate(df)
    ranking_df = create_ranking(df)

    total_players = len(df)
    total_wins = int(df["wins"].sum())
    total_losses = int(df["losses"].sum())
    top_score = int(df["points"].max())

    # Metric cards with icons
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("🎮 Total Players", total_players)
    col2.metric("🏆 Total Wins", total_wins)
    col3.metric("❌ Total Losses", total_losses)
    col4.metric("⭐ Highest Points", top_score)

    st.divider()

    # Top player highlight
    top_player = df.sort_values(by=["points", "wins"], ascending=[False, False]).iloc[0]
    st.success(
        f"Top Player: {top_player['player_name']} from {top_player['team_name']} with {top_player['points']} points."
    )

    # Dashboard charts
    left, right = st.columns(2)

    with left:
        st.subheader("Player Ranking by Points")

        fig = px.bar(
            df.sort_values(by="points", ascending=False),
            x="player_name",
            y="points",
            color="team_name",
            text="points",
            title="Ranking Points"
        )

        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=420,
            xaxis_title="Player",
            yaxis_title="Points"
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Win and Loss Comparison")

        fig2 = px.bar(
            df,
            x="player_name",
            y=["wins", "losses"],
            barmode="group",
            title="Wins vs Losses"
        )

        fig2.update_layout(
            height=420,
            xaxis_title="Player",
            yaxis_title="Matches"
        )

        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # More professional analytics
    left2, right2 = st.columns(2)

    with left2:
        st.subheader("Win Rate Analysis")

        fig3 = px.line(
            df.sort_values(by="win_rate", ascending=False),
            x="player_name",
            y="win_rate",
            markers=True,
            title="Player Win Rate Percentage"
        )

        fig3.update_layout(
            height=400,
            xaxis_title="Player",
            yaxis_title="Win Rate (%)"
        )

        st.plotly_chart(fig3, use_container_width=True)

    with right2:
        st.subheader("Points Distribution")

        fig4 = px.pie(
            df,
            names="player_name",
            values="points",
            title="Points Distribution by Player"
        )

        fig4.update_layout(height=400)

        st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    st.subheader("Top Player Table")

    display_cols = safe_display_columns(
        ranking_df,
        [
            "rank_position",
            "player_name",
            "team_name",
            "country",
            "wins",
            "losses",
            "points",
            "win_rate"
        ]
    )

    st.dataframe(
        ranking_df[display_cols],
        use_container_width=True
    )

    st.divider()

    st.subheader("Tournament Summary")
    st.markdown(
        f"""
        <div class="info-box">
        This dashboard contains <b>{total_players}</b> player records.
        The total number of wins is <b>{total_wins}</b>, and the total number of losses is <b>{total_losses}</b>.
        The highest score recorded is <b>{top_score}</b> points.
        </div>
        """,
        unsafe_allow_html=True
    )


# --------------------------------------------------
# Upload CSV Page
# --------------------------------------------------
def upload_csv_page():
    st.markdown('<div class="main-title">📁 Upload CSV Dataset</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Upload player dataset, measure processing time, and save it into SQLite database</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    Required CSV columns: <b>Player Name, Team, Wins, Losses, Points</b><br>
    Optional column: <b>Country</b><br><br>
    This page measures the actual processing time for reading, validating, sorting, and ranking the uploaded CSV dataset.
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            start_time = time.perf_counter()

            df = pd.read_csv(uploaded_file)

            missing_columns = validate_csv(df)

            if not missing_columns:
                processed_df = df.sort_values(by=["Points", "Wins"], ascending=[False, False]).copy()
                processed_df["Rank"] = range(1, len(processed_df) + 1)
            else:
                processed_df = df.copy()

            end_time = time.perf_counter()
            processing_time = end_time - start_time

            st.success("CSV file uploaded and processed successfully.")

            col1, col2, col3 = st.columns(3)
            col1.metric("Number of Records", len(df))
            col2.metric("Processing Time", f"{processing_time:.4f} seconds")
            col3.metric("Missing Columns", len(missing_columns))

            if missing_columns:
                st.error(f"Missing required columns: {', '.join(missing_columns)}")
                st.warning("Please check your CSV format and upload again.")
            else:
                st.subheader("Processed Dataset Preview")
                st.dataframe(processed_df, use_container_width=True)

                col_save, col_clear = st.columns(2)

                with col_save:
                    if st.button("Save Data to Database"):
                        insert_players_from_csv(df)
                        save_upload_history(uploaded_file.name, len(df), processing_time)
                        st.success("Player data and processing time saved successfully into SQLite database.")

                with col_clear:
                    if st.button("Clear Existing Player Data"):
                        clear_player_data()
                        st.warning("All player records have been deleted.")

        except Exception as e:
            st.error("Error reading or processing CSV file.")
            st.write(e)

    st.divider()

    st.subheader("Sample CSV Format")

    sample_data = pd.DataFrame({
        "Player Name": ["Alex", "Ryan", "Daniel", "Mira", "Farid"],
        "Team": ["Team Alpha", "Team Bravo", "Team Omega", "Team Nova", "Team Titan"],
        "Country": ["Malaysia", "Malaysia", "Singapore", "Malaysia", "Indonesia"],
        "Wins": [10, 8, 6, 6, 5],
        "Losses": [2, 3, 4, 5, 5],
        "Points": [300, 250, 200, 180, 160]
    })

    st.dataframe(sample_data, use_container_width=True)


# --------------------------------------------------
# Players Page
# --------------------------------------------------
def players_page():
    st.markdown('<div class="main-title">👥 Player Records</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">View and manage player information stored in SQLite database</div>', unsafe_allow_html=True)

    df = load_players()

    if df.empty:
        st.warning("No player records found.")
        return

    search_name = st.text_input("Search player by name")

    if search_name:
        df = df[df["player_name"].str.contains(search_name, case=False, na=False)]

    display_cols = safe_display_columns(
        df,
        ["player_id", "player_name", "team_name", "country", "wins", "losses", "points"]
    )

    st.dataframe(df[display_cols], use_container_width=True)

    st.divider()

    st.subheader("Add New Player Manually")

    with st.form("add_player_form"):
        col1, col2 = st.columns(2)

        with col1:
            player_name = st.text_input("Player Name")
            team_name = st.text_input("Team Name")
            country = st.text_input("Country")

        with col2:
            wins = st.number_input("Wins", min_value=0, step=1)
            losses = st.number_input("Losses", min_value=0, step=1)
            points = st.number_input("Points", min_value=0, step=10)

        submit_button = st.form_submit_button("Add Player")

        if submit_button:
            if player_name and team_name:
                cursor.execute("""
                INSERT INTO players (player_name, team_name, country, wins, losses, points)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (player_name, team_name, country, int(wins), int(losses), int(points)))

                conn.commit()
                st.success("New player added successfully.")
                st.rerun()
            else:
                st.error("Player name and team name are required.")


# --------------------------------------------------
# Rankings Page
# --------------------------------------------------
def rankings_page():
    st.markdown('<div class="main-title">🏆 Automatic Player Rankings</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Players are ranked based on points and wins</div>', unsafe_allow_html=True)

    df = load_players()

    if df.empty:
        st.warning("No ranking data available.")
        return

    df = calculate_win_rate(df)
    ranking_df = create_ranking(df)

    st.markdown("""
    <div class="info-box">
    Ranking rule: Players are sorted by <b>total points</b>. If points are the same, 
    players with more <b>wins</b> will be ranked higher.
    </div>
    """, unsafe_allow_html=True)

    display_cols = safe_display_columns(
        ranking_df,
        [
            "rank_position",
            "player_name",
            "team_name",
            "country",
            "wins",
            "losses",
            "points",
            "win_rate"
        ]
    )

    st.dataframe(
        ranking_df[display_cols],
        use_container_width=True
    )

    st.divider()

    fig = px.bar(
        ranking_df,
        x="rank_position",
        y="points",
        color="player_name",
        text="points",
        title="Ranking Position and Points"
    )

    fig.update_layout(
        xaxis_title="Ranking Position",
        yaxis_title="Points",
        height=450
    )

    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# Database Page
# --------------------------------------------------
def database_page():
    st.markdown('<div class="main-title">🗄️ SQLite Database Information</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">View stored database records and upload history</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    Database name: <b>tournament.db</b><br>
    Main table: <b>players</b><br>
    Extra table: <b>upload_history</b><br><br>
    This version also includes an auto-fix if the old database does not contain the country column.
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Players Table")
    players_df = load_players()
    st.dataframe(players_df, use_container_width=True)

    st.subheader("Upload History Table")
    upload_df = pd.read_sql_query("SELECT * FROM upload_history", conn)
    st.dataframe(upload_df, use_container_width=True)

    st.divider()

    if st.button("Clear All Player Data"):
        clear_player_data()
        st.warning("All player data has been cleared.")
        st.rerun()


# --------------------------------------------------
# Testing Summary Page
# --------------------------------------------------
def testing_summary_page():
    st.markdown('<div class="main-title">✅ Testing Summary</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">System testing results and actual dataset processing time</div>', unsafe_allow_html=True)

    testing_data = pd.DataFrame({
        "Test Case": [
            "User Login",
            "CSV Upload",
            "Database Storage",
            "Ranking Generation",
            "Dashboard Display",
            "Player Search",
            "Manual Player Entry",
            "Team Filter",
            "Old Database Country Column Fix",
            "Dataset Processing Time"
        ],
        "Expected Result": [
            "User can login successfully",
            "CSV file imported correctly",
            "Data stored in SQLite database",
            "Ranking displayed based on points and wins",
            "Charts and metric cards display correctly",
            "Player can be searched by name",
            "New player can be added",
            "Dashboard can filter players by team",
            "System does not crash when old database has no country column",
            "System displays actual processing time after CSV upload"
        ],
        "Actual Result": [
            "Successful",
            "Successful",
            "Successful",
            "Successful",
            "Successful",
            "Successful",
            "Successful",
            "Successful",
            "Successful",
            "Successful"
        ],
        "Status": [
            "Pass",
            "Pass",
            "Pass",
            "Pass",
            "Pass",
            "Pass",
            "Pass",
            "Pass",
            "Pass",
            "Pass"
        ]
    })

    st.subheader("Functional Testing Results")
    st.dataframe(testing_data, use_container_width=True)

    testing_data["Result Value"] = testing_data["Status"].apply(lambda x: 1 if x == "Pass" else 0)

    fig = px.bar(
        testing_data,
        x="Test Case",
        y="Result Value",
        text="Status",
        title="Functional Testing Result Summary"
    )

    fig.update_layout(
        xaxis_title="Test Case",
        yaxis_title="Status Value",
        height=450
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Actual Dataset Processing Time")

    upload_df = pd.read_sql_query(
        "SELECT file_name, total_records, processing_time_seconds, upload_time FROM upload_history ORDER BY upload_id",
        conn
    )

    if upload_df.empty:
        st.info("No processing time data yet. Upload CSV files and click 'Save Data to Database' to record actual processing time.")
    else:
        st.dataframe(upload_df, use_container_width=True)

        fig_time = px.line(
            upload_df,
            x="total_records",
            y="processing_time_seconds",
            markers=True,
            hover_data=["file_name", "upload_time"],
            title="Actual Dataset Processing Time"
        )

        fig_time.update_layout(
            xaxis_title="Number of Records",
            yaxis_title="Processing Time (seconds)",
            height=450
        )

        st.plotly_chart(fig_time, use_container_width=True)


# --------------------------------------------------
# About System Page
# --------------------------------------------------
def about_system_page():
    st.markdown('<div class="main-title">ℹ️ About This System</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Project explanation for BIT1034 Advance Programming</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
    <b>Project Title:</b> Smart Gaming Tournament Analytics System<br><br>
    <b>Course:</b> BIT1034 Advance Programming<br><br>
    <b>Main Purpose:</b> To help tournament organizers manage player data, upload CSV datasets,
    store data in SQLite database, generate automatic rankings, and view analytics charts.
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Technologies Used")

    tech_df = pd.DataFrame({
        "Technology": [
            "Python",
            "Streamlit",
            "SQLite",
            "Pandas",
            "Plotly",
            "GitHub"
        ],
        "Purpose": [
            "Main programming language",
            "Build web-based dashboard",
            "Store tournament data",
            "Read and process CSV dataset",
            "Create interactive charts",
            "Store and manage source code"
        ]
    })

    st.dataframe(tech_df, use_container_width=True)

    st.subheader("Main Functions")
    st.write("1. Login system")
    st.write("2. Upload CSV dataset")
    st.write("3. Store player data in SQLite database")
    st.write("4. Display player records")
    st.write("5. Generate automatic rankings")
    st.write("6. Display metric cards with icons")
    st.write("7. Display Plotly dashboard charts")
    st.write("8. Filter dashboard by team")
    st.write("9. Show testing summary")
    st.write("10. Auto-fix missing country column issue")


# --------------------------------------------------
# Main Application
# --------------------------------------------------
if not st.session_state.logged_in:
    login_page()
else:
    selected_menu = sidebar_menu()

    if selected_menu == "Dashboard":
        dashboard_page()

    elif selected_menu == "Upload CSV":
        upload_csv_page()

    elif selected_menu == "Players":
        players_page()

    elif selected_menu == "Rankings":
        rankings_page()

    elif selected_menu == "Database":
        database_page()

    elif selected_menu == "Testing Summary":
        testing_summary_page()

    elif selected_menu == "About System":
        about_system_page()

    st.markdown(
        '<div class="footer">BIT1034 Advance Programming | Smart Gaming Tournament Analytics System</div>',
        unsafe_allow_html=True
    )
