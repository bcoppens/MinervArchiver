#!/usr/bin/env python3
import logging
import os
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import Select
import sys

# Set-up the logger.
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S',
                    level=logging.INFO)


def ask_user(question: str) -> str:
    resp = None
    while not resp:
        resp = input(question)
    return resp


def login(driver: WebDriver, username: str, password: str):
    # Load Minerva home.
    driver.get('https://minerva.ugent.be/')

    # Click the login button.
    login_btn = driver.find_element_by_id('btn_logincas')
    login_btn.click()
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: 'login.ugent.be' in d.current_url)

    # Fill in username.
    username_field = driver.find_element_by_id('username')
    username_field.send_keys(username)

    # Fill in password.
    password_field = driver.find_element_by_id('user_pass')
    password_field.send_keys(password)

    # Click authenticate button.
    login_auth_btn = driver.find_element_by_id('wp-submit')
    login_auth_btn.click()
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: 'minerva.ugent.be' in d.current_url)


def get_courses(driver: WebDriver) -> set:
    driver.get("https://minerva.ugent.be/index.php")
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: 'index.php' in d.current_url)

    # Get the courses.
    courses = set()
    links = driver.find_elements_by_tag_name('a')
    for link in links:
        href = link.get_attribute('href')
        if href is not None and 'course_home.php?cidReq=' in href:
            courses.add(link.get_attribute('href'))

    return courses

def get_clean_course_name(course: str, course_name: str):
    course_name_clean = "".join(c for c in course_name if
                                c.isalpha() or c.isdigit() or c == ' ').rstrip()
    return f"{course[course.index('cidReq') + 7:]} - {course_name_clean.lower()}"

def get_base_directory(course: str, course_name: str):
    return os.path.join(out_dir, get_clean_course_name(course, course_name))

def download_documents(driver: WebDriver, course: str):
    # Browse to the home directory.
    driver.get(course)
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: course in d.current_url)

    files = course.replace("course_home", "document")
    driver.get(files)
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: files in d.current_url)

    # Click the zip link.
    links = driver.find_elements_by_tag_name('a')
    ziplink = None
    for link in links:
        href = link.get_attribute('href')
        if href is not None and 'downloadfolder' in href:
            ziplink = href
            break

    if not ziplink:
        logging.error("ZIP-link not found :(")
        exit(1)

    # Determine the course name.
    course_name = None
    for c in driver.find_elements_by_tag_name('h1'):
        if 'minerva' not in str(c.text).lower():
            course_name = c.text

    # Find the file name.
    new_name = f"{get_clean_course_name(course, course_name)}.zip"

    new_path = os.path.join(get_base_directory(course, course_name), "documents")

    Path(new_path).mkdir(parents=True, exist_ok=True)

    new_file = os.path.join(new_path, new_name)

    if os.path.exists(new_file):
        logging.info(f"Already exists {new_name}")
        return

    empties = driver.find_elements_by_class_name('italic')
    for empty in empties:
        if empty.tag_name == 'td' and 'Geen gegevens weer te geven' in empty.text:
            logging.info(f"No files found: {new_name}")
            return

    driver.get(ziplink)

    # Wait for the file to download.
    logging.info("Awaiting file download...")
    out_file = os.path.join(out_dir, 'documents.zip')
    sleep = WebDriverWait(driver, 1800)
    sleep.until(lambda d: os.path.exists(out_file))

    # Rename the file.
    os.rename(out_file, new_file)
    logging.info(f"Saved {new_name}")

# From https://selenium-python.readthedocs.io/waits.html
class element_has_css_class(object):
  """An expectation for checking that an element has a particular css class.

  locator - used to find the element
  returns the WebElement once it has the particular css class
  """
  def __init__(self, locator, css_class):
    self.locator = locator
    self.css_class = css_class

  def __call__(self, driver):
    element = driver.find_element(*self.locator)   # Finding the referenced element
    if self.css_class in element.get_attribute("class"):
        return element
    else:
        return False

def download_student_publications(driver: WebDriver, course: str):
    # Browse to the home directory.
    driver.get(course)
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: course in d.current_url)

    links = driver.find_elements_by_tag_name('a')
    present = False
    for link in links:
        href = link.get_attribute('href')
        if href is not None and 'student_publication' in href:
            color = link.value_of_css_property("color")
            print (color)
            if "rgba(30, 100, 200, 1)" in str(color):
                present = True
                break
    if not present:
        return

    logging.info("Found student publications")

    files = course.replace("course_home/course_home.php", "student_publication/index.php")
    driver.get(files)
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: files in d.current_url)

    # Click the zip link.
    links = driver.find_elements_by_tag_name('input')
    id_link = None
    for link in links:
        id = link.get_attribute('id')
        print (id)
        if id is not None and "select_all_none_actions_top" in id:
            id_link = link
            break

    if not id_link:
        logging.error("id-link not found :(")
        exit(1)

    id_link.click()

    #sleep = WebDriverWait(driver, 10)
    #element = sleep.until(element_has_css_class((By.ID, 'select_all_none_actions'), "multiple_actions_checkbox_checked"))

    selects = driver.find_elements_by_tag_name('select')
    dropdown = None
    for select in selects:
        name = select.get_attribute('name')
        if name is not None and "multiple_actions" in name:
            dropdown = select
            break

    if not dropdown:
        logging.error("dropdown not found, probably a visible student publications without submissions!")
        return

    Select(dropdown).select_by_visible_text("Download")

    inputs = driver.find_elements_by_tag_name('input')
    submit = None
    for input in inputs:
        id = input.get_attribute('id')
        if id is not None and "multiple_actions_submit" in id:
            submit = input
            break

    if not submit:
        logging.error("submit not found :(")
        exit(1)

    submit.click()

    driver.switch_to_alert().accept()

    # These files appear in out_dir/ under the name <CourseCode>-<Name of User>-studentpublications.zip
    # Given that I can't easily redirect these files in Selenium(?), just leave it

def download_dropbox(driver: WebDriver, course: str):
    # Browse to the home directory.
    driver.get(course)
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: course in d.current_url)

    links = driver.find_elements_by_tag_name('a')
    present = False
    for link in links:
        href = link.get_attribute('href')
        if href is not None and 'dropbox' in href:
            color = link.value_of_css_property("color")
            print (color)
            if "rgba(30, 100, 200, 1)" in str(color):
                present = True
                break
    if not present:
        return

    logging.info("Found dropbox")

    files = course.replace("course_home/course_home.php", "dropbox/index.php")
    driver.get(files)
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: files in d.current_url)

    # Click the zip link.
    links = driver.find_elements_by_tag_name('input')
    id_link = None
    for link in links:
        id = link.get_attribute('id')
        print (id)
        if id is not None and "select_all_none_actions_top" in id:
            id_link = link
            break

    if not id_link:
        logging.error("id-link not found :(")
        exit(1)

    id_link.click()

    #sleep = WebDriverWait(driver, 10)
    #element = sleep.until(element_has_css_class((By.ID, 'select_all_none_actions'), "multiple_actions_checkbox_checked"))

    selects = driver.find_elements_by_tag_name('select')
    dropdown = None
    for select in selects:
        name = select.get_attribute('name')
        if name is not None and "multiple_actions" in name:
            dropdown = select
            break

    if not dropdown:
        logging.error("dropdown not found, probably a visible dropbox without submissions!")
        return

    Select(dropdown).select_by_visible_text("Bestand/folder downloaden")

    inputs = driver.find_elements_by_tag_name('input')
    submit = None
    for input in inputs:
        id = input.get_attribute('id')
        if id is not None and "multiple_actions_submit" in id:
            submit = input
            break

    if not submit:
        logging.error("submit not found :(")
        exit(1)

    submit.click()

    driver.switch_to_alert().accept()

    # These files appear in out_dir/ but don't have a uniform name. If there is only one file, this takes the filename
    # of that file, if there are multiple, they are sent to a zip file.
    # Given that I can't easily redirect these files in Selenium(?), just leave it


if __name__ == '__main__':
    # Validate arguments.
    if len(sys.argv) != 2:
        logging.error("Syntax: python3 main.py output_directory")
        exit(1)

    # Parse arguments.
    out_dir = os.path.abspath(sys.argv[1]).rstrip("/") + "/"

    # Get username from user.
    username = ask_user("Username?")
    password = ask_user("Password?")

    # Create a new webdriver.
    logging.info("Booting...")
    prefs = {"download.default_directory": out_dir}

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_experimental_option('prefs', prefs)

    driver = webdriver.Chrome(executable_path="./chromedriver",
                              chrome_options=options)

    logging.info("Authenticating...")
    login(driver, username, password)

    logging.info("Getting courses...")
    courses = get_courses(driver)

    logging.info(f"Found {len(courses)} courses. (They are: {str(courses)})")

    for ci, course in enumerate(courses):
        logging.info(f"Downloading {ci + 1}/{len(courses)}")
        download_documents(driver, course)
        download_student_publications(driver, course)
        download_dropbox(driver, course)

    logging.info("Done!")
