import json
import re
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from prompts import GATEMAN_PROMPT, AUDITOR_PROMPT

def extract_json(text):
    """Robustly extracts JSON from a string even if it has conversational filler."""
    # Look for anything between { and }
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        return match.group(1)
    return text

# 1. Define the State (the data passed between agents)
class ClaimState(TypedDict):
    context: str               # The OCR and System File text
    gateman_result: dict       # Output from Agent 1
    final_result: dict         # Output from Agent 2
    status: Literal["PASS", "FAIL"]

# 2. Define the Nodes
class ClaimsGraph:
    def __init__(self, model_id: str):
        # We set temperature 0.0 here for both agents
        self.llm = ChatGroq(
            model=model_id, 
            temperature=0.0,
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    def call_gateman(self, state: ClaimState):
        print("--- CALLING GATEMAN ---")
        prompt = GATEMAN_PROMPT + "\n\nINPUT DATA:\n" + state["context"]
        response = self.llm.invoke(prompt)
        
        try:
            # Clean the response before parsing
            cleaned_content = extract_json(response.content)
            res_json = json.loads(cleaned_content)
        except Exception as e:
            print(f"Gateman JSON Error: {e}. Raw content: {response.content}")
            # Fallback if the LLM fails to output JSON
            res_json = {"status": "FAIL", "decision": "UNCERTAIN", "reasoning": "JSON Parse Error"}
            
        return {
            "gateman_result": res_json,
            "status": res_json.get("status", "FAIL")
        }

    def call_auditor(self, state: ClaimState):
        """Second Agent: Only runs if Gateman passes. Checks Policy and Identity."""
        print("--- CALLING AUDITOR ---")
        prompt = AUDITOR_PROMPT + "\n\nINPUT DATA:\n" + state["context"]
        response = self.llm.invoke(prompt)
        
        try:
            # Add the same cleaning and error handling here!
            cleaned_content = extract_json(response.content)
            res_json = json.loads(cleaned_content)
        except Exception as e:
            print(f"Auditor JSON Error: {e}. Raw content: {response.content}")
            res_json = {
                "decision": "UNCERTAIN", 
                "reasoning": "Auditor JSON Parse Error",
                "payout_amount": 0.0,
                "confidence_score": 0.0
            }
            
        return {"final_result": res_json}

    # 3. Define the Routing Logic
    def route_after_gateman(self, state: ClaimState):
        if state["status"] == "FAIL":
            return "end"  # Stop the process
        return "continue" # Move to Auditor

# 4. Build the Graph
def create_graph(model_id: str):
    workflow = ClaimsGraph(model_id)
    builder = StateGraph(ClaimState)

    # Add Nodes
    builder.add_node("gateman", workflow.call_gateman)
    builder.add_node("auditor", workflow.call_auditor)

    # Set Entry Point
    builder.set_entry_point("gateman")

    # Add Conditional Edge
    builder.add_conditional_edges(
        "gateman",
        workflow.route_after_gateman,
        {
            "end": END,
            "continue": "auditor"
        }
    )

    # Finish at END
    builder.add_edge("auditor", END)

    return builder.compile()