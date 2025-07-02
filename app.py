from flask import Flask, render_template, request, Response
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
from flask import jsonify
import time
import os

app = Flask(__name__)

active_sessions = {} 

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

    if username in active_sessions:
        return jsonify({"status": "success"})

    options = webdriver.ChromeOptions()
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
            return jsonify({"status": "otp_required"})

        active_sessions[username] = driver
        return jsonify({"status": "success"})

    except Exception as e:
        driver.quit()
        return jsonify({"status": "error", "message": str(e)})

@app.route('/logout', methods=['POST'])
def logout():
    username = request.form['username']
    driver = active_sessions.pop(username, None)
    if driver:
        driver.quit()
        return jsonify({"status": "logged_out"})
    return jsonify({"status": "no_active_session"})
    
def selenium_generator_match_history(url, username, password, game_filter, otp=None, driver=None):
    options = webdriver.ChromeOptions()
    # options.binary_location = "/usr/bin/chromium"
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    

    if driver is None:
        yield "No active session. Please login again.\n"
        return
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
         
            return
        
        yield "OTP verified, continuing to match history...\n"    

    base_url = get_base_url(url)
    yield "Navigating Match History page...\n"
    driver.get(base_url + '/match_history')
    yield "In Match History Page...\n"
  
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

    yield f"\nTotal revenue across all pages: ₹{total_revenue:,.2f}\n"

def selenium_generator_transactions_multiplayer(url, username, password, game_filter, otp=None, driver=None):
    options = webdriver.ChromeOptions()
    # options.binary_location = "/usr/bin/chromium"
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    if driver is None:
        yield "No active session. Please login again.\n"
        return
    wait = WebDriverWait(driver, 15)

    yield "Opening login page...\n"
    driver.get(url)
    wait.until(EC.presence_of_element_located((By.ID, "exampleInputEmail1"))).send_keys(username)
    driver.find_element(By.ID, "txtPassword").send_keys(password + Keys.RETURN)
    time.sleep(2)

    # Handle OTP if needed
    if "otp" in driver.page_source.lower() or driver.find_elements(By.ID, "otp"):
        if otp:
            yield "Submitting OTP...\n"
            otp_input = wait.until(EC.presence_of_element_located((By.ID, "otp")))
            otp_input.send_keys(otp)
            try:
                driver.find_element(By.ID, "submitOTP").click()
            except:
                otp_input.send_keys(Keys.RETURN)
            time.sleep(3)
        else:
            yield "OTP required but not provided.\n"
           
            return

    base_url = get_base_url(url)
    driver.get(base_url + '/transactions')
    yield "On transactions page...\n"
    time.sleep(1)

    # Select game
    dropdown = driver.find_element(By.XPATH, '//*[@id="game_name"]')
    dropdown.click()
    dropdown.send_keys(game_filter)
    dropdown.send_keys(Keys.RETURN)
    time.sleep(5)

    old_rows = driver.find_elements(By.CSS_SELECTOR, 'table#transactions_table tbody tr')

    # Filter Bot players
    bot_filter = driver.find_element(By.XPATH, '//*[@id="user_search"]')
    bot_filter.click()
    print("clicked Bot filter")
    bot_filter.send_keys("Bot")
    bot_filter.send_keys(Keys.RETURN)
    print("Select Bot success")
    if old_rows:
        wait.until(EC.staleness_of(old_rows[0]))  
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table#transactions_table tbody tr')))

    # Identify columns
    headers = driver.find_elements(By.CSS_SELECTOR, 'table#transactions_table thead th')
    bet_idx = win_idx = commission_idx = None
    for i, h in enumerate(headers):
        t = h.text.strip().lower()
        if t == "bet amount": bet_idx = i
        elif t == "win amount": win_idx = i
        elif t == "commission": commission_idx = i

    if bet_idx is None or win_idx is None or commission_idx is None:
        driver.quit()
        yield "Error: required columns not found!\n"
        return

    def get_rows(): return driver.find_elements(By.CSS_SELECTOR, 'table#transactions_table tbody tr')
    def wait_for_reload(old_rows):
        wait.until(EC.staleness_of(old_rows[0]))
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table#transactions_table tbody tr')))

    # Step 1: Bot revenue
    def calc_bot_revenue():
            total_win = 0.0
            total_bet = 0.0
            page = 1
            while True:
                rows = get_rows()
                page_win = 0.0
                page_bet = 0.0
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, 'td')
                    try:
                        bet = float(cols[bet_idx].text.replace(',', '').replace('₹', '').replace('$', ''))
                        win = float(cols[win_idx].text.replace(',', '').replace('₹', '').replace('$', ''))
                        page_bet += bet
                        page_win += win
                    except:
                        pass
                total_win += page_win
                total_bet += page_bet
                yield f"[Bot] Page {page} Bet = ₹{page_bet:,.2f}, Win = ₹{page_win:,.2f}\n"
                nxt = driver.find_element(By.ID, 'transactions_table_next')
                if 'disabled' in nxt.get_attribute('class'):
                    break
                old = rows
                driver.execute_script("arguments[0].click();", nxt)
                wait_for_reload(old)
                page += 1
            return {"win": total_win, "bet": total_bet, "net": total_win - total_bet}

    # Helper to get final return value from generator
    def run_and_capture_result(gen_func):
        result = None
        gen = gen_func()
        try:
            while True:
                msg = next(gen)
                if isinstance(msg, str):
                    yield msg
        except StopIteration as e:
            result = e.value
        return result

    # Run bot revenue calc and capture win/bet/net
    bot_result = yield from run_and_capture_result(calc_bot_revenue)
    bot_win = bot_result['win']
    bot_bet = bot_result['bet']
    bot_revenue = bot_result['net']

    # Step 2: Clear Bot filter
    yield "Refreshing page for commission calculation...\n"
    driver.get(base_url + '/transactions')
    wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="game_name"]')))
    dropdown = driver.find_element(By.XPATH, '//*[@id="game_name"]')
    dropdown.click()
    dropdown.send_keys(game_filter)
    dropdown.send_keys(Keys.RETURN)
    time.sleep(5)

    # Wait for table to reload
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table#transactions_table tbody tr')))

    # Step 3: Calculate commission for all
    def calc_commission_all():
        total_comm = 0.0
        page = 1
        while True:
            rows = get_rows()
            page_comm = 0.0
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, 'td')
                try:
                    comm = float(cols[commission_idx].text.replace(',', '').replace('₹', '').replace('$', ''))
                    page_comm += comm
                except:
                    pass
            total_comm += page_comm
            yield f"Page {page} Commission = ₹{page_comm:,.2f}\n"
            nxt = driver.find_element(By.ID, 'transactions_table_next')
            if 'disabled' in nxt.get_attribute('class'):
                break
            old = rows
            driver.execute_script("arguments[0].click();", nxt)
            wait_for_reload(old)
            page += 1
        return total_comm

    comm_result = yield from run_and_capture_result(calc_commission_all)
    total_commission = comm_result


    total_revenue = bot_revenue + total_commission
    yield f"\n Final Revenue: (Win ₹{bot_win:,.2f} - Bet ₹{bot_bet:,.2f}) + Commission ₹{total_commission:,.2f} = ₹{total_revenue:,.2f} \n"

def selenium_generator_transactions_singleplayer(url, username, password, game_filter, otp=None, driver=None):
    options = webdriver.ChromeOptions()
    # options.binary_location = "/usr/bin/chromium"
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    if driver is None:
        yield "No active session. Please login again.\n"
        return

    wait = WebDriverWait(driver, 15)

    yield "Opening login page...\n"
    driver.get(url)

    wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="exampleInputEmail1"]')))
    driver.find_element(By.XPATH, '//*[@id="exampleInputEmail1"]').send_keys(username)
    driver.find_element(By.XPATH, '//*[@id="txtPassword"]').send_keys(password + Keys.RETURN)
    time.sleep(2)

    if "otp" in driver.page_source.lower() or len(driver.find_elements(By.ID, "otp")) > 0:
        if otp:
            yield "OTP required. Submitting OTP...\n"
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

     # Select game
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

    driver = active_sessions.get(username)
    if not driver:
        return "Session expired or not logged in. Please login again.", 403

    if page_type == 'match_history':
        return Response(selenium_generator_match_history(url, username, password, game_filter, otp, driver),
                        mimetype='text/plain')
    elif page_type == 'transactions':
      game_type = request.form.get('game_type', 'singleplayer')  

    if game_type == 'singleplayer':
        return Response(selenium_generator_transactions_singleplayer(url, username, password, game_filter, otp, driver),
                        mimetype='text/plain')
    elif game_type == 'multiplayer':
        return Response(selenium_generator_transactions_multiplayer(url, username, password, game_filter, otp, driver),
                        mimetype='text/plain')
    else:
        return "Invalid game type selected", 400


@app.route('/get_games', methods=['POST'])
def get_games():
    url = request.json['url']
    username = request.json['username']
    password = request.json['password']
    page_type = request.json['page_type']

    options = webdriver.ChromeOptions()
    # options.binary_location = "/usr/bin/chromium"
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
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)


