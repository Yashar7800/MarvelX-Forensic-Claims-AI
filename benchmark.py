import os
import json
import easyocr
from dotenv import load_dotenv

# Import our new LangGraph workflow
from claims_graph import create_graph

# Load environment variables (API keys, etc.)
load_dotenv()

def run_benchmark():
    # Make sure you have GROQ_API_KEY in your .env file
    model_id = "llama-3.3-70b-versatile"
    
    print("⏳ Initializing LangGraph and EasyOCR (this might take a few seconds)...")
    app = create_graph(model_id=model_id)
    reader = easyocr.Reader(['en']) 
    
    base_path = "data/" 
    results = []

    # Find all directories that start with 'claim'
    claim_folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
    # Sort them numerically (claim 1, claim 2...)
    claim_folders.sort()
    
    print(f"🚀 Starting Multi-Agent benchmark for {len(claim_folders)} claims...")

    for folder in claim_folders:
        folder_path = os.path.join(base_path, folder)
        desc_path = os.path.join(folder_path, "description.txt")
        
        if not os.path.exists(desc_path):
            continue

        # Read the customer's description
        with open(desc_path, "r", encoding="utf-8") as f:
            description = f.read()

        # Gather all other files (receipts, photos, certificates)
        docs = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                if f != "description.txt" and f != "answer.json"]

        print(f"🔎 Processing {folder}...")

        # ---------------------------------------------------------
        # 1. BUILD THE CONTEXT STRING (Using your logic from agent.py)
        # ---------------------------------------------------------
        context = f"CLAIM DESCRIPTION: {description}\n\nSUPPORTING DOCUMENTS:\n"
        
        for path in docs:
            path = path.replace("\\", "/")
            if not os.path.exists(path):
                continue
            
            filename = os.path.basename(path)

            if path.lower().endswith(('.txt', '.md')):
                with open(path, 'r', encoding='utf-8') as f:
                    context += f"\n[Text Document: {filename}]\n{f.read()}\n"
                    
            elif path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    ocr_results = reader.readtext(path, detail=0)
                    text = " ".join(ocr_results)
                except Exception as e:
                    text = f"[OCR Error: {str(e)}]"
                    
                context += f"\n[Image/OCR Content: {filename}]\n{text}\n"
        
        # ---------------------------------------------------------
        # 2. RUN THE LANGGRAPH WORKFLOW
        # ---------------------------------------------------------
        initial_state = {"context": context, "status": "PASS"}
        
        try:
            # The graph routes automatically between Gateman and Auditor
            result_state = app.invoke(initial_state)
            
            # Determine which agent provided the final answer
            if result_state["status"] == "FAIL":
                print("   ❌ Gateman triggered a Kill-Switch!")
                analysis = result_state.get("gateman_result", {})
            else:
                print("   ✅ Gateman passed. Auditor completed policy check.")
                analysis = result_state.get("final_result", {})

        except Exception as e:
            print(f"   ⚠️ Error processing {folder}: {e}")
            analysis = {
                "decision": "UNCERTAIN",
                "reasoning": f"System Error: {str(e)}",
                "confidence_score": 0.0,
                "payout_amount": 0.0
            }

        # 3. SAVE THE RESULTS
        results.append({
            "claim": folder,
            "decision": analysis.get("decision", "UNCERTAIN"),
            "confidence_score": analysis.get("confidence_score", 0.0),
            "reasoning": analysis.get("reasoning", "No reasoning provided."),
            "payout": analysis.get("payout_amount", 0.0)
        })

    # Save to the results file
    output_file = "system_results_v2.json" 
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ DONE! All results saved to {output_file}")

if __name__ == "__main__":
    run_benchmark()