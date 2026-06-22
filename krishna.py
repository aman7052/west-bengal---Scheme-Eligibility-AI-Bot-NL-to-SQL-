from langchain_community.utilities import SQLDatabase
from langchain_ollama import OllamaLLM
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json

# ==========================================
# 1. DATABASE CONNECTION (PostgreSQL)
# ==========================================
postgres_uri = "postgresql+psycopg2://postgres:705219@localhost:5432/demodb"
db = SQLDatabase.from_uri(postgres_uri, include_tables=['wb_schemes'])
execute_query = QuerySQLDataBaseTool(db=db)

# ==========================================
# 2. DUAL LLM SETUP (OllamaLLM - No Warning)
# ==========================================
# Llama3: Hindi/English samajhne aur context yaad rakhne ke liye
general_llm = OllamaLLM(model="llama3", temperature=0)
# SQLCoder: Sirf perfect SQL query banane ke liye
sql_llm = OllamaLLM(model="sqlcoder", temperature=0)

# ==========================================
# 3. PROMPT 1: CONTEXT & PROFILE EXTRACTOR (Llama 3)
# ==========================================
extractor_prompt = ChatPromptTemplate.from_template("""
You are a profile extractor assistant. Your job is to look at the Chat History and the New User Message, and extract the current cumulative user profile fields in JSON format.
If a detail was mentioned in the history, keep it. If it is updated in the new message, change it. 

CRITICAL RULE: If a field is missing from both history and new message, strictly set its value to the string "N/A". Do NOT use null or None.

Fields to extract (strictly match these keys):
- age (INTEGER or "N/A")
- family_income (INTEGER or "N/A")
- gender (STRING like 'Male', 'Female' or "N/A")
- caste (STRING like 'SC', 'ST', 'OBC', 'General' or "N/A")
- marital_status (STRING like 'Single', 'Married' or "N/A")
- occupation (STRING like 'Student', 'Farmer' or "N/A")
- residence_area (STRING like 'Urban', 'Rural' or "N/A")
- school_type (STRING like 'Government', 'Private' or "N/A")
- education (STRING like '10th', '12th' or "N/A")

Chat History:
{history}

New User Message: {input}

Respond ONLY with a valid JSON object. Do not add any conversational text or markdown blocks.
""")

extractor_chain = extractor_prompt | general_llm | StrOutputParser()

# ==========================================
# 4. PROMPT 2: DYNAMIC SQL GENERATOR (SQLCoder)
# ==========================================
sql_prompt = ChatPromptTemplate.from_template("""
### Task
Generate a PostgreSQL query for 'wb_schemes' table based on the exact user profile data provided.

### Database Schema
Table name: wb_schemes
Columns:
- id (INTEGER)
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

### Extracted Profile Data:
Age: {extracted_age}
Income: {extracted_income}
Gender: {extracted_gender}
Caste: {extracted_caste}
Marital Status: {extracted_marital_status}
Occupation: {extracted_occupation}
Residence Area: {extracted_residence_area}
School Type: {extracted_school_type}
Education: {extracted_education}

### Strict Rules for SQL Generation:
1. Base query MUST always be exactly: SELECT scheme_name, scheme_code FROM wb_schemes WHERE 1=1
2. If Age is NOT "N/A", ADD: AND (min_age <= {extracted_age} AND max_age >= {extracted_age})
3. If Income is NOT "N/A", ADD: AND (max_income >= {extracted_income})
4. If Gender is NOT "N/A", ADD: AND (gender ILIKE '%{extracted_gender}%' OR gender = 'All')
5. If Caste is NOT "N/A", ADD: AND (caste ILIKE '%{extracted_caste}%' OR caste = 'All')
6. If Marital Status is NOT "N/A", ADD: AND (marital_status ILIKE '%{extracted_marital_status}%' OR marital_status = 'All')
7. If Occupation is NOT "N/A", ADD: AND (occupation ILIKE '%{extracted_occupation}%' OR occupation = 'All')
8. If Residence Area is NOT "N/A", ADD: AND (residence_area ILIKE '%{extracted_residence_area}%' OR residence_area = 'All')
9. If School Type is NOT "N/A", ADD: AND (school_type ILIKE '%{extracted_school_type}%' OR school_type = 'All')
10. If Education is NOT "N/A", ADD: AND (education ILIKE '%{extracted_education}%' OR education = 'All')
11. Do NOT invent columns or conditions for fields that are "N/A".
12. Output ONLY the raw SQL query. No explanation, no markdown blocks.

Response:
SELECT 
""")

sql_chain = sql_prompt | sql_llm | StrOutputParser()

# ==========================================
# 5. STATE VARIABLES (Memory Management)
# ==========================================
user_profile = {
    "age": "N/A", 
    "family_income": "N/A", 
    "gender": "N/A",
    "caste": "N/A",
    "marital_status": "N/A",
    "occupation": "N/A", 
    "residence_area": "N/A",
    "school_type": "N/A",
    "education": "N/A"
}
history_str = ""

# ==========================================
# 6. BOT CORE LOOP
# ==========================================
def start_langchain_bot():
    global history_str, user_profile
    print("Bot : System ready. How can I help you?")
    
    while True:
        user_input = input("\nUser: ").strip()
        if not user_input: continue

        # Identity Reset Check
        if "mera naam" in user_input.lower() and "aman" not in user_input.lower():
            print("[System]: New user detected. Resetting profile memory...")
            user_profile = {k: "N/A" for k in user_profile}
            history_str = ""
            continue

        try:
            # Step A: Extract details and update profile state
            raw_json = extractor_chain.invoke({"history": history_str, "input": user_input})
            cleaned_json = raw_json.strip().replace("```json", "").replace("```", "").strip()
            
            try:
                new_data = json.loads(cleaned_json)
                for key in user_profile:
                    if key in new_data and new_data[key] is not None and str(new_data[key]).lower() != "null":
                        user_profile[key] = new_data[key]
            except Exception:
                pass  # Fallback to current profile if JSON parsing fails

            print(f"--- DEBUG: Current Cumulative Profile: {user_profile} ---")

            # Step B: Generate clean query using SQLCoder based on profile data
            generated_sql = sql_chain.invoke({
                "extracted_age": user_profile["age"],
                "extracted_income": user_profile["family_income"],
                "extracted_gender": user_profile["gender"],
                "extracted_caste": user_profile["caste"],
                "extracted_marital_status": user_profile["marital_status"],
                "extracted_occupation": user_profile["occupation"],
                "extracted_residence_area": user_profile["residence_area"],
                "extracted_school_type": user_profile["school_type"],
                "extracted_education": user_profile["education"]
            }).strip()

            # Clean and enforce syntax safety
            generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()
            if not generated_sql.upper().startswith("SELECT"):
                generated_sql = "SELECT " + generated_sql
            
            print(f"--- DEBUG: LLM generated this SQL: {generated_sql} ---")

            # Step C: Execute on PostgreSQL and print response
            response = execute_query.invoke(generated_sql)
            
            if response and "Error" not in str(response):
                print(f"\n[Bot]: Based on your profile, you are eligible for:\n{response}")
            else:
                print("\n[Bot]: No eligible schemes found for this current profile criteria.")
            
            # Append interaction to string history
            history_str += f"\nUser: {user_input}\nBot: {str(response)}"

        except Exception as e:
            print(f"Bot: Sorry, I faced an error processing that: {e}")

if __name__ == "__main__":
    start_langchain_bot()