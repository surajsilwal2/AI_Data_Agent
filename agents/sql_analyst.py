import os
from utils.llm_pick import pick_llm
from langchain_core.messages import HumanMessage, AIMessage
from utils.schema_context import get_schema_context
from utils.database import execute_sql_query
import json
from models.schema import AgentSchema, JudgeSchema
from langgraph.graph import StateGraph, START, END


def curate_questions(state: AgentSchema) -> AgentSchema:
    user_question = state.user_question
    llm = pick_llm('low')
    response = llm.invoke(f"curate the following question: {user_question}").content
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
        
    generated_sql_query = llm.invoke(prompt_context).content
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
    answer = response['answer'].strip().lower()
    state.is_safe = ("safe" if answer in ('yes', 'safe') else 'unsafe')
    state.comments = response['comments']

    return state


def canceled_sql(state: AgentSchema) -> AgentSchema:
    comments = state.comments
    state.final_answer = f"The generated sql query is seemed unsafe to execute. The reason provided by the judge is: {comments}"
    state.messages = state.messages + [AIMessage(content=f"{state.final_answer}")]
    return state



def execute_query(state: AgentSchema) -> AgentSchema:
    sql_query = state.generated_sql_query

    if not sql_query.strip():
        state.sql_query_execution_result = json.dumps({
            "success": False,
            "error": "No SQL query was generated",
            "data": []
        })
        return state

    execution_result = execute_sql_query(sql_query)

    state.sql_query_execution_result = json.dumps(execution_result, default=str)

    return state


def represent_final_answer(state: AgentSchema) -> AgentSchema:

    execution_result = state.sql_query_execution_result
    curated_question = state.curated_ques

    llm = pick_llm("low")

    prompt = f"""
    You are an SQL analyst agent. Your task is to provide a final answer to the user based on the
    execution result of the SQL query and the user's original question. The final answer should be
    concise, clear, and directly address the user's query. Avoid including any SQL code or technical
    details in the final answer. The final answer should be in a user-friendly format that is easy to
    understand. If the execution result is empty or does not provide a clear answer to the user's question, explain this in the final answer. \n
    Here is the execution result: {execution_result} \n
    Here is the user's original question: {curated_question}
    """

    # Get the final answer from the LLM
    llm_response = llm.invoke(prompt).content

    state.final_answer = llm_response
    # Append the final answer to the messages list
    state.messages = state.messages + [AIMessage(content=f"{llm_response}")]

    return state



sql_agent_graph = StateGraph(AgentSchema)

sql_agent_graph.add_node(curate_questions, name="curate_questions")
sql_agent_graph.add_node(prompt_query_context, name = "prompt_query_context")
sql_agent_graph.add_node(generate_sql, name="generate_sql")
sql_agent_graph.add_node(is_safe_sql, name="is_safe_sql")
sql_agent_graph.add_node(canceled_sql, name="canceled_sql")
sql_agent_graph.add_node(execute_query, name="execute_query")
sql_agent_graph.add_node(represent_final_answer, name="represent_final_answer")


# edges
sql_agent_graph.add_edge(START, "curate_questions")
sql_agent_graph.add_edge("curate_questions","prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql")
sql_agent_graph.add_edge("generate_sql", "is_safe_sql")

# conditional edge function
def is_safe_sql_edge(state: AgentSchema) -> str:
    if state.is_safe == "safe":
        return "execute_query"
    else:
        return "canceled_sql"

sql_agent_graph.add_conditional_edges("is_safe_sql", is_safe_sql_edge)
sql_agent_graph.add_edge("canceled_sql", END)
sql_agent_graph.add_edge("execute_query", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)

# compile 
sql_analyst = sql_agent_graph.compile()

if __name__ == "__main__":

    input_schema = {
        "messages": [],
        "user_question": "What are the different types of Payment Methods we have in our database",
        "curated_ques": "",
        "prompt_query_Context": "",
        "generated_sql_query": "",
        "is_safe": "unsafe",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }

    # Execute the Graph
    print("Running SQL agent...", flush=True)
    sql_analyst_response = sql_analyst.invoke(input_schema)
    # Print the final output of the graph execution
    print(sql_analyst_response['messages'])
    print("********************************")

    # Print the generated SQL query
    print(sql_analyst_response['generated_sql_query'])

    print("********************************")

    # Print the result of executing the SQL query
    print(sql_analyst_response['sql_query_execution_result'])

    print("********************************")



