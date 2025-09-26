import os
import pandas as pd
import sqlite3
from typing import List
import logging

from translation_utils import score_translation_pair, backtranslate_fallback

logger = logging.getLogger(__name__)

def generate_report(matched_pairs: List[tuple], client, elements_dict: dict) -> str:
    os.makedirs("data/output", exist_ok=True)
    data = []
    for idx, (eng, spa) in enumerate(matched_pairs, start=1):
        eng_text = eng['text'] if eng else "N/A"
        spa_text = spa['text'] if spa else "N/A"
        eng_rect = eng['rect'] if eng else {}
        spa_rect = spa['rect'] if spa else {}
        eng_screenshot = eng['screenshot_path'] if eng and eng.get('screenshot_path') else "N/A"
        spa_screenshot = spa['screenshot_path'] if spa and spa.get('screenshot_path') else "N/A"
        score_dict = score_translation_pair(client, eng_text, spa_text)
        if score_dict['score'] < 0.85 and spa_text != "N/A":
            back_trans = backtranslate_fallback(client, spa_text)
            if back_trans:
                back_score_dict = score_translation_pair(client, eng_text, back_trans)
                if back_score_dict['score'] > score_dict['score']:
                    score_dict['score'] = back_score_dict['score']
                    score_dict['explanation'] += f"\nBack-translation check (improved score): {back_trans}"
                else:
                    score_dict['explanation'] += f"\nBack-translation check (no improvement): {back_trans}"
        serial = eng['serial'] if eng else (spa['serial'] if spa else idx)
        data.append({
            "Serial": serial,
            "English_Text": eng_text,
            "Spanish_Text": spa_text,
            "English_Rect": str(eng_rect),
            "Spanish_Rect": str(spa_rect),
            "English_Screenshot": eng_screenshot,
            "Spanish_Screenshot": spa_screenshot,
            "Score": score_dict['score'],
            "Flag": score_dict['flag'],
            "Translation_Correct": score_dict['trans_correct'],
            "Capitalization_Issue": score_dict['cap_issue'],
            "Time_Issue": score_dict['time_issue'],
            "Other_Issue": score_dict['other_issue'],
            "Explanation": score_dict['explanation'],
            "Truncated_In_Spanish": spa['is_truncated'] if spa else False
        })
    df = pd.DataFrame(data)
    report_path = "data/output/facebook_translation_report.csv"
    df.to_csv(report_path, index=False)
    db_path = "data/output/facebook_report.db"
    conn = sqlite3.connect(db_path)
    df.to_sql("translation_checks", conn, if_exists="replace", index=False)
    conn.close()
    logger.info(f"Report generated at {report_path}")
    return report_path