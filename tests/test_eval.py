import os
import json
import pytest

from src.eval.ragas_eval import run_evaluation

def load_golden_dataset():
    """Loads the 100+ test cases generated in Step 5.1"""
    # Adjust path if tests are run from a different working directory
    dataset_path = os.path.join(os.path.dirname(__file__), "..", "src", "eval", "golden_dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_agent_accuracy():
    """
    CI/CD Gate: Fails the build if the agent's performance drops below 
    acceptable accuracy and quality thresholds.
    """
    dataset = load_golden_dataset()
    
    # Run the full evaluation pipeline
    result = run_evaluation(dataset)
    
    # 1. Check Hard Classification Accuracy
    # If the LLM starts miscategorizing standard emails, fail the build.
    assert result.accuracy_pct >= 90.0, f"Accuracy {result.accuracy_pct}% is below 90% threshold"
    
    # 2. Check Generation Quality (RAGAS)
    # Ensure draft replies don't hallucinate (Faithfulness)
    assert result.faithfulness_score >= 0.85, f"Faithfulness {result.faithfulness_score} is below 0.85 threshold"
    
    # Ensure classification intent maps logically to the email (Answer Relevancy)
    assert result.relevancy_score >= 0.85, f"Answer Relevancy {result.relevancy_score} is below 0.85 threshold"
