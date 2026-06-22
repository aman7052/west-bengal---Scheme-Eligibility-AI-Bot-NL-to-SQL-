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
# 2. LLM SETUP (Sirf Llama 3 Chahiye Details Yaad Rakhne Ke Liye)
# ==========================================
general_llm = OllamaLLM(model="llama3", temperature=0)

# ==========================================
# 3. PROMPT: PROFILE EXTRACTOR (Llama 3)
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
- education (STRING like '8', '12' or "N/A". Strictly extract ONLY the digits if the user says '12th' or '8th standard')

Chat History:
{history}

New User Message: {input}

Respond ONLY with a valid JSON object. Do not add any conversational text or markdown blocks.
""")

extractor_chain = extractor_prompt | general_llm | StrOutputParser()

# ==========================================
# 4. PYTHON DYNAMIC QUERY BUILDER (100% Error-Free)
# ==========================================
def build_sql_query(profile):
    query = "SELECT scheme_name, scheme_code FROM wb_schemes WHERE 1=1"
    
    # Agar data N/A nahi hai, tabhi aur sirf tabhi SQL condition judegi!
    if profile.get("age") and str(profile["age"]).upper() != "N/A":
        query += f" AND (min_age <= {profile['age']} AND max_age >= {profile['age']})"
        
    if profile.get("family_income") and str(profile["family_income"]).upper() != "N/A":
        query += f" AND (max_income >= {profile['family_income']})"
        
    if profile.get("gender") and str(profile["gender"]).upper() != "N/A":
        query += f" AND (gender ILIKE '%{profile['gender']}%' OR gender ILIKE '%Any%')"
        
    if profile.get("caste") and str(profile["caste"]).upper() != "N/A":
        query += f" AND (caste ILIKE '%{profile['caste']}%' OR caste ILIKE '%Any%')"
        
    if profile.get("marital_status") and str(profile["marital_status"]).upper() != "N/A":
        query += f" AND (marital_status ILIKE '%{profile['marital_status']}%' OR marital_status ILIKE '%Any%')"
        
    if profile.get("occupation") and str(profile["occupation"]).upper() != "N/A":
        query += f" AND (occupation ILIKE '%{profile['occupation']}%' OR occupation ILIKE '%Any%')"
        
    if profile.get("residence_area") and str(profile["residence_area"]).upper() != "N/A":
        query += f" AND (residence_area ILIKE '%{profile['residence_area']}%' OR residence_area ILIKE '%Any%')"
        
    if profile.get("school_type") and str(profile["school_type"]).upper() != "N/A":
        query += f" AND (school_type ILIKE '%{profile['school_type']}%' OR school_type ILIKE '%Any%')"
        
    if profile.get("education") and str(profile["education"]).upper() != "N/A":
        query += f" AND (education ILIKE '%{profile['education']}%' OR education ILIKE '%Any%')"
        
    return query

# ==========================================
# 5. STATE VARIABLES (Memory Management)
# ==========================================
user_profile = {
    "age": "N/A", "family_income": "N/A", "gender": "N/A", "caste": "N/A",
    "marital_status": "N/A", "occupation": "N/A", "residence_area": "N/A",
    "school_type": "N/A", "education": "N/A"
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

        # Reset Memory if New User Detected
        if "mera naam" in user_input.lower() and "ram" not in user_input.lower() and "aman" not in user_input.lower():
            print("[System]: New user detected. Resetting profile memory...")
            user_profile = {k: "N/A" for k in user_profile}
            history_str = ""
            continue

        try:
            # Step A: JSON Extract karein Llama 3 se
            raw_json = extractor_chain.invoke({"history": history_str, "input": user_input})
            cleaned_json = raw_json.strip().replace("```json", "").replace("```", "").strip()
            
            try:
                new_data = json.loads(cleaned_json)
                for key in user_profile:
                    if key in new_data and new_data[key] is not None and str(new_data[key]).lower() != "null":
                        user_profile[key] = new_data[key]
            except Exception:
                pass  

            print(f"--- DEBUG: Current Cumulative Profile: {user_profile} ---")

            # Step B: Python se Clean SQL generate karein (NO SQLCoder required!)
            generated_sql = build_sql_query(user_profile)
            print(f"--- DEBUG: Generated SQL via Python: {generated_sql} ---")

            # Step C: Database Query Execute karein
            response = db.run(generated_sql)
            
            if response and "Error" not in str(response) and response != "[]":
                print(f"\n[Bot]: Based on your profile, you are eligible for:\n{response}")
            else:
                print("\n[Bot]: No eligible schemes found for this current profile criteria.")
            
            history_str += f"\nUser: {user_input}\nBot: {str(response)}"

        except Exception as e:
            print(f"Bot: Sorry, I faced an error processing that: {e}")

if __name__ == "__main__":
    start_langchain_bot()