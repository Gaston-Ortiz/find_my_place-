# Third party imports
import boto3
from langchain_aws import ChatBedrock
from langchain_community.llms import DeepInfra
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# Internal dependencies
from ai_bot_app import settings
from ai_bot_app.routers.routers_dependencies.tools import retrieve_docs, save_data


def get_llm_model(
    model_name: str = settings.CHAT_MODEL,
    temperature: float = 0.1,
):
    """Initialize the agent with the given parameters."""
    # Hardcoded model until we enable the model selection in ux
    model_name = settings.CHAT_MODEL

    if "gpt" in model_name:
        llm_model = ChatOpenAI(model_name=model_name, temperature=temperature)
    elif "claude" in model_name:
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.region_name,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        llm_model = ChatBedrock(
            client=bedrock_runtime,
            model_id=model_name,
            provider="anthropic",
        )
    else:
        llm_model = DeepInfra(model_id=model_name)
        llm_model.model_kwargs = {
            "temperature": temperature,
            "max_new_tokens": 4000,
        }

    return llm_model


def get_react_agent(model_name: str = settings.CHAT_MODEL, temperature: float = 0.3):
    """
    Get a react agent

    Parameters
    ----------
    model_name: str
        The name of the model to use
    temperature: float
        The temperature to use

    Returns
    -------
    agent_executor: Runnable
        The react agent
    """
    llm_model = get_llm_model(model_name=model_name, temperature=temperature)

    prompt_template = """
    You are a helpful assistant that helps the user to find the best product for their needs. In this case the products that we have are houses

    You can use the tool retrieve_docs to get more information about the houses.
    You can also use the tool save_data to save the data of the houses that you find if the user asks for it.

    Now help the user to find the best house for their needs.
    """

    memory = MemorySaver()

    agent_executor = create_react_agent(
        model=llm_model,
        tools=[retrieve_docs, save_data],
        checkpointer=memory,
        prompt=prompt_template,
    )

    return agent_executor
