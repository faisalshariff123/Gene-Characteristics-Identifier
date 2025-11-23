from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = "AIzaSyDvPLYJdugD4MMbyJCB8i9zmB7ElUoZASw"
def search_gene(gene_name):
    """
    umm so this function searches for a gene and gets basic information
    gene_name: like "BRCA1" or "TP53"
    """
    print(f"Searching for gene: {gene_name}")
    
    try:
        # Step 1: Find the gene ID
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            'db': 'gene',
            'term': f'{gene_name}[Gene Name] AND human[Organism]',
            'retmode': 'json'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # Check if we found anything
        if 'idlist' not in data['esearchresult'] or not data['esearchresult']['idlist']:
            return