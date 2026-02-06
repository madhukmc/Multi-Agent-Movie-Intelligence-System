import os
import requests
import streamlit as st
from fpdf import FPDF
from dotenv import load_dotenv

from phi.agent import Agent
from phi.model.google import Gemini

# =====================================================
# LOAD KEYS
# =====================================================
load_dotenv()

OMDB_API_KEY = "824843d5"
TMDB_API_KEY = "43cf5554948ee0407cdfe5ed60baa0e1"
GEMINI_API_KEY = "AIzaSyBRbEW_RAnpZQIwPIPfw_dxX0jAjkJqwqE"

os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

# =====================================================
# AGENTS
# =====================================================
analysis_agent = Agent(
    name="Movie Analysis Agent",
    model=Gemini(id="gemini-2.5-flash"),
    instructions="Summarize the movie strictly using provided data.",
    markdown=True,
)

qa_agent = Agent(
    name="Movie QnA Agent",
    model=Gemini(id="gemini-2.5-flash"),
    instructions="Answer questions only using the movie data.",
    markdown=True,
)

test_agent = Agent(
    name="Movie Test Agent",
    model=Gemini(id="gemini-2.5-flash"),
    instructions="""
    Validate the AI answer.

    PASS → answer matches movie data
    FAIL → hallucination or unrelated

    Output format:
    TEST RESULT: PASS or FAIL
    REASON:
    """,
    markdown=False,
)

document_agent = Agent(
    name="Movie Document Agent",
    model=Gemini(id="gemini-2.5-flash"),
    instructions="Format validated content into a professional report.",
    markdown=True,
)

# =====================================================
# UI
# =====================================================
st.set_page_config(page_title="🎬 Multi-Agent Movie Intelligence")
st.title("🎬 Multi-Agent Movie Intelligence System")

movie_title = st.text_input("🎥 Enter Movie Title")
user_question = st.text_area("❓ Ask a question about the movie (optional)")

# =====================================================
# MAIN EXECUTION
# =====================================================
if st.button("🎯 Analyze Movie"):

    if not movie_title:
        st.warning("Please enter a movie title.")
        st.stop()

    # ---------------- FETCH MOVIE DATA ----------------
    with st.spinner("🔍 Fetching movie data..."):

        search = requests.get(
            "https://www.omdbapi.com/",
            params={"s": movie_title, "apikey": OMDB_API_KEY},
            timeout=10
        ).json()

        if search.get("Response") == "False":
            st.error("Movie not found. Try exact title like 'Avatar 2009'.")
            st.stop()

        imdb_id = search["Search"][0]["imdbID"]

        omdb = requests.get(
            "https://www.omdbapi.com/",
            params={"i": imdb_id, "plot": "full", "apikey": OMDB_API_KEY},
            timeout=10
        ).json()

        tmdb_search = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params={"query": movie_title, "api_key": TMDB_API_KEY},
            timeout=10
        ).json()

        budget = "N/A"
        revenue = "N/A"

        if tmdb_search.get("results"):
            tmdb_id = tmdb_search["results"][0]["id"]
            tmdb = requests.get(
                f"https://api.themoviedb.org/3/movie/{tmdb_id}",
                params={"api_key": TMDB_API_KEY},
                timeout=10
            ).json()
            budget = tmdb.get("budget", "N/A")
            revenue = tmdb.get("revenue", "N/A")

        movie_context = f"""
Title: {omdb.get('Title')}
Year: {omdb.get('Year')}
Genre: {omdb.get('Genre')}
Director: {omdb.get('Director')}
Actors: {omdb.get('Actors')}
Runtime: {omdb.get('Runtime')}
IMDb Rating: {omdb.get('imdbRating')}
Plot: {omdb.get('Plot')}
Budget: {budget}
Revenue: {revenue}
"""

    # ---------------- ANALYSIS ----------------
    summary = analysis_agent.run(movie_context).content
    st.subheader("🎞️ Movie Summary")
    st.write(summary)

    final_report = f"MOVIE REPORT\n\n{summary}\n\n"

    # ---------------- USER QUESTION ----------------
    if user_question:

        answer = qa_agent.run(
            f"Movie Data:\n{movie_context}\n\nQuestion:\n{user_question}"
        ).content

        test_output = test_agent.run(
            f"Movie Data:\n{movie_context}\n\nQuestion:\n{user_question}\n\nAnswer:\n{answer}"
        ).content

        st.subheader("🧪 Test Result")
        st.write(test_output)

        if "PASS" in str(test_output):
            final_report += f"""
QUESTION:
{user_question}

ANSWER:
{answer}

VALIDATION:
{test_output}
"""
        else:
            final_report += f"""
QUESTION:
{user_question}

ANSWER REJECTED
{test_output}
"""

    # ---------------- DOCUMENT AGENT (ALWAYS RUNS) ----------------
    document_response = document_agent.run(final_report)
    document_text = str(document_response.content)

    # ---------------- PDF GENERATION ----------------
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    safe_text = document_text.encode("latin-1", "ignore").decode("latin-1")
    pdf.multi_cell(0, 8, safe_text)

    file_name = movie_title.replace(" ", "_") + "_Movie_Report.pdf"
    pdf.output(file_name)

    with open(file_name, "rb") as f:
        st.download_button(
            "📄 Download Movie Report (PDF)",
            f,
            file_name=file_name,
            mime="application/pdf",
        )

st.markdown("---")
st.caption("Streamlit • PhiData • Multi-Agent AI • Gemini • OMDb • TMDb")
