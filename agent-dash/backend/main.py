from flask import Flask, request, jsonify
from flask_cors import CORS
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app, origins="*", allow_headers=["Content-Type"], methods=["GET", "POST", "OPTIONS"])

# Initialize Vertex AI
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "molten-album-478703-d8")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

vertexai.init(project=PROJECT_ID, location=LOCATION)

# gemini model using preview API
#model = GenerativeModel("gemini-2.0-flash-001")
model = GenerativeModel("gemini-2.5-pro")

# Database schema for employee data
EMPLOYEE_SCHEMA = {
    "fields": {
        "demographics": ["first_name", "last_name", "gender", "country_of_birth", "birth_year"],
        "location": ["location_city"],
        "job_info": ["job_profile", "job_title", "job_family_group", "job_family_name", "job_code"],
        "organization": ["supervisory_organization_siglum", "band"],
        "classification": ["blue_white_collar", "worker_type", "worker_status"],
        "time_tracking": ["planned_hours", "overtime_hours"],
        "employment_dates": ["start_date", "termination_date"]
    }
}

# System prompt
SYSTEM_PROMPT = """You are an expert AI dashboard analyst for HR and workforce analytics.

Generate intelligent dashboards from employee data. When user requests a dashboard, respond in JSON format:

{
  "message": "Brief explanation",
  "analysis_type": "attrition|hours|demographics|workforce|custom",
  "dashboard": {
    "title": "Dashboard Title",
    "subtitle": "Context",
    "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
    "fields_used": ["field1", "field2"],
    "metrics": [
      {"label": "Metric Name", "value": "12.3%", "insight": "What it means"}
    ],
    "visualizations": [
      {"type": "bar|line|pie|donut", "title": "Chart Title", "description": "What it shows"}
    ]
  }
}

Available fields: """ + json.dumps(EMPLOYEE_SCHEMA, indent=2)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "model": "gemini-pro (Vertex AI Preview)"
    }), 200


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        conversation_history = data.get('history', [])
        
        # Build prompt
        full_context = f"{SYSTEM_PROMPT}\n\nUser: {user_message}\n\nAssistant (respond in JSON):"
        
        # Call Gemini
        response = model.generate_content(
            full_context,
            generation_config={
                "max_output_tokens": 2048,
                "temperature": 0.7,
                "top_p": 0.95,
            }
        )
        
        assistant_message = response.text
        
        # Parse JSON
        try:
            if "```json" in assistant_message:
                json_start = assistant_message.find("```json") + 7
                json_end = assistant_message.find("```", json_start)
                assistant_message = assistant_message[json_start:json_end].strip()
            elif "```" in assistant_message:
                json_start = assistant_message.find("```") + 3
                json_end = assistant_message.find("```", json_start)
                assistant_message = assistant_message[json_start:json_end].strip()
            
            dashboard_data = json.loads(assistant_message)
        except:
            dashboard_data = {
                "message": assistant_message,
                "dashboard": None
            }
        
        return jsonify({
            "response": dashboard_data.get("message", assistant_message),
            "dashboard": dashboard_data.get("dashboard"),
            "analysis_type": dashboard_data.get("analysis_type"),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/search-trends', methods=['POST'])
def search_trends():
    try:
        data = request.json
        topic = data.get('topic', '')
        industry = data.get('industry', 'general')
        
        prompt = f"Provide industry benchmarks for {topic} in {industry} industry."
        response = model.generate_content(prompt)
        
        return jsonify({
            "trends": response.text,
            "topic": topic,
            "industry": industry,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "trends": "Trends unavailable",
            "error": str(e)
        }), 200


@app.route('/api/generate-chart-data', methods=['POST'])
def generate_chart_data():
    try:
        data = request.json
        chart_config = data.get('chart_config', {})
        chart_type = chart_config.get('type', 'bar')
        
        if chart_type in ['pie', 'donut']:
            mock_data = {
                "labels": ["Category A", "Category B", "Category C"],
                "datasets": [{"data": [35, 28, 22]}]
            }
        else:
            mock_data = {
                "labels": ["Q1", "Q2", "Q3", "Q4"],
                "datasets": [{"label": "Metric", "data": [65, 72, 68, 81]}]
            }
        
        return jsonify(mock_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
