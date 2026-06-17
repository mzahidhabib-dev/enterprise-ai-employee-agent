# src/security/pii.py
"""
PII Detection and Redaction utility using Microsoft Presidio.

Scans text for sensitive entities (e.g., PHONE_NUMBER, CREDIT_CARD) and
replaces them with tokens (e.g., [PHONE_NUMBER]) before the text is sent
to the LLM.
"""

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

class PIIRedactor:
    def __init__(self):
        # Initializes presidio components (requires spacy en_core_web_lg to be installed)
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.entities = ["PHONE_NUMBER", "CREDIT_CARD", "EMAIL_ADDRESS", "PERSON", "LOCATION", "US_SSN"]

    def redact(self, text: str) -> tuple[str, list[dict]]:
        """
        Runs the analyzer on text and anonymizes found entities using a replace operator.
        
        Returns:
            tuple: (redacted_text, list_of_found_entities)
        """
        if not text:
            return text, []
            
        analyzer_results = self.analyzer.analyze(text=text, entities=self.entities, language='en')
        
        operators = {
            entity_type: OperatorConfig("replace", {"new_value": f"[{entity_type}]"}) 
            for entity_type in self.entities
        }
        
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,
            operators=operators
        )
        
        found_entities = [
            {"entity_type": res.entity_type, "start": res.start, "end": res.end, "score": res.score}
            for res in analyzer_results
        ]
        
        return anonymized_result.text, found_entities

# Singleton instance to be used across nodes
pii_redactor = PIIRedactor()
