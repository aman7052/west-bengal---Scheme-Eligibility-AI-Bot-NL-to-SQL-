from langchain_community.utilities import SQLDatabase
from langchain_ollama import ChatOllama
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter
from langchain_community.llms import Ollama

# 1. Database Connection (PostgreSQL)
# Format: postgresql+psycopg2://user:password@host:port/dbname
postgres_uri = "postgresql+psycopg2://postgres:705219@localhost:5432/demodb"
db = SQLDatabase.from_uri(postgres_uri, include_tables=['wb_schemes'])

# 2. LLM Setup (Llama 3 via Ollama)
llm = ChatOllama(model="sqlcoder", temperature=0)

# 3. Prompt Template 
system_prompt = """
### Task
Generate a PostgreSQL query to find eligible schemes from the 'wb_schemes' table based on the user's question.

### Database Schema
You MUST ONLY use the 'wb_schemes' table. Do NOT invent other tables.
Here is the official table structure:
{table_info}

The table 'wb_schemes' has ONLY these columns:
- id (INTEGER)
- scheme_name (VARCHAR)
- scheme_code (VARCHAR)
- min_age (INTEGER)
- max_age (INTEGER)
- max_income (INTEGER)
- gender (VARCHAR)
- occupation (VARCHAR)
- education (VARCHAR)

### Strict Mapping Rules:
1. TABLE: Always use 'wb_schemes'. Never use any other table name.
2. AGE: Use (min_age <= [age] AND max_age >= [age]). For example, if age is 22: (min_age <= 22 AND max_age >= 22).
3. INCOME: Use (max_income >= [income]). For example, if income is 10000: (max_income >= 10000).
4. EDUCATION/STUDENT: If user mentions '12th' or 'student', filter using (education ILIKE '%12%' OR occupation ILIKE '%Student%'). Do NOT use a column named 'class'.
5. LIMIT: Always use LIMIT {top_k}.
6. OUTPUT: Return ONLY the raw SQL query starting with SELECT. No explanations.

### User Question:
{input}

### Response:
SELECT 
"""

# Here presence of top_k and table_info is imp
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

# 4. Memory Setup (List to store history)
history = []

# 5. LangChain Chain Setup

# 1. SQL Query Writing Chain
 
write_query = create_sql_query_chain(llm, db, prompt)

# 2. Query execute  
execute_query = QuerySQLDataBaseTool(db=db)

# 3. Final Chain Logic
 
chain = (
    RunnablePassthrough.assign(
        table_info=lambda _: db.get_table_info(),
        history=lambda _: history,
        top_k=lambda _: 17,
        question=lambda x: x["input"]  
    )
    | write_query 
    | (lambda x: {"query": x}) 
    | execute_query
)

# --- Bot Loop ---
def start_langchain_bot():
    print("Bot : System ready. How can I help you?")
    
    while True:
        user_input = input("\nUser: ").strip()
        if not user_input: continue

        # Identity Reset Logic (Simple check)
        if "mera naam" in user_input.lower() and len(history) > 0:
            print("[System]: New user detected. Clearing memory...")
            history.clear()

        try:
            generated_sql = write_query.invoke({
                "question": user_input, 
                "table_info": db.get_table_info(), 
                "history": history, 
                "top_k": 5
            })
            print(f"--- DEBUG: LLM generated this SQL: {generated_sql} ---")

            # finding result 
            response = chain.invoke({"input": user_input})
            if response and "Not Found" not in str(response):
                print(f"\n[Bot]: Based on your profile, you are eligible for:\n{response}")
            else:
                print("Bot: Not Found.")
            
            # Update history (saving human input and response)
            history.append(("human", user_input))
            # Store the response in string format
            history.append(("ai", str(response)))

        except Exception as e:
            print(f"Bot: Sorry, I don't understand this query. Error: {e}")

if __name__ == "__main__":
    start_langchain_bot()