from models.schema import AgentSchema, JudgeSchema
from utils.llm_pick import pick_llm
from langchain_core.messages import HumanMessage
from utils.schema_context import get_schema_context


def curate_questions(state: AgentSchema) -> AgentSchema:
    user_question = state.user_question
    llm = pick_llm('low')
    response = llm.invoke(f"curate the following question: {user_question}")
    state.curated_ques = response
    state.messages = state.messages + [HumanMessage(content=f"{response}")]
    return state


def prompt_query_context(state: AgentSchema) -> AgentSchema:
    user_question = state.curated_ques  # get user question

    db_context = get_schema_context('public')  # retrieve database structure

    # combine question and database context
    prompt_context = f"""
     You are a PostgreSQL SQL generation agent.

     USER QUESTION:
    {user_question}

    DATABASE SCHEMA:
    {db_context}

  INSTRUCTIONS:
    1. Generate SQL using only existing tables and columns.
    2. Use the relationships defined in the schema.
    3. Do not invent table names or column names.
    4. Generate read-only SELECT queries only.
    5. Return SQL that answers the user's question.
    6. Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
  """

    state.prompt_query_Context = prompt_context

    return state



def generate_sql(state: AgentSchema) -> AgentSchema:
    prompt_context = state.prompt_query_Context
    llm = pick_llm('medium')
        
    generated_sql_query = llm.invoke(prompt_context)
    state.generated_sql_query = generated_sql_query
    return state


def is_safe_sql(state: AgentSchema) -> AgentSchema:

    sql_query = state.generated_sql_query

    llm = pick_llm("medium")
    llm_judge = llm.with_structured_output(JudgeSchema)

    prompt = f"""
    You are an SQL Judge for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for data retrieval and should not modify the 
    database in any way. Neither the SQL query nor the prompt should contain any SQL commands that can modify the
    database, such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any other commands that can change
    the structure or content of the database. If the SQL query is safe, respond with 'Yes' otherwise respond with 
    'No'. Additionally, provide comments explaining your decision.
    Here's the SQL query to evaluate:
    {sql_query}"""

    # Get the structured output as a dictionary
    response = llm_judge.invoke(prompt).model_dump()
    state.is_safe = response['answer']
    state.comments = response['comments']

    return state


def canceled_sql(state: AgentSchema) -> AgentSchema:
    comments = state.comments
    state.final_answer = f"The generated sql query is seemed unsafe to execute. The reason provided by the judge is: {comments}"
    return state



