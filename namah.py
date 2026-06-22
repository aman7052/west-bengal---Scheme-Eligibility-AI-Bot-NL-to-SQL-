from langchain_community.utilities import SQLDatabase
from langchain_ollama import OllamaLLM
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re


# 1. DATABASE CONNECTION (PostgreSQL)

postgres_uri = "postgresql+psycopg2://postgres:705219@localhost:5432/demodb"
db = SQLDatabase.from_uri(postgres_uri, include_tables=['wb_schemes'])
execute_query = QuerySQLDataBaseTool(db=db)

 
# 2. DUAL LLM SETUP
 
general_llm = OllamaLLM(model="llama3", temperature=0)
sql_llm = OllamaLLM(model="llama3", temperature=0)

 
# 3. PROMPT 1: PROFILE EXTRACTOR (Llama 3) - MODIFIED
 
extractor_prompt = ChatPromptTemplate.from_template("""
You are a strict profile extractor assistant. Your job is to look at the Chat History and the New User Message, and extract the current cumulative user profile fields in JSON format.
If a detail was mentioned in the history, keep it. If it is updated in the new message, change it. 

### CRITICAL EXTRACTION RULES:
1. If a field is missing from both history and new message, strictly set its value to the string "N/A". Do NOT use null or None.
2. If the user mentions education like '12th' or '12th standard', strictly extract ONLY the number '12'. For '8th', extract '8'.
3. NEVER put numbers like '12', '12th', '8' inside the 'school_type' field. 'school_type' can ONLY be 'Government', 'Private' or "N/A".
4. STRICT NO-ASSUMPTION RULE: Do NOT make any assumptions or logical guesses about 'education' or any other field based on age or occupation. For example, if a user says they are a 25-year-old "student" but does NOT explicitly state their class or education level in the text, you MUST set 'education' to "N/A". Only extract what is explicitly written!.
5. STRICT GENDER RULE: NEVER guess or assume the 'gender' field based on the user's name (e.g., if the name is 'Ragini' or 'Ritika', do NOT set gender to 'Female' unless the user explicitly mentions 'female', 'girl', or 'woman' in the text). Keep the previous gender or set it to "N/A" if never mentioned.
6. "If the user explicitly asks to 'remove', 'clear'  a specific field/detail (e.g., 'remove education' or 'clear income'), you MUST strictly set that field's value back to 'N/A'."
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

 
# 4. PROMPT 2: PURE LLM SQL GENERATOR WITH EXAMPLES (SQLCoder) - MODIFIED
 
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
6. For any valid text field, dynamically generate the condition exactly like this: AND (field_name ILIKE '%<value_from_profile>%' OR field_name ILIKE '%Any%')
                                              
### Examples of how you must behave:

Example 1 Input:
- age: 25, family_income: N/A, gender: Female, caste: N/A, marital_status: N/A, occupation: N/A, residence_area: N/A, school_type: N/A, education: N/A
Example 1 Expected SQL:
SELECT wb_schemes.scheme_name, wb_schemes.scheme_code FROM wb_schemes WHERE 1=1 AND (min_age <= 25 AND max_age >= 25) AND (gender ILIKE '%Female%' OR gender ILIKE '%Any%');

Example 2 Input:
- age: N/A, family_income: 150000, gender: N/A, caste: N/A, marital_status: N/A, occupation: Farmer, residence_area: N/A, school_type: N/A, education: N/A
Example 2 Expected SQL:
SELECT wb_schemes.scheme_name, wb_schemes.scheme_code FROM wb_schemes WHERE 1=1 AND (max_income >= 150000) AND (occupation ILIKE '%Farmer%' OR occupation ILIKE '%Any%');

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

 
# 5. STATE VARIABLES (Memory Management)
 
user_profile = {
    "age": "N/A", "family_income": "N/A", "gender": "N/A", "caste": "N/A",
    "marital_status": "N/A", "occupation": "N/A", "residence_area": "N/A",
    "school_type": "N/A", "education": "N/A"
}
history_str = ""

 
# 6. BOT CORE LOOP
 
def start_langchain_bot():
    global history_str, user_profile
    print("Bot : System ready. How can I help you?")
    
    while True:
        user_input = input("\nUser: ").strip()
        if not user_input: continue

        #  DYNAMIC MEMORY RESET BLOCK
        if user_input.lower().strip() in ['reset', 'clear', 'new']:
            print("[System]: Memory reset requested. Clearing current profile and chat history...")
            user_profile = {k: "N/A" for k in user_profile}
            history_str = ""
            print("[System]: System ready. How can I help you?")
            continue

        try:
            # Step A:JSON extraction from Llama 3
            raw_json = extractor_chain.invoke({"history": history_str, "input": user_input})
            cleaned_json = raw_json.strip().replace("```json", "").replace("```", "").strip()
            
            try:
                new_data = json.loads(cleaned_json)
                
                # Very simple and generic update:
                # If LLM has provided a value for a field in JSON, update it.
                # If LLM has carried forward a value from history and provided the old value, leave it.
                for key in user_profile:
                    if key in new_data and new_data[key] is not None and str(new_data[key]).lower() != "null":
                        user_profile[key] = new_data[key]
                
            except Exception as json_err:
                pass

            print(f"--- DEBUG: Current Cumulative Profile: {user_profile} ---")

            # Step B:LLM SQL GENERATION  
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

            # Clean markdown if any
            generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()
            if not generated_sql.upper().startswith("SELECT"):
                generated_sql = "SELECT " + generated_sql

            print(f"--- DEBUG: LLM Generated SQL: {generated_sql} ---")

            # Step C: Database Query Execution
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