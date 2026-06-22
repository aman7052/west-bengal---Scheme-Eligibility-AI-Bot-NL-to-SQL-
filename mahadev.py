from langchain_community.utilities import SQLDatabase
from langchain_ollama import OllamaLLM
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json

# 1. Database Connection (PostgreSQL)
postgres_uri = "postgresql+psycopg2://postgres:705219@localhost:5432/demodb"
db = SQLDatabase.from_uri(postgres_uri, include_tables=['wb_schemes'])
execute_query = QuerySQLDataBaseTool(db=db)

# 2. Dual LLM Setup (Dono Models ka sahi use)
# Llama3: Hindi samajhne aur details yaad rakhne ke liye badiya hai
general_llm = OllamaLLM(model="llama3", temperature=0)
# SQLCoder: Sirf schema dekh kar accurate query banane ke liye hai
sql_llm = OllamaLLM(model="sqlcoder", temperature=0)

# 3. Prompt 1: Details ko Track aur Combine karne ke liye (Llama 3)
extractor_prompt = ChatPromptTemplate.from_template("""
You are a profile extractor assistant. Your job is to look at the Chat History and the New User Message, and extract the current cumulative user profile fields in JSON format.
If a detail was mentioned in the history, keep it. If it is updated in the new message, change it. If missing, keep it null.

Fields to extract:
- age (INTEGER)
- family_income (INTEGER)
- occupation (STRING, e.g., 'Student')
- gender (STRING, e.g., 'Male', 'Female')

Chat History:
{history}

New User Message: {input}

Respond ONLY with a valid JSON object. Do not add any conversational text or markdown blocks.
""")

extractor_chain = extractor_prompt | general_llm | StrOutputParser()

# 4. Prompt 2: Database ke liye SQL generate karne ke liye (SQLCoder)
sql_prompt = ChatPromptTemplate.from_template("""
### Task
Generate a PostgreSQL query for 'wb_schemes' table based on the extracted user profile data.

### Database Schema
Table: wb_schemes
Columns:
- id (INTEGER)
- scheme_name (VARCHAR)
- min_age (INTEGER)
- max_age (INTEGER)
- max_income (INTEGER)
- gender (VARCHAR)
- occupation (VARCHAR)
- education (VARCHAR)

### Extracted Profile Data:
Age: {extracted_age}
Income: {extracted_income}
Occupation: {extracted_occupation}
Gender: {extracted_gender}

### Strict Rules for NULL handling:
1. Base query is always: SELECT * FROM wb_schemes WHERE 1=1
2. If Age is NOT 'null' and NOT None, ADD: AND (min_age <= {extracted_age} AND max_age >= {extracted_age})
3. If Income is NOT 'null' and NOT None, ADD: AND (max_income >= {extracted_income})
4. If Occupation is NOT 'null' and NOT None, ADD: AND (occupation ILIKE '%{extracted_occupation}%' OR education ILIKE '%{extracted_occupation}%')
5. If Gender is NOT 'null' and NOT None, ADD: AND (gender ILIKE '%{extracted_gender}%')
6. Do NOT invent any WHERE clause for fields that are 'null'.
7. Output ONLY the raw SQL query. No markdown blocks, no explanations.

Response:
SELECT 
""")

sql_chain = sql_prompt | sql_llm | StrOutputParser()

# 5. State Variables (Jo details ko hamesha jod kar rakhega)
user_profile = {"age": "null", "family_income": "null", "occupation": "null", "gender": "null"}
history_str = ""

# --- Bot Loop ---
def start_langchain_bot():
    global history_str, user_profile
    print("Bot : System ready. How can I help you?")
    
    while True:
        user_input = input("\nUser: ").strip()
        if not user_input: continue

        # Reset memory if a new user arrives
        if "mera naam" in user_input.lower() and "aman" not in user_input.lower():
            print("[System]: New user detected. Clearing profile memory...")
            user_profile = {"age": "null", "family_income": "null", "occupation": "null", "gender": "null"}
            history_str = ""

        try:
            # Step A: Hinglish text se details extract karo aur global profile me save karo
            raw_json = extractor_chain.invoke({"history": history_str, "input": user_input})
            cleaned_json = raw_json.strip().replace("```json", "").replace("```", "").strip()
            
            try:
                new_data = json.loads(cleaned_json)
                for key in user_profile:
                    if key in new_data and new_data[key] is not None and str(new_data[key]).lower() != "null":
                        user_profile[key] = new_data[key]
            except Exception:
                pass # JSON parse fail hone par purani details bani rahengi

            print(f"--- DEBUG: Current Cumulative Profile: {user_profile} ---")

            # Step B: Safe format mein SQLCoder se query generate karwao
            generated_sql = sql_chain.invoke({
                "extracted_age": user_profile["age"],
                "extracted_income": user_profile["family_income"],
                "extracted_occupation": user_profile["occupation"],
                "extracted_gender": user_profile["gender"]
            }).strip()

            # Query Clean-up block
            generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()
            if not generated_sql.upper().startswith("SELECT"):
                generated_sql = "SELECT " + generated_sql
            
            print(f"--- DEBUG: LLM generated this SQL: {generated_sql} ---")

            # Step C: Database par query execute karo
            response = execute_query.invoke(generated_sql)
            
            if response:
                print(f"\n[Bot]: Based on your profile, you are eligible for:\n{response}")
            else:
                print("\n[Bot]: No eligible schemes found.")
            
            # History update karein taaki context yaad rahe
            history_str += f"\nUser: {user_input}\nBot: {str(response)}"

        except Exception as e:
            print(f"Bot: Sorry, I faced an error: {e}")

if __name__ == "__main__":
    start_langchain_bot()