import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

def score_translation_pair(client, eng_text: str, spa_text: str) -> Dict:
    if not eng_text or not spa_text:
        return {
            'score': 0.0,
            'flag': 'Mismatch',
            'trans_correct': 'No',
            'cap_issue': 'No, none',
            'time_issue': 'No, none',
            'other_issue': '',
            'explanation': 'Missing text in pair.'
        }
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Evaluate if the Spanish text is a precise translation of the English text, preserving meaning, tone, and structure. Check for capitalization errors, time/date formatting mismatches, truncations, and other issues. Output strictly in this format:\nScore (0-1): <float>\nFlag: <Match|Review|Mismatch>\nTranslation Correct: <Yes/No>\nCapitalization Issue: <Yes/No>, <description or none>\nTime Formatting Issue: <Yes/No>, <description or none>\nOther Issue: <description or none>"},
                {"role": "user", "content": f"English: {eng_text}\nSpanish: {spa_text}"}
            ],
            temperature=0.1,
            max_tokens=250
        )
        output = response.choices[0].message.content.strip()
        score_match = re.search(r"Score \(0-1\): (\d+\.?\d*)", output)
        flag_match = re.search(r"Flag: (Match|Review|Mismatch)", output)
        trans_match = re.search(r"Translation Correct: (Yes|No)", output)
        cap_match = re.search(r"Capitalization Issue: (Yes|No), (.*)", output)
        time_match = re.search(r"Time Formatting Issue: (Yes|No), (.*)", output)
        other_match = re.search(r"Other Issue: (.*)", output)
        return {
            'score': float(score_match.group(1)) if score_match else 0.0,
            'flag': flag_match.group(1) if flag_match else 'Mismatch',
            'trans_correct': trans_match.group(1) if trans_match else 'No',
            'cap_issue': cap_match.group(0) if cap_match else 'No, none',
            'time_issue': time_match.group(0) if time_match else 'No, none',
            'other_issue': other_match.group(1).strip() if other_match else '',
            'explanation': output
        }
    except Exception as e:
        logger.error(f"LLM scoring error: {str(e)}")
        return {
            'score': 0.0,
            'flag': 'Mismatch',
            'trans_correct': 'No',
            'cap_issue': 'No, none',
            'time_issue': 'No, none',
            'other_issue': '',
            'explanation': f"Error during LLM evaluation: {str(e)}"
        }

def backtranslate_fallback(client, spa_text: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Provide an accurate English back-translation of the Spanish text, maintaining original meaning and structure."},
                {"role": "user", "content": spa_text}
            ],
            temperature=0.0,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Back-translation error: {str(e)}")
        return ""