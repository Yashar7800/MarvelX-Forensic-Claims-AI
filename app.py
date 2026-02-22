from flask import Flask, render_template, request, jsonify
import os
import subprocess
from werkzeug.utils import secure_filename
import json
import sys

app = Flask(__name__)

# Set the base directory for data
BASE_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(BASE_DATA_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit_claim', methods=['POST'])
def submit_claim():
    try:
        # 1. Get Inputs
        claim_number = request.form.get('claim_number')
        description_text = request.form.get('description')
        proof_file = request.files.get('proof')
        supporting_file = request.files.get('supporting')

        if not claim_number:
            return jsonify({"success": False, "error": "Claim number is required"}), 400

        # 2. Create the specific Claim Folder
        safe_claim_name = secure_filename(claim_number.lower())
        claim_dir = os.path.join(BASE_DATA_DIR, safe_claim_name)
        os.makedirs(claim_dir, exist_ok=True)

        # 3. Save Proof (Image)
        if proof_file and proof_file.filename:
            proof_ext = os.path.splitext(proof_file.filename)[1]
            proof_path = os.path.join(claim_dir, f"proof{proof_ext}")
            proof_file.save(proof_path)

        # 4. Save Description as description.txt
        if description_text:
            desc_path = os.path.join(claim_dir, 'description.txt')
            with open(desc_path, 'w', encoding='utf-8') as f:
                f.write(description_text)

        # 5. Save Supporting File (.md)
        if supporting_file and supporting_file.filename:
            supp_path = os.path.join(claim_dir, secure_filename(supporting_file.filename))
            supporting_file.save(supp_path)

        # 6. Run the benchmark.py script
        subprocess.run([sys.executable, 'benchmark.py'], check=True)

        # 7. Fetch the verdict
        results_file = "system_results_v2.json"
        verdict = {"decision": "UNCERTAIN", "reasoning":f"Claim {claim_number} not found in {results_file}.", "payout_amount": 0.0}
        
        if os.path.exists(results_file):
            with open(results_file, 'r') as f:
                try:
                    all_results = json.load(f)
                    
                    import re
                    search_id = re.sub(r'[^a-zA-Z0-9]', '', claim_number.lower())
                    
                    for res in all_results:
                        raw_val = str(res.get("claim", res.get("claim_id", "")))
                        res_id = re.sub(r'[^a-zA-Z0-9]', '', raw_val.lower())
                        
                        if res_id == search_id:
                            verdict = {
                                "decision": res.get("decision", res.get("status", "UNCERTAIN")),
                                "reasoning": res.get("reasoning", "No reasoning provided."),
                                "payout_amount": res.get("payout_amount", res.get("payout", 0.0))
                            }
                            break
                except json.JSONDecodeError:
                    # FIX 2: Added the missing except block
                    verdict["reasoning"] = "Error reading the results file (invalid JSON)."

        # FIX 3: Placed the return statement at the bottom so it ALWAYS returns a response
        return jsonify({"success": True, "verdict": verdict})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    

if __name__ == '__main__':
    app.run(debug=True, port=5000)