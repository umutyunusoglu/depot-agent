import json
import sys
from time import perf_counter

from ollama import chat

from depot_agent.rag import search_policies, search_product_docs
from tools import get_product_info, get_substitutes

MODEL = "granite4.2:8b"
MAX_STEPS = 6

TOOLS = {
    "get_product_info": get_product_info,
    "get_substitutes": get_substitutes,
    "search_product_docs": search_product_docs,
    "search_policies": search_policies,
}

SYSTEM_PROMPT = """You are an assistant for the sales team of Northline Building Supply, \
a roofing materials distributor with warehouses in Dallas, Houston and Atlanta.
Always use the tools to answer questions about products, prices and stock. Never guess numbers.
If a tool returns an error, explain it or ask the user to clarify.
For specs and policies, use the search tools and cite the source file, e.g. [summit.md]. If the documents don't contain the answer, say you don't have that information.
"""


def _execute_tool(name: str, args: dict) -> dict:
    if name not in TOOLS:
        return {"error": f"Unknown tool '{name}'. Available tools: {list(TOOLS)}"}
    try:
        return TOOLS[name](**args)
    except TypeError as e:  # yanlış ya da eksik argüman
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:  # tool'un içinde başka bir hata (ör. veritabanı)
        return {"error": f"{name} failed: {e}"}


def run_agent(question: str, max_steps: int = MAX_STEPS) -> str:
    start = perf_counter()
    input_tokens = 0
    output_tokens = 0
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    # Model sınıra kadar cevap vermezse kullanıcı bunu görür.
    answer = "Sorry, I couldn't answer this within the step limit."

    for step in range(1, max_steps + 1):
        response = chat(model=MODEL, messages=messages, tools=list(TOOLS.values()))
        messages.append(response.message)
        input_tokens += response.prompt_eval_count or 0
        output_tokens += response.eval_count or 0

        # Tool istemediyse cevabını vermiştir.
        if not response.message.tool_calls:
            answer = response.message.content
            break

        for call in response.message.tool_calls:
            name = call.function.name
            args = call.function.arguments
            print(f"  -> {name}({args})")
            result = _execute_tool(name, args)
            messages.append(
                {"role": "tool", "content": json.dumps(result), "tool_name": name}
            )

    elapsed = perf_counter() - start
    print(
        f"  [steps={step}  time={elapsed:.1f}s  tokens in/out={input_tokens}/{output_tokens}]"
    )
    return answer


if __name__ == "__main__":
    print(run_agent(" ".join(sys.argv[1:])))
