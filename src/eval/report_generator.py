import os
from datetime import datetime
from jinja2 import Template

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Accuracy Report</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 40px; }
        .container { max-width: 800px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .summary-box { background: #e8f4f8; border-left: 5px solid #3498db; padding: 20px; margin-bottom: 30px; border-radius: 4px; }
        .metric { font-size: 1.2em; margin: 10px 0; }
        .metric strong { color: #2c3e50; display: inline-block; width: 180px; }
        .success { color: #27ae60; font-weight: bold; }
        .warning { color: #f39c12; font-weight: bold; }
        .failed-cases { margin-top: 30px; }
        .failed-cases ul { list-style-type: none; padding: 0; }
        .failed-cases li { background: #fdf2e9; padding: 10px; margin: 5px 0; border-left: 4px solid #e67e22; border-radius: 3px; }
        .footer { margin-top: 40px; text-align: center; color: #7f8c8d; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Agent Performance Report</h1>
        <div class="summary-box">
            <h2>Weekly Summary</h2>
            <p>Your system is <strong>{{ "%.1f"|format(accuracy_pct) }}%</strong> accurate this week.</p>
        </div>
        
        <h2>Quality Metrics (RAGAS)</h2>
        <div class="metric">
            <strong>Faithfulness:</strong> 
            <span class="{{ 'success' if faithfulness_score >= 0.85 else 'warning' }}">
                {{ "%.2f"|format(faithfulness_score) }}
            </span>
        </div>
        <div class="metric">
            <strong>Answer Relevancy:</strong> 
            <span class="{{ 'success' if relevancy_score >= 0.85 else 'warning' }}">
                {{ "%.2f"|format(relevancy_score) }}
            </span>
        </div>
        <div class="metric">
            <strong>Context Recall:</strong> 
            <span class="{{ 'success' if recall_score >= 0.85 else 'warning' }}">
                {{ "%.2f"|format(recall_score) }}
            </span>
        </div>

        {% if failed_cases %}
        <div class="failed-cases">
            <h2>Cases Requiring Human Review</h2>
            <p>The following test cases failed the expected action classification:</p>
            <ul>
                {% for case_id in failed_cases %}
                <li>Test ID: {{ case_id }}</li>
                {% endfor %}
            </ul>
        </div>
        {% else %}
        <div class="failed-cases">
            <h2>All Cases Passed Classification! 🎉</h2>
        </div>
        {% endif %}

        <div class="footer">
            Generated on {{ date }} <br>
            Powered by Enterprise AI Gateway
        </div>
    </div>
</body>
</html>
"""

def generate_html_report(eval_result, output_dir="d:/My Porjects/ai employee agent/reports"):
    """
    Generates a client-facing HTML report from the evaluation results.
    Saves it to reports/accuracy.html.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    template = Template(HTML_TEMPLATE)
    html_content = template.render(
        accuracy_pct=eval_result.accuracy_pct,
        faithfulness_score=eval_result.faithfulness_score,
        relevancy_score=eval_result.relevancy_score,
        recall_score=eval_result.recall_score,
        failed_cases=eval_result.failed_cases,
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    file_path = os.path.join(output_dir, "accuracy.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return file_path
