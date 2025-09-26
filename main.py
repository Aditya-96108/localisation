import os
import time
import re
from typing import List, Dict
from fastapi import FastAPI
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging

from config import client, model, FACEBOOK_USERNAME, FACEBOOK_PASSWORD
from browser_utils import ensure_language, change_app_language, extract_elements, capture_element_screenshot
from image_utils import ssim
from matching_utils import match_elements
from report_utils import generate_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/check/facebook")
async def check_translation():
    base_url = "https://www.facebook.com"
    languages = {
        "english": {"locale": "en_US", "accept_lang": "en-US,en;q=0.9", "lang": "en-US"},
        "spanish": {"locale": "es_ES", "accept_lang": "es-ES,es;q=0.9", "lang": "es"}
    }

    os.makedirs("english", exist_ok=True)
    os.makedirs("spanish", exist_ok=True)
    os.makedirs("data/output/issue_screenshots", exist_ok=True)

    report = {
        "ui_issues": [],
        "overall_ssim": None,
        "report_path": ""
    }
    elements_dict = {}
    screenshots = {}
    serial_counter = 1
    drivers = {}  

    for lang, data in languages.items():
        logger.info(f"Setting Chrome language to {data['lang']} for Facebook")
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=2560,1440")  
        options.add_argument(f"--lang={data['lang']}")
        options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        options.add_experimental_option("prefs", {
            "intl.accept_languages": data['accept_lang']
        })
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        drivers[lang] = driver
        try:
            url = base_url + f"?locale={data['locale']}"
            logger.info(f"Navigating to {url} for {lang}")
            driver.get(url)
            time.sleep(5)

            change_app_language(driver, lang, FACEBOOK_USERNAME, FACEBOOK_PASSWORD)
            driver.get(url)
            time.sleep(5)

            lang_changed = ensure_language(driver, lang)
            if not lang_changed:
                report["ui_issues"].append(f"Failed to confirm {lang} language for Facebook after attempts.")
            time.sleep(3)
            screenshot_path = f"{lang}/facebook_screenshot.png"
            if driver.save_screenshot(screenshot_path) and os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                screenshots[lang] = screenshot_path
                logger.info(f"Screenshot captured and saved to {screenshot_path} for {lang}")
            else:
                report["ui_issues"].append(f"Screenshot capture failed for {lang} on Facebook.")
                logger.warning(f"Screenshot capture failed for {lang} on Facebook")
            elements, serial_counter = extract_elements(driver, lang, serial_counter)
            elements_dict[lang] = elements
            logger.info(f"Extracted {len(elements)} text elements for {lang} on Facebook")
        except Exception as e:
            report["ui_issues"].append(f"Processing error for {lang} on Facebook: {str(e)}")
            logger.error(f"Processing error for {lang} on Facebook: {str(e)}")
        

    if "english" in elements_dict and "spanish" in elements_dict:
        matched_pairs = match_elements(elements_dict["english"], elements_dict["spanish"], model=model)
    else:
        matched_pairs = []
        logger.warning("No elements extracted for matching")

  
    for idx, (eng, spa) in enumerate(matched_pairs, start=1):
        if eng and spa and spa['text'] != "N/A":
            score_dict = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Evaluate if the Spanish text is a precise translation of the English text, preserving meaning, tone, and structure. Output strictly in this format:\nScore (0-1): <float>\nFlag: <Match|Review|Mismatch>\nTranslation Correct: <Yes/No>\nCapitalization Issue: <Yes/No>, <description or none>\nTime Formatting Issue: <Yes/No>, <description or none>\nOther Issue: <description or none>"},
                    {"role": "user", "content": f"English: {eng['text']}\nSpanish: {spa['text']}"}
                ],
                temperature=0.1,
                max_tokens=250
            ).choices[0].message.content.strip()
            score_match = re.search(r"Score \(0-1\): (\d+\.?\d*)", score_dict)
            score = float(score_match.group(1)) if score_match else 0.0
            if score < 0.85 and not spa.get('screenshot_path'):
                driver = drivers.get('spanish')
                if driver and spa.get('element'):
                    screenshot_path = f"data/output/issue_screenshots/issue_{spa['serial']}_spanish_translation.png"
                    spa['screenshot_path'] = capture_element_screenshot(driver, spa['element'], screenshot_path)

    report["report_path"] = generate_report(matched_pairs, client, elements_dict)

    if "english" in screenshots and "spanish" in screenshots:
        img_en = Image.open(screenshots["english"])
        img_es = Image.open(screenshots["spanish"])
        if img_en.size != img_es.size:
            img_es = img_es.resize(img_en.size, Image.LANCZOS)
        overall_ssim = ssim(img_en, img_es)
        report["overall_ssim"] = f"{overall_ssim:.2f}"
        logger.info(f"Overall SSIM: {overall_ssim:.2f}")
        if overall_ssim < 0.85:
            report["ui_issues"].append(f"Significant overall UI differences detected (SSIM: {overall_ssim:.2f}).")

    
    for driver in drivers.values():
        driver.quit()

    return report