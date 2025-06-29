from flask import Flask, render_template, request, Response
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
import time
import os

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

def get_base_url(full_url):
    parsed = urlparse(full_url)
    return f"{parsed.scheme}://{parsed.netloc}"

@app.route('/check_login', methods=['POST'])
def check_login():
    url = request.form['url']
    username = request.form['username']
    password = request.form['password']
    options = webdriver.ChromeOptions()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)

    wait = WebDriverWait(driver, 10)

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.ID, "exampleInputEmail1"))).send_keys(username)
        driver.find_element(By.ID, "txtPassword").send_keys(password + Keys.RETURN)
        time.sleep(2)

        if "otp" in driver.page_source.lower() or driver.find_elements(By.ID, "otp"): 
            driver.quit()
            return jsonify({"status": "otp_required"})

        driver.quit()
        return jsonify({"status": "success"})

    except Exception as e:
        driver.quit()
        return jsonify({"status": "error", "message": str(e)})
    
def selenium_generator_match_history(url, username, password, game_filter, otp=None):
    options = webdriver.ChromeOptions()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    yield "Opening login page...\n"
    driver.get(url)

    wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="exampleInputEmail1"]')))
    driver.find_element(By.XPATH, '//*[@id="exampleInputEmail1"]').send_keys(username)
    driver.find_element(By.XPATH, '//*[@id="txtPassword"]').send_keys(password + Keys.RETURN)
    time.sleep(2)  

    if "otp" in driver.page_source.lower() or len(driver.find_elements(By.ID, "otp")) > 0:
        if otp:
            yield "OTP required. Submitting OTP from form...\n"
            otp_input = wait.until(EC.presence_of_element_located((By.ID, "otp")))
            if otp_input.is_displayed() and otp_input.is_enabled():
                otp_input.send_keys(otp)
            else:
                yield "OTP input not interactable, skipping OTP submission.\n"
            
            try:
                submit_btn = driver.find_element(By.ID, "submitOTP")  
                submit_btn.click()
            except:
                otp_input.send_keys(Keys.RETURN)
            
            time.sleep(3)
        else:
            yield "OTP required but not provided. Please enter OTP in the form.\n"
            driver.quit()
            return
        
        yield "OTP verified, continuing to match history...\n"    

    base_url = get_base_url(url)
    yield "Match History page...\n"
    driver.get(base_url + '/match_history')
    yield "In Match History Page\n"
  
    wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="gameName_search"]')))
    print("Found match_history Drop Down")
    dropdown_input = driver.find_element(By.XPATH, '//*[@id="gameName_search"]')
    time.sleep(30)
    dropdown_input.click()
    time.sleep(5)

    old_rows = driver.find_elements(By.CSS_SELECTOR, 'table#transactions_table tbody tr')

    dropdown_input.send_keys(game_filter)
    dropdown_input.send_keys(Keys.RETURN)

    wait.until(EC.staleness_of(old_rows[0]))
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table#transactions_table tbody tr')))

    def get_revenue_column_index(driver):
        headers = driver.find_elements(By.CSS_SELECTOR, 'table#transactions_table thead th')
        for i, header in enumerate(headers):
            if header.text.strip().lower() == "revenue":
                return i
        raise Exception("'Revenue' column not found!")

    revenue_index = get_revenue_column_index(driver)

    def extract_revenue_from_page():
        revenues = []
        rows = driver.find_elements(By.CSS_SELECTOR, 'table#transactions_table tbody tr')
        for idx, row in enumerate(rows, start=1):
            try:
                cols = row.find_elements(By.TAG_NAME, 'td')
                if len(cols) > revenue_index:
                    revenue_text = cols[revenue_index].text.strip()
                    revenue = float(revenue_text.replace(',', '').replace('₹', '').replace('$', ''))
                    revenues.append(revenue)
            except Exception:
                pass
        return revenues, rows

    total_revenue = 0.0
    page = 1

    while True:
        yield f'Processing page {page}...\n'

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table#transactions_table tbody tr')))
        
        revenues, rows = extract_revenue_from_page()
        page_revenue = sum(revenues)
        total_revenue += page_revenue
        yield f"Page {page} revenue: ₹{page_revenue:,.2f}\n"

        try:
            next_button = driver.find_element(By.ID, 'transactions_table_next')
            next_button_class = next_button.get_attribute('class')

            if 'disabled' in next_button_class:
                yield "Reached the last page.\n"
                break

            driver.execute_script("arguments[0].click();", next_button)

            wait.until(EC.staleness_of(rows[0]))
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table#transactions_table tbody tr')))
            
            page += 1
            time.sleep(1)

        except Exception as e:
            yield f"Failed at page {page}: {e}\n"
            break

    driver.quit()
    yield f"\nTotal revenue across all pages: ₹{total_revenue:,.2f}\n"

def selenium_generator_transactions(url, username, password, game_filter, otp=None):
    options = webdriver.ChromeOptions()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)


    wait = WebDriverWait(driver, 15)

    yield "Opening login page...\n"
    driver.get(url)

    wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="exampleInputEmail1"]')))
    driver.find_element(By.XPATH, '//*[@id="exampleInputEmail1"]').send_keys(username)
    driver.find_element(By.XPATH, '//*[@id="txtPassword"]').send_keys(password + Keys.RETURN)
    time.sleep(2)

    if "otp" in driver.page_source.lower() or len(driver.find_elements(By.ID, "otp")) > 0:
        if otp:
            yield "OTP required. Submitting OTP from form...\n"
            otp_input = wait.until(EC.presence_of_element_located((By.ID, "otp")))
            if otp_input.is_displayed() and otp_input.is_enabled():
                otp_input.send_keys(otp)
            else:
                yield "OTP input not interactable, skipping OTP submission.\n"

            try:
                submit_btn = driver.find_element(By.ID, "submitOTP")  # Adjust if needed
                submit_btn.click()
            except:
                otp_input.send_keys(Keys.RETURN)

            time.sleep(3)
        else:
            yield "OTP required but not provided. Please enter OTP in the form.\n"
            driver.quit()
            return

    base_url = get_base_url(url)

    yield "Navigating to transactions page...\n"
    driver.get(base_url + '/transactions')
    yield "In transaction page..."
    time.sleep(1)

    dropdown_input = driver.find_element(By.XPATH, '//*[@id="game_name"]')
    dropdown_input.click()
    time.sleep(1)

    old_rows = driver.find_elements(By.CSS_SELECTOR, 'table#transactions_table tbody tr')

    dropdown_input.send_keys(game_filter)
    dropdown_input.send_keys(Keys.RETURN)

    wait.until(EC.staleness_of(old_rows[0]))
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table#transactions_table tbody tr')))

    headers = driver.find_elements(By.CSS_SELECTOR, 'table#transactions_table thead th')
    bet_idx = win_idx = None
    for i, header in enumerate(headers):
        text = header.text.strip().lower()
        if text == "bet amount":
            bet_idx = i
        elif text == "win amount":
            win_idx = i
    if bet_idx is None or win_idx is None:
        yield "Could not find Bet Amount or Win Amount columns\n"
        driver.quit()
        return

    def extract_revenue():
        revenues = []
        rows = driver.find_elements(By.CSS_SELECTOR, 'table#transactions_table tbody tr')
        for idx, row in enumerate(rows, start=1):
            try:
                cols = row.find_elements(By.TAG_NAME, 'td')
                bet_text = cols[bet_idx].text.strip().replace(',', '').replace('₹', '').replace('$', '')
                win_text = cols[win_idx].text.strip().replace(',', '').replace('₹', '').replace('$', '')
                bet = float(bet_text)
                win = float(win_text)
                revenue = bet - win
                revenues.append(revenue)
            except Exception:
                pass
        return revenues, rows

    total_revenue = 0.0
    page = 1

    while True:
        yield f'Processing page {page}...\n'
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table#transactions_table tbody tr')))
        revenues, rows = extract_revenue()
        page_revenue = sum(revenues)
        total_revenue += page_revenue
        yield f"Page {page} revenue: ₹{page_revenue:,.2f}\n"

        try:
            next_button = driver.find_element(By.ID, 'transactions_table_next')
            next_button_class = next_button.get_attribute('class')

            if 'disabled' in next_button_class:
                yield "Reached the last page.\n"
                break

            driver.execute_script("arguments[0].click();", next_button)
            wait.until(EC.staleness_of(rows[0]))
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table#transactions_table tbody tr')))
            page += 1
            time.sleep(1)

        except Exception as e:
            yield f"Failed at page {page}: {e}\n"
            break

    driver.quit()
    yield f"\nTotal revenue across all pages: ₹{total_revenue:,.2f}\n"


@app.route('/calculate', methods=['POST'])
def calculate():
    url = request.form['url']
    username = request.form['username']
    password = request.form['password']
    game_filter = request.form['game_filter']
    page_type = request.form['page_type']
    otp = request.form.get('otp', None)

    if page_type == 'match_history':
        return Response(selenium_generator_match_history(url, username, password, game_filter, otp),
                        mimetype='text/plain')
    elif page_type == 'transactions':
        return Response(selenium_generator_transactions(url, username, password, game_filter, otp),
                        mimetype='text/plain')

    else:
        return "Invalid page type selected", 400

from flask import jsonify

@app.route('/get_games', methods=['POST'])
def get_games():
    url = request.json['url']
    username = request.json['username']
    password = request.json['password']
    page_type = request.json['page_type']

    options = webdriver.ChromeOptions()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.ID, "exampleInputEmail1"))).send_keys(username)
        driver.find_element(By.ID, "txtPassword").send_keys(password + Keys.RETURN)
        time.sleep(2)

        base_url = get_base_url(url)

        if page_type == "match_history":
            driver.get(base_url + "/match_history")
        else:
            driver.get(base_url + "/transactions")


        wait.until(EC.presence_of_element_located((By.ID, "gameName_search")))
        dropdown = driver.find_element(By.ID, "gameName_search")
        dropdown.click()
        time.sleep(1)

        options_elements = driver.find_elements(By.XPATH, '//ul[@id="gameName_search_listbox"]/li')
        games = [opt.text.strip() for opt in options_elements if opt.text.strip()]
        driver.quit()
        return jsonify({"games": games})

    except Exception as e:
        driver.quit()
        return jsonify({"error": str(e)}), 500


# if __name__ == '__main__':
#     app.run(debug=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
