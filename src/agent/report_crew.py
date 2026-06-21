# src/agent/report_crew.py
"""
CrewAI role-based agents for generating the Daily Report.

Implements a 3-agent sequential process (Researcher -> Writer -> Reviewer)
to fetch today's metrics from the database, draft a concise narrative,
verify its accuracy, and finally save it to PostgreSQL and broadcast via Slack.
"""

import json
from datetime import date

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

from src.agent.llm import llm
from src.db.database import SessionLocal
from src.db.models import EmailLog, Contact, DailyReport
from src.tools.slack_tools import send_slack_alert


def get_db_metrics() -> str:
    """Queries the database for today's email processing metrics and leads."""
    today = date.today()
    try:
        with SessionLocal() as db:
            # Note: For SQLite/Postgres date comparison in this simplified tool,
            # we check if processed_at or updated_at starts with today's date string
            # or just pull all records from today. 
            emails_today = db.query(EmailLog).filter(
                EmailLog.processed_at >= today
            ).all()
            
            contacts_today = db.query(Contact).filter(
                Contact.updated_at >= today,
                Contact.is_lead == True
            ).all()
            
            total_processed = len(emails_today)
            replied = len([e for e in emails_today if e.classification_action == "reply"])
            leads = len(contacts_today)
            high_priority = len([e for e in emails_today if e.priority == "high"])
            
            data = {
                "date": str(today),
                "total_emails_processed": total_processed,
                "emails_replied_to": replied,
                "high_priority_emails": high_priority,
                "new_leads_found": leads,
                "lead_details": [
                    {"name": c.name, "company": c.company, "email": c.email} 
                    for c in contacts_today
                ]
            }
            return json.dumps(data, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Database query failed: {str(e)}"})


def generate_and_send_daily_report() -> str:
    """
    Orchestrates the CrewAI 3-agent team, saves the result to the DB, 
    and sends a Slack alert.
    """
    # 1. Fetch metrics deterministically in Python to prevent LLM hallucinations
    metrics_json = get_db_metrics()

    writer_agent = Agent(
        role="Report Writer",
        goal="Write a concise 4-sentence daily activity report from the metrics JSON",
        backstory="A clear, concise business writer who summarizes data into actionable executive summaries.",
        llm="gemini/gemini-flash-latest",
        verbose=True,
    )

    reviewer_agent = Agent(
        role="Quality Reviewer",
        goal="Check the report for accuracy against the metrics. If a number is wrong, correct it. Return the final report text only.",
        backstory="A meticulous QA reviewer who ensures narrative reports exactly match the underlying hard data.",
        llm="gemini/gemini-flash-latest",
        verbose=True,
    )

    # 2. Define the Tasks
    task_write = Task(
        description=f"Using these exact metrics: {metrics_json}, draft a concise 4-sentence daily activity report.",
        expected_output="A 4-sentence paragraph summarizing the daily agent activity.",
        agent=writer_agent,
    )

    task_review = Task(
        description="Review the writer's draft against the researcher's JSON data. Correct any factual errors. Output ONLY the final, polished report text.",
        expected_output="The final, fact-checked report text string.",
        agent=reviewer_agent,
    )

    # 3. Create the Crew and Kickoff
    crew = Crew(
        agents=[writer_agent, reviewer_agent],
        tasks=[task_write, task_review],
        process=Process.sequential,
        verbose=True,
    )

    # Crew output from the final task
    crew_output = crew.kickoff()
    final_report_text = str(crew_output)
    
    metrics_dict = None
    try:
        metrics_dict = json.loads(metrics_json)
    except:
        pass

    # 4. Save to PostgreSQL
    try:
        with SessionLocal() as db:
            report_record = DailyReport(
                report_text=final_report_text,
                metrics_json=metrics_dict
            )
            db.add(report_record)
            db.commit()
    except Exception as e:
        print(f"Error saving to DailyReport table: {e}")

    # 5. Send Slack Alert
    try:
        send_slack_alert.invoke({
            "channel": "#ai-employee-agent-alerts",
            "title": "📊 AI Agent Daily Activity Report",
            "message": final_report_text,
            "priority": "low"
        })
    except Exception as e:
        print(f"Error sending Slack alert: {e}")

    return final_report_text
