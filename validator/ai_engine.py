import os
import json
from google import genai

class AIEngine:
    def __init__(self):
        # check for env variable
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Error configuring Gemini Client: {e}")
                self.client = None

    def generate_unified_analysis(self, sql_text, existing_violations=None):
        """
        Optimized method: Generates both summary and insights in a ONE single API call.
        Returns dict: { 'summary': str, 'insights': list }
        """
        if not self.client:
            return {
                "summary": self._simulation_summary(),
                "insights": self._simulation_insights()
            }

        try:
            ignore_context = ""
            if existing_violations and len(existing_violations) > 0:
                ignore_context = (
                    "CRITICAL INSTRUCTION: The following issues have ALREADY been detected by static analysis. "
                    "DO NOT report them again. Focus only on performance and pure logic/business intent flaws.\n"
                    "ALREADY FOUND (IGNORE THESE):\n- " + "\n- ".join(existing_violations) + "\n\n"
                )

            prompt = (
                "You are an expert Database Administrator. Perform two tasks on this SQL script:\n"
                "1. Summarize it in plain English for a non-technical manager (under 3 sentences).\n"
                "2. Analyze it for deep Logic errors, Performance bottlenecks, and Best Practices (ignore naming conventions).\n\n"
                f"{ignore_context}"
                "Return the result as a SINGLE VALID JSON object with this exact structure:\n"
                "{\n"
                '  "summary": "The executive summary text...",\n'
                '  "insights": [\n'
                '     { "type": "Performance Risk", "message": "...", "severity": "High", "related_code_snippet": "UPDATE employees..." }\n'
                '  ]\n'
                "}\n"
                "IMPORTANT: In 'related_code_snippet', include a short, unique substring of the SQL code that triggered this insight. This helps me verify where the error is.\n"
                "Do not include markdown code blocks. Just raw JSON.\n\n"
                f"SQL Script:\n{sql_text}"
            )
            
            # Use the new SDK method
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )

            # Access text from the response (SDK v1.0 usually has response.text)
            clean_text = response.text.strip()
            if clean_text.startswith("```"):
                clean_text = clean_text.strip("`")
                if clean_text.startswith("json"):
                    clean_text = clean_text[4:]
            
            data = json.loads(clean_text)
            
            # Defensive normalization
            return {
                "summary": data.get("summary", "**AI Executive Summary**: (Missing)"),
                "insights": data.get("insights", [])
            }

        except Exception as e:
            return {
                "summary": f"**AI Executive Summary**: (Error) {str(e)}",
                "insights": [{
                    "type": "AI Error",
                    "message": f"Failed to analyze logic: {str(e)}",
                    "severity": "Low"
                }]
            }

    # Deprecated single handlers (kept for compatibility or testing)
    def summarize_sql(self, sql_text): 
        return self.generate_unified_analysis(sql_text)['summary']

    def analyze_logic(self, statements, existing_violations=None):
        return self.generate_unified_analysis("\n".join(statements), existing_violations)['insights']

    # ------------------------------------------------------------------
    # Simulation Fallbacks (Keep these so the app works without a key too)
    # ------------------------------------------------------------------
    def _simulation_summary(self):
        return (
            "**AI Executive Summary** (Simulation - No API Key Found): "
            "This script performs a schema migration. "
            "It primarily creates backup tables for data retention, "
            "updates the customer records, and cleans up temporary objects. "
        )

    def _simulation_insights(self):
        return [
            {
                "type": "Simulation Notice",
                "message": "AI is running in simulation mode. Set GEMINI_API_KEY environment variable to get real insights.",
                "severity": "Low"
            },
            {
                "type": "Logic Warning",
                "message": "(Simulated) The `DELETE` statement lacks a clearly defined date range.",
                "severity": "Medium"
            }
        ]
