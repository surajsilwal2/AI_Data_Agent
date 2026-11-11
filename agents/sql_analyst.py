from models.schema import AgentSchema
from utils.llm_pick import pick_llm


def curate_questions(state: AgentSchema) -> AgentSchema:
    user_question = state.user_question
    llm = pick_llm('low')
    response = llm.invoke(f"curate the following question: {user_question}")
    state.curated_ques = response
    return state