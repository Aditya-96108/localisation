import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import io
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def ensure_language(driver, target_lang: str) -> bool:
    known_texts = {
        "english": ["log in", "create new account", "forgot password?", "connect with friends"],
        "spanish": ["iniciar sesión", "crear una cuenta", "¿has olvidado la contraseña?", "facebook te ayuda"]
    }[target_lang]
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            page_source = driver.page_source.lower()
            if any(text.lower() in page_source for text in known_texts):
                logger.info(f"Language confirmed as {target_lang} for Facebook")
                return True
            logger.warning(f"Language not detected for {target_lang} on Facebook, attempting to switch (attempt {attempt + 1})")
            footer_links = driver.find_elements(By.CSS_SELECTOR, "a[role='link'], a")
            target_link_texts = ["english"] if target_lang == "english" else ["español", "spanish"]
            for link in footer_links:
                link_text = link.text.strip().lower()
                if any(t.lower() in link_text for t in target_link_texts):
                    link.click()
                    time.sleep(3)
                    driver.refresh()
                    time.sleep(3)
                    break
            else:
                logger.warning(f"No suitable language link found for {target_lang} on Facebook attempt {attempt + 1}")
        except Exception as e:
            logger.error(f"Error during language assurance for {target_lang} on Facebook attempt {attempt + 1}: {e}")
        time.sleep(2)
    logger.error(f"Failed to ensure {target_lang} language for Facebook after {max_attempts} attempts")
    return False

def change_app_language(driver, target_lang: str, username: str, password: str):
    wait = WebDriverWait(driver, 20)
    try:
        logger.info("Logging in to Facebook")
        driver.find_element(By.ID, "email").send_keys(username)
        driver.find_element(By.ID, "pass").send_keys(password)
        driver.find_element(By.NAME, "login").click()
        time.sleep(10)
        logger.info("Logged in successfully")

        logger.info("Opening account menu")
        account_menu_xpath = "//div[@aria-label='Account' or @aria-label='Cuenta' or @aria-label='Your profile' or @aria-label='Tu perfil' or @role='button' and .//svg[@viewBox='0 0 16 16']]"
        account_menu = wait.until(EC.element_to_be_clickable((By.XPATH, account_menu_xpath)))
        account_menu.click()
        time.sleep(3)

        logger.info("Clicking Settings & Privacy")
        settings_privacy_xpath = "//span[normalize-space(text())='Settings & privacy' or normalize-space(text())='Configuración y privacidad']"
        settings_privacy = wait.until(EC.element_to_be_clickable((By.XPATH, settings_privacy_xpath)))
        settings_privacy.click()
        time.sleep(3)

        logger.info("Clicking Language")
        language_xpath = "//span[normalize-space(text())='Language' or normalize-space(text())='Idioma']"
        language = wait.until(EC.element_to_be_clickable((By.XPATH, language_xpath)))
        language.click()
        time.sleep(5)

        logger.info("Clicking Edit for Facebook language")
        edit_button_xpath = "//div[contains(text(), 'Facebook language') or contains(text(), 'Idioma de Facebook')]//following-sibling::*//div[@role='button' and (contains(text(), 'Edit') or contains(text(), 'Editar'))] | //div[contains(text(), 'Facebook language') or contains(text(), 'Idioma de Facebook')]//a[contains(text(), 'Edit') or contains(text(), 'Editar')]"
        edit_button = wait.until(EC.element_to_be_clickable((By.XPATH, edit_button_xpath)))
        edit_button.click()
        time.sleep(3)

        logger.info("Searching and selecting language")
        lang_input_xpath = "//input[@aria-label='Search languages' or @aria-label='Buscar idiomas' or @placeholder[contains(., 'Search') or contains(., 'Buscar')]]"
        lang_input = wait.until(EC.presence_of_element_located((By.XPATH, lang_input_xpath)))
        lang_name = "English (US)" if target_lang == "english" else "Español"
        lang_input.send_keys(lang_name)
        time.sleep(2)
        lang_option_xpath = f"//span[normalize-space(text())='{lang_name}']"
        lang_option = wait.until(EC.element_to_be_clickable((By.XPATH, lang_option_xpath)))
        lang_option.click()
        time.sleep(3)

        logger.info("Saving changes")
        save_button_xpath = "//div[@role='button' and (normalize-space(text())='Save Changes' or normalize-space(text())='Guardar cambios')] | //button[normalize-space(text())='Save Changes' or normalize-space(text())='Guardar cambios']"
        save_button = wait.until(EC.element_to_be_clickable((By.XPATH, save_button_xpath)))
        save_button.click()
        time.sleep(10)
        logger.info(f"Account language changed to {lang_name} successfully")

        logger.info("Logging out")
        account_menu = wait.until(EC.element_to_be_clickable((By.XPATH, account_menu_xpath)))
        account_menu.click()
        time.sleep(2)
        logout_xpath = "//span[normalize-space(text())='Log Out' or normalize-space(text())='Cerrar sesión']"
        logout_button = wait.until(EC.element_to_be_clickable((By.XPATH, logout_xpath)))
        logout_button.click()
        time.sleep(5)
        logger.info("Logged out successfully")
    except Exception as e:
        logger.error(f"Error during app language change: {str(e)}")
        driver.save_screenshot(f"debug_{target_lang}_error.png")
        with open(f"debug_{target_lang}_error.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.info(f"Debug screenshot and page source saved for {target_lang}")

def get_element_rect(el):
    location = el.location
    size = el.size
    return {'x': location['x'], 'y': location['y'], 'width': size['width'], 'height': size['height']}

def capture_element_screenshot(driver, element, output_path: str, padding: int = 20):
    try:
        rect = get_element_rect(element)
        screenshot = driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(screenshot))
        left = max(0, rect['x'] - padding)
        top = max(0, rect['y'] - padding)
        right = min(img.width, rect['x'] + rect['width'] + padding)
        bottom = min(img.height, rect['y'] + rect['height'] + padding)
        cropped_img = img.crop((left, top, right, bottom))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cropped_img.save(output_path, quality=95)  # High-quality PNG
        logger.info(f"Screenshot saved for element at {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error capturing element screenshot: {str(e)}")
        return None

def extract_elements(driver, language: str, serial_counter: int) -> List[Dict]:
    elements = []
    try:
        els = driver.find_elements(By.CSS_SELECTOR, "*")
        for el in els:
            if el.is_displayed() and el.size['height'] > 0 and el.size['width'] > 0:
                text = el.text.strip()
                placeholder = el.get_attribute("placeholder") or ""
                aria_label = el.get_attribute("aria-label") or ""
                title = el.get_attribute("title") or ""
                combined_text = text or placeholder or aria_label or title
                if combined_text:
                    rect = get_element_rect(el)
                    is_truncated = driver.execute_script(
                        "return arguments[0].scrollWidth > arguments[0].clientWidth || arguments[0].scrollHeight > arguments[0].clientHeight;",
                        el
                    )
                    screenshot_path = None
                    if is_truncated:
                        screenshot_path = capture_element_screenshot(
                            driver, el, f"data/output/issue_screenshots/issue_{serial_counter}_{language}_truncation.png"
                        )
                    elements.append({
                        'text': combined_text,
                        'rect': rect,
                        'is_truncated': is_truncated,
                        'tag': el.tag_name,
                        'element': el,
                        'serial': serial_counter,
                        'screenshot_path': screenshot_path
                    })
                    serial_counter += 1
        return elements, serial_counter
    except Exception as e:
        logger.error(f"Element extraction error: {e}")
        return [], serial_counter