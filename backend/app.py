# app.py — Bio Re:code Backend Server (Gemini 2.0 Flash Version)
# This file handles searching for genes and generating AI summaries using Google Gemini 2.0.

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv

# Load environment variables (so we don't expose API keys in code)
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = Flask(__name__)
CORS(app)  # Enables frontend (like Streamlit or HTML) to talk to this backend


# =====================================================
# 🧬 Function 1: Search for a gene in the NCBI database
# =====================================================
def search_gene(gene_name):
    """
    This function searches for a gene and retrieves basic biological information
    from the NCBI Gene database.
    Example: "BRCA1" or "TP53"
    """
    print(f"Searching for gene: {gene_name}")
    
    try:
        # Step 1: Find the gene ID using NCBI's eSearch API
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            'db': 'gene',
            'term': f'{gene_name}[Gene Name] AND human[Organism]',
            'retmode': 'json'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # Check if results exist
        if 'idlist' not in data['esearchresult'] or not data['esearchresult']['idlist']:
            return {"error": "Gene not found"}
        
        gene_id = data['esearchresult']['idlist'][0]
        print(f"Found gene ID: {gene_id}")  # FIXED TYPO: was gene_sid
        
        # Step 2: Get detailed info using NCBI's eSummary API
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        summary_params = {
            'db': 'gene',
            'id': gene_id,
            'retmode': 'json'
        }
        
        summary_response = requests.get(summary_url, params=summary_params, timeout=10)
        summary_data = summary_response.json()
        
        gene_info = summary_data['result'][gene_id]
        
        # Step 3: Return key details for display or AI summary
        return {
            'name': gene_info.get('name', gene_name),  # Gene symbol (e.g., BRCA1)
            'gene_id': gene_id,  # Unique NCBI Gene ID
            'description': gene_info.get('description', 'No description available'),
            'summary': gene_info.get('summary', 'No summary available'),
            'chromosome': gene_info.get('chromosome', 'Unknown'),  # Which chromosome it's located on
            'map_location': gene_info.get('maplocation', 'Unknown'),  # Exact chromosome position
            'aliases': ', '.join(gene_info.get('otheraliases', [])) if gene_info.get('otheraliases') else 'None',
            'mim_number': ', '.join([str(m) for m in gene_info.get('mim', [])]) if gene_info.get('mim') else 'Not available',
            'organism': gene_info.get('organism', {}).get('scientificname', 'Homo sapiens'),
            'gene_type': gene_info.get('geneticsource', 'Unknown')  # e.g., protein-coding, pseudogene, etc.
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}


# =====================================================
# 🤖 Function 2: Generate AI Summary using OpenRouter API
# =====================================================
def create_ai_summary(gene_info):
    """
    This function takes gene information and asks an AI model via OpenRouter
    to create a short, human-readable summary for researchers and clinicians.
    
    OpenRouter provides access to multiple models including Claude, GPT-4, and more!
    """
    print("Creating AI summary with OpenRouter...")
    
    try:
        # OpenRouter API endpoint
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Prompt template for AI
        prompt = f"""You are a bioinformatics expert. Create a brief 3–4 sentence summary for researchers and clinicians.

Gene: {gene_info.get('name', 'Unknown')}
Description: {gene_info.get('description', 'No description')}
Details: {gene_info.get('summary', 'No details')[:500]}

Focus on:
1. What this gene does (functional role)
2. Any disease connections
3. Clinical significance

Keep it concise and professional."""
        
        # OpenRouter request payload
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",  # Optional, for rankings
            "X-Title": "Bio Re:code Gene Search"       # Optional, for rankings
        }
        
        data = {
            "model": "anthropic/claude-3.5-sonnet",  # You can change this to other models
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 300
        }
        
        # Send the request to OpenRouter
        response = requests.post(url, json=data, headers=headers, timeout=30)
        result = response.json()
        
        # Extract AI text response
        if 'choices' in result and len(result['choices']) > 0:
            ai_text = result['choices'][0]['message']['content']
            model_used = result.get('model', 'Unknown Model')
            return ai_text, model_used
        else:
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            return f"Could not generate AI summary. Error: {error_msg}", "Error"
            
    except Exception as e:
        print(f"AI Error: {e}")
        return f"AI summary unavailable: {str(e)}", "Error"


# =====================================================
# 🌐 Flask API Endpoints
# =====================================================

# Serve the CRT frontend
@app.route('/')
def index():
    """Serve the retro CRT-themed frontend interface"""
    return render_template('index.html')


# Original search endpoint
@app.route('/search', methods=['POST'])
def search():
    """
    This endpoint handles POST requests from your frontend or Streamlit interface.
    It expects a JSON object containing { "gene": "<gene_name>" }.
    """
    print("\n=== New Search Request ===")
    
    # Extract gene name from incoming request
    data = request.get_json()
    gene_name = data.get('gene', '').strip().upper()
    
    if not gene_name:
        return jsonify({"error": "Please enter a gene name"}), 400
    
    print(f"Searching for: {gene_name}")
    
    # Step 1: Get gene data from NCBI
    gene_data = search_gene(gene_name)
    if "error" in gene_data:
        return jsonify(gene_data), 404
    
    # Step 2: Generate AI summary with OpenRouter
    ai_summary, ai_model = create_ai_summary(gene_data)
    
    # Step 3: Combine all info into one response
    result = {
        "success": True,
        "gene": gene_data['name'],
        "gene_id": gene_data['gene_id'],
        "description": gene_data['description'],
        "summary": gene_data['summary'],
        "chromosome": gene_data['chromosome'],
        "map_location": gene_data['map_location'],
        "aliases": gene_data['aliases'],
        "mim_number": gene_data['mim_number'],
        "organism": gene_data['organism'],
        "gene_type": gene_data['gene_type'],
        "ai_summary": ai_summary,
        "source": "NCBI Gene Database",
        "ai_model": ai_model
    }
    
    print("Search completed successfully!")
    return jsonify(result)


# CRT Frontend compatible endpoint
@app.route('/api/search', methods=['POST'])
def api_search():
    """
    This endpoint is compatible with the CRT frontend.
    It expects a JSON object containing { "gene_name": "<gene_name>" }.
    """
    print("\n=== CRT Frontend Search Request ===")
    
    data = request.get_json()
    gene_name = data.get('gene_name', '').strip().upper()
    
    if not gene_name:
        return jsonify({'error': 'No gene name provided'}), 400
    
    print(f"Searching for: {gene_name}")
    
    # Step 1: Get gene data from NCBI
    gene_data = search_gene(gene_name)
    if "error" in gene_data:
        return jsonify({'error': f'Gene {gene_name} not found in database'}), 404
    
    # Step 2: Generate AI summary with OpenRouter
    ai_summary, ai_model = create_ai_summary(gene_data)
    
    # Step 3: Return data in format compatible with CRT frontend
    result = {
        'symbol': gene_data['name'],
        'name': gene_data['description'],
        'gene_id': gene_data['gene_id'],
        'chromosome': gene_data['chromosome'],
        'location': gene_data['map_location'],
        'description': gene_data['summary'],
        'aliases': gene_data['aliases'],
        'mim_number': gene_data['mim_number'],
        'organism': gene_data['organism'],
        'gene_type': gene_data['gene_type'],
        'ai_summary': ai_summary,
        'ai_model': ai_model
    }
    
    print("Search completed successfully!")
    return jsonify(result)


# Simple test route to check backend connection
@app.route('/test', methods=['GET'])
def test():
    """
    Basic health check route to verify the server is running.
    """
    return jsonify({
        "status": "Server is running!",
        "message": "Bio Re:code API v1.0",
        "ai_provider": "OpenRouter",
        "available_models": [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4-turbo",
            "google/gemini-pro",
            "meta-llama/llama-3.1-70b-instruct"
        ]
    })


# =====================================================
# 🚀 Run the Flask Server
# =====================================================
if __name__ == '__main__':
    print("=" * 50)
    print("🧬 Bio Re:code Server Starting...")
    print("=" * 50)
    print("🤖 Using: OpenRouter API (Claude, GPT-4, etc.)")
    print("📡 Server running at: http://localhost:5000")
    print("🧪 Test it at: http://localhost:5000/test")
    print("=" * 50)
    app.run(debug=True, port=5000)