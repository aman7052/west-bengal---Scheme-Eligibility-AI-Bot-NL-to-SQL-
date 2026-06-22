import streamlit as st
from langchain_community.utilities import SQLDatabase
from langchain_ollama import OllamaLLM
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re

# Streamlit Page Config - Setting up premium dark aesthetic
st.set_page_config(
    page_title="west bengal  - Scheme Eligibility AI Bot",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling for Dark Mode Aesthetic & Interactive Elements
st.markdown("""
<style>
    .reportview-container {
        background: #111216;
    }
    .stChatFloatingInputContainer {
        background-color: transparent !important;
    }
    .sidebar-profile-box {
        background-color: #1e2030;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3b4261;
        margin-bottom: 10px;
    }
    .profile-pill {
        display: inline-block;
        background: #2e3047;
        color: #ff9e64;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.85em;
        margin: 3px;
        border: 1px solid #ff9e6455;
    }
    .profile-pill-active {
        background: #24283b;
        color: #7aa2f7;
        border: 1px solid #7aa2f788;
    }
</style>
""", unsafe_allow_html=True)

# 1. DATABASE CONNECTION (Cached to run only once)
@st.cache_resource
def get_db_connection():
    postgres_uri = "postgresql+psycopg2://postgres:705219@localhost:5432/demodb"
    db = SQLDatabase.from_uri(postgres_uri, include_tables=['wb_schemes'])
    return db

db = get_db_connection()
execute_query = QuerySQLDataBaseTool(db=db)


# 2. DUAL LLM SETUP (Cached to prevent reload delays)
@st.cache_resource
def get_llm_models():
    general_llm = OllamaLLM(model="llama3", temperature=0)
    sql_llm = OllamaLLM(model="llama3", temperature=0)
    return general_llm, sql_llm

general_llm, sql_llm = get_llm_models()


# 3. PROMPT 1: PROFILE EXTRACTOR (Llama 3)
extractor_prompt = ChatPromptTemplate.from_template("""
You are a strict profile extractor assistant. Your job is to look at the Chat History and the New User Message, and extract the current cumulative user profile fields in JSON format.
If a detail was mentioned in the history, keep it. If it is updated in the new message, change it. 

### CRITICAL EXTRACTION RULES:
1. If a field is missing from both history and new message, strictly set its value to the string "N/A". Do NOT use null or None.
2. If the user mentions education like '12th' or '12th standard', strictly extract ONLY the number '12'. For '8th', extract '8'.
3. NEVER put numbers like '12', '12th', '8' inside the 'school_type' field. 'school_type' can ONLY be 'Government', 'Private' or "N/A".
4. STRICT NO-ASSUMPTION RULE: Do NOT make any assumptions or logical guesses about 'education' or any other field based on age or occupation. For example, if a user says they are a 25-year-old "student" but does NOT explicitly state their class or education level in the text, you MUST set 'education' to "N/A". Only extract what is explicitly written!.
5. STRICT GENDER RULE: NEVER guess or assume the 'gender' field based on the user's name (e.g., if the name is 'Ragini' or 'Ritika', do NOT set gender to 'Female' unless the user explicitly mentions 'female', 'girl', or 'woman' in the text). Keep the previous gender or set it to "N/A" if never mentioned.
6. "If the user explicitly asks to 'remove', 'clear' a specific field/detail (e.g., 'remove education' or 'clear income'), you MUST strictly set that field's value back to 'N/A'."
7. Once a field is explicitly 'removed' or 'cleared' (set to 'N/A') in a previous turn, it must REMAIN 'N/A' in all future turns. Do NOT bring it back or carry it forward from older history unless the user explicitly tells you to add/update it again.                                     

Fields to extract (strictly match these keys):
- age (INTEGER or "N/A")
- family_income (INTEGER or "N/A")
- gender (STRING like 'Male', 'Female' or "N/A")
- caste (STRING like 'SC', 'ST', 'OBC', 'General' or "N/A")
- marital_status (STRING like 'Single', 'Married', 'Unmarried', 'Widow' or "N/A")
- occupation (STRING like 'Student', 'Farmer', 'women', 'handicrafting', 'priest', 'fisherman', 'weaver', 'artistic background', or "N/A")
- residence_area (STRING like 'west bengal', or "N/A")
- school_type (STRING like 'Government', 'Private' or "N/A")
- education (STRING like '8', '9', '10', '11', '12' or "N/A")

Chat History:
{history}

### Examples of how you must behave:

Example 1 Input Message: "I am Ram, age 20, male and 12 class student"
Example 1 Expected Output JSON:
{{"age": 20, "family_income": "N/A", "gender": "Male", "caste": "N/A", "marital_status": "N/A", "occupation": "Student", "residence_area": "N/A", "school_type": "N/A", "education": "12"}}

Example 2 (Profile Update):
If History has: "I am Ram, age 20, male and 12 class student"
And New Input Message is: "update my name from ram to ratna and i am female"
Example 2 Expected Output JSON:
{{"age": 20, "family_income": "N/A", "gender": "Female", "caste": "N/A", "marital_status": "N/A", "occupation": "Student", "residence_area": "N/A", "school_type": "N/A", "education": "12"}}

Example 3 (Multiple Profile Updates):
If History has: "I am Ram, age 20, male and 12 class student"
And New Input Message is: "change my name to ratna, age from 20 to 25 and i am female"
Example 3 Expected Output JSON:
{{"age": 25, "family_income": "N/A", "gender": "Female", "caste": "N/A", "marital_status": "N/A", "occupation": "Student", "residence_area": "N/A", "school_type": "N/A", "education": "12"}}

Example 3 (Multiple Profile Updates):
If History has: "I am Ram, age 20, male and 12 class student"
And New Input Message is: "change my name to ratna and age from 20 to 25"
Example 3 Expected Output JSON:
{{"age": 25, "family_income": "N/A", "gender": "male", "caste": "N/A", "marital_status": "N/A", "occupation": "Student", "residence_area": "N/A", "school_type": "N/A", "education": "12"}}
                                                                                                        
Example 4 (Removing/Clearing a Detail):
If History has: "I am Ram, age 20, male and 12 class student"
And New Input Message is: "update my name from ram to ragini and remove education 12"
Example 4 Expected Output JSON:
{{"age": 20, "family_income": "N/A", "gender": "Male", "caste": "N/A", "marital_status": "N/A", "occupation": "Student", "residence_area": "N/A", "school_type": "N/A", "education": "N/A"}}
                                                                                                        
New User Message: {input}

Respond ONLY with a valid JSON object. Do not add any conversational text or markdown blocks.
""")

extractor_chain = extractor_prompt | general_llm | StrOutputParser()


# 4. PROMPT 2: PURE LLM SQL GENERATOR WITH EXAMPLES (Llama 3 optimized for exact matching)
sql_prompt = ChatPromptTemplate.from_template("""
### Task
Generate a PostgreSQL query for 'wb_schemes' table based on the extracted user profile data.

### Database Schema
Table name: wb_schemes
Columns:
- id (INTEGER)/'
- scheme_name (VARCHAR)
- scheme_code (VARCHAR)
- min_age (INTEGER)
- max_age (INTEGER)
- max_income (INTEGER)
- gender (VARCHAR)
- caste (VARCHAR)
- marital_status (VARCHAR)
- occupation (VARCHAR)
- residence_area (VARCHAR)
- school_type (VARCHAR)
- education (VARCHAR)

### Strict Rules for SQL Generation:
1. Base query MUST always be: SELECT wb_schemes.scheme_name, wb_schemes.scheme_code FROM wb_schemes WHERE 1=1
2. CRITICAL RULE: If any profile field is "N/A", you MUST completely IGNORE it. Do NOT write any condition or ILIKE filter for that field. The word "N/A" must NEVER appear anywhere in your SQL output.
3. MANDATORY RULE: If any text field (gender, caste, occupation, marital_status, residence_area, school_type, education) is NOT "N/A", you MUST absolutely include it in the query. Do NOT skip any valid field!
4. If age is not "N/A", add: AND (min_age <= {extracted_age} AND max_age >= {extracted_age})
5. If family_income is not "N/A", add: AND (max_income >= {extracted_income})
6. For standard text fields (caste, occupation, marital_status, residence_area, school_type), generate exactly like this: AND (field_name ILIKE '%<value_from_profile>%' OR field_name ILIKE '%Any%')
7. STRICT EXACT MATCH RULE FOR GENDER: Do NOT use ILIKE '%value%' for gender to avoid substring issues (e.g., 'Female' matching 'Male'). Use exact case-insensitive match like: AND (LOWER(gender) = LOWER('{extracted_gender}') OR LOWER(gender) = 'any')
8. STRICT EXACT MATCH RULE FOR EDUCATION: If education is NOT "N/A", you MUST absolutely include it using exact case-insensitive match like: AND (LOWER(education) = LOWER('{extracted_education}') OR LOWER(education) = 'any')

### Examples of how you must behave:

Example 1 Input:
- age: 25, family_income: N/A, gender: Female, caste: N/A, marital_status: N/A, occupation: N/A, residence_area: N/A, school_type: N/A, education: N/A
Example 1 Expected SQL:
SELECT wb_schemes.scheme_name, wb_schemes.scheme_code FROM wb_schemes WHERE 1=1 AND (min_age <= 25 AND max_age >= 25) AND (LOWER(gender) = LOWER('Female') OR LOWER(gender) = 'any');

Example 2 Input:
- age: N/A, family_income: 150000, gender: N/A, caste: N/A, marital_status: N/A, occupation: Farmer, residence_area: N/A, school_type: N/A, education: N/A
Example 2 Expected SQL:
SELECT wb_schemes.scheme_name, wb_schemes.scheme_code FROM wb_schemes WHERE 1=1 AND (max_income >= 150000) AND (LOWER(occupation) = LOWER('Farmer') OR LOWER(occupation) = 'any');

Example 3 Input (With Education and Gender):
- age: 17, family_income: N/A, gender: Female, caste: N/A, marital_status: N/A, occupation: Student, residence_area: N/A, school_type: N/A, education: 12
Example 3 Expected SQL:
SELECT wb_schemes.scheme_name, wb_schemes.scheme_code FROM wb_schemes WHERE 1=1 AND (min_age <= 17 AND max_age >= 17) AND (LOWER(gender) = LOWER('Female') OR LOWER(gender) = 'any') AND (LOWER(occupation) = LOWER('Student') OR LOWER(occupation) = 'any') AND (LOWER(education) = LOWER('12') OR LOWER(education) = 'any');

### Now process this Current User Profile:
- age: {extracted_age}
- family_income: {extracted_income}
- gender: {extracted_gender}
- caste: {extracted_caste}
- marital_status: {extracted_marital_status}
- occupation: {extracted_occupation}
- residence_area: {extracted_residence_area}
- school_type: {extracted_school_type}
- education: {extracted_education}

Output ONLY the raw SQL query. Do not provide any explanation, markdown formatting, or introductory text.

Response:
SELECT 
""")

sql_chain = sql_prompt | sql_llm | StrOutputParser()


# 5. INITIALIZE SESSION STATE VARIABLES (Streamlit Memory)
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "age": "N/A", "family_income": "N/A", "gender": "N/A", "caste": "N/A",
        "marital_status": "N/A", "occupation": "N/A", "residence_area": "N/A",
        "school_type": "N/A", "education": "N/A"
    }

if "history_str" not in st.session_state:
    st.session_state.history_str = ""

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


# --- STREAMLIT SIDEBAR: USER ACTIVE PROFILE MONITOR ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🛡️ SQL Query Generator AI Engine</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #737aa2;'>West Bengal Schemes Eligibility Evaluator</p>", unsafe_allow_html=True)
    st.write("---")
    
    st.markdown("### 📊 Active Profile State:")
    
    # Render fields in sidebar beautifully with conditional badges
    for key, val in st.session_state.user_profile.items():
        is_na = str(val) == "N/A"
        class_pill = "profile-pill" if is_na else "profile-pill profile-pill-active"
        icon_field = "⚪" if is_na else "🔵"
        st.markdown(
            f"**{key.replace('_', ' ').capitalize()}:** <span class='{class_pill}'>{val}</span>", 
            unsafe_allow_html=True
        )
    
    st.write("---")
    
    # Reset Application Button
    if st.button("🧹 Reset Memory / Clear Chat", use_container_width=True):
        st.session_state.user_profile = {k: "N/A" for k in st.session_state.user_profile}
        st.session_state.history_str = ""
        st.session_state.chat_messages = []
        st.success("App state flushed successfully!")
        st.rerun()


# --- MAIN HEADER SECTION ---
st.markdown("<h1 style='text-align: center; margin-bottom: 5px;'>🛡️ Chat with west bengal scheme bot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #565f89; margin-bottom: 25px;'>Enterprise Relational Scheme Discovery Engine | Developed by NIC Kolkata</p>", unsafe_allow_html=True)


# --- CHAT CONTAINER RENDERING ---
# Render all previous chat history logs securely
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg:
            with st.expander("🛠️ View Compiled SQL Query & Analytics"):
                st.code(msg["sql"], language="sql")


# --- INPUT BOX CONTROLLER ---
if user_input := st.chat_input(" Tell me your query"):
    
    # 1. Display User Message in UI and Append to memory logs
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.chat_messages.append({"role": "user", "content": user_input})

    # 2. Check for manual resets
    if user_input.lower().strip() in ['reset', 'clear', 'new']:
        st.session_state.user_profile = {k: "N/A" for k in st.session_state.user_profile}
        st.session_state.history_str = ""
        st.session_state.chat_messages = []
        st.success("Memory reset done. App refreshed!")
        st.rerun()

    # 3. AI Execution Pipeline
    with st.chat_message("assistant"):
        # Setup modern stream spinner
        with st.spinner("AI is evaluating demographics & writing secure SQL..."):
            try:
                # Step A: Llama 3 JSON profile extraction
                raw_json = extractor_chain.invoke({
                    "history": st.session_state.history_str, 
                    "input": user_input
                })
                cleaned_json = raw_json.strip().replace("```json", "").replace("```", "").strip()
                
                try:
                    new_data = json.loads(cleaned_json)
                    # Backup previous gender to protect from substring assumptions
                    previous_gender = st.session_state.user_profile.get("gender", "N/A")
                    
                    # Update profile
                    for key in st.session_state.user_profile:
                        if key in new_data and new_data[key] is not None and str(new_data[key]).lower() != "null":
                            st.session_state.user_profile[key] = new_data[key]
                    
                    # Exact Match Override verification for Gender assumptions
                    gender_words = ['male', 'female', 'boy', 'girl', 'woman', 'man', 'lady', 'gentleman']
                    has_explicit_gender = any(word in user_input.lower() for word in gender_words)
                    
                    if not has_explicit_gender and previous_gender != "N/A":
                        st.session_state.user_profile["gender"] = previous_gender
                        
                except Exception as json_err:
                    pass

                # Step B: LLM SQL Generation
                generated_sql = sql_chain.invoke({
                    "extracted_age": st.session_state.user_profile["age"],
                    "extracted_income": st.session_state.user_profile["family_income"],
                    "extracted_gender": st.session_state.user_profile["gender"],
                    "extracted_caste": st.session_state.user_profile["caste"],
                    "extracted_marital_status": st.session_state.user_profile["marital_status"],
                    "extracted_occupation": st.session_state.user_profile["occupation"],
                    "extracted_residence_area": st.session_state.user_profile["residence_area"],
                    "extracted_school_type": st.session_state.user_profile["school_type"],
                    "extracted_education": st.session_state.user_profile["education"]
                }).strip()

                # Cleanup SQL structure
                generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()
                if not generated_sql.upper().startswith("SELECT"):
                    generated_sql = "SELECT " + generated_sql

                # Python exact replace gate for Gender substring safety
                if "gender ILIKE '%Male%'" in generated_sql:
                    generated_sql = generated_sql.replace("gender ILIKE '%Male%'", "LOWER(gender) = 'male'")
                elif "gender ILIKE '%Female%'" in generated_sql:
                    generated_sql = generated_sql.replace("gender ILIKE '%Female%'", "LOWER(gender) = 'female'")

                # Step C: PostgreSQL Query Transaction via psycopg2
                response = db.run(generated_sql)
                
                # Format response for beautiful UI presentation
                if response and "Error" not in str(response) and response != "[]":
                    # Simple regex clean to format DB output tuples neatly
                    cleaned_response = response.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
                    bot_text = f"Based on your profile, you are eligible for:\n\n**{cleaned_response}**"
                else:
                    bot_text = "No eligible schemes found for this current profile criteria in our database."

                # Update stream memory state
                st.session_state.history_str += f"\nUser: {user_input}\nBot: {str(response)}"

                # Print response and reveal compiled SQL query cleanly
                st.markdown(bot_text)
                with st.expander("🛠️ View Compiled SQL Query & Analytics"):
                    st.code(generated_sql, language="sql")

                # Store assistant session response
                st.session_state.chat_messages.append({
                    "role": "assistant", 
                    "content": bot_text,
                    "sql": generated_sql
                })

            except Exception as e:
                error_msg = f"Sorry, I faced an error processing the database transaction: {str(e)}"
                st.error(error_msg)

    # Re-run after processing input to sync sidebar state seamlessly
    st.rerun()