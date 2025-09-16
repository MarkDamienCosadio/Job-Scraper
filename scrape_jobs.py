

import pandas as pd
import time
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Set up undetected Chrome WebDriver

options = uc.ChromeOptions()
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-blink-features=AutomationControlled')
driver = uc.Chrome(options=options)

# --- Scroll to load all job cards ---
def scroll_to_load_all_jobs(driver, pause_time=5, max_attempts=40):
	last_height = driver.execute_script("return document.body.scrollHeight")
	attempts = 0
	while attempts < max_attempts:
		# Lazy scroll: scroll in increments to trigger loading
		for frac in [0.25, 0.5, 0.75, 1.0]:
			driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{frac});")
			time.sleep(0.5)
		driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
		time.sleep(pause_time)
		new_height = driver.execute_script("return document.body.scrollHeight")
		if new_height == last_height:
			time.sleep(3)
			new_height = driver.execute_script("return document.body.scrollHeight")
			if new_height == last_height:
				break
			last_height = new_height
		else:
			last_height = new_height
		attempts += 1
	print(f"Scrolled {attempts} times to load all job cards.")
try:
	url = "https://hiring.cafe/?searchState=%7B%22searchQuery%22%3A%22marketing+director%22%2C%22dateFetchedPastNDays%22%3A14%2C%22locations%22%3A%5B%7B%22id%22%3A%22ZhY1yZQBoEtHp_8UErzY%22%2C%22types%22%3A%5B%22administrative_area_level_1%22%5D%2C%22address_components%22%3A%5B%7B%22long_name%22%3A%22New+York%22%2C%22short_name%22%3A%22NY%22%2C%22types%22%3A%5B%22administrative_area_level_1%22%5D%7D%2C%7B%22long_name%22%3A%22United+States%22%2C%22short_name%22%3A%22US%22%2C%22types%22%3A%5B%22country%22%5D%7D%5D%2C%22formatted_address%22%3A%22New+York%2C+United+States%22%2C%22population%22%3A19274244%2C%22workplace_types%22%3A%5B%5D%2C%22options%22%3A%7B%22flexible_regions%22%3A%5B%22anywhere_in_country%22%2C%22anywhere_in_continent%22%2C%22anywhere_in_world%22%5D%7D%7D%5D%7D"
	driver.get(url)
	time.sleep(5)

	# Scroll to load all job cards before scraping
	scroll_to_load_all_jobs(driver)

	# Click the first job card, wait for dialog/modal, then click 'Full View' link with correct URL
	from selenium.webdriver.common.action_chains import ActionChains
	job_cards = WebDriverWait(driver, 10).until(
		EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.relative.flex.flex-col.items-start.w-full.rounded-x-lg.rounded-t-lg'))
	)
	if job_cards:
		for idx, card in enumerate(job_cards):
			try:
				# Scroll the card into view before interacting
				driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", card)
				time.sleep(0.5)
				actions = ActionChains(driver)
				actions.move_to_element(card).pause(0.5).click(card).perform()
				print(f"Clicked job card {idx+1}, waiting for dialog...")
				# Wait for dialog/modal to appear
				try:
					dialog = WebDriverWait(driver, 10).until(
						EC.presence_of_element_located((By.CSS_SELECTOR, '[role="dialog"], [aria-modal="true"]'))
					)
					print("Dialog/modal appeared. Looking for 'Full View' link with job URL...")
					# Find the header and click the 'Full View' link inside it
					header = WebDriverWait(driver, 10).until(
						EC.visibility_of_element_located((By.CSS_SELECTOR, 'header.chakra-modal__header'))
					)
					try:
						# Find the 'Full View' anchor by its text
						full_view_link = header.find_element(
							By.XPATH,
							".//a[span[text()='Full View'] and starts-with(@href, 'https://hiring.cafe/job/')]")
						time.sleep(1.5)
						full_view_link.click()
						print(f"Clicked 'Full View' link: {full_view_link.get_attribute('href')}")
						# Switch to the new tab
						time.sleep(2)  # Wait for tab to open
						driver.switch_to.window(driver.window_handles[-1])
						print("Switched to new tab for data extraction.")
						# --- Extract job data from the new tab below ---
						job_data = {}
						job_data['url'] = driver.current_url
						try:
							job_title = driver.find_element(By.CSS_SELECTOR, 'h2.font-extrabold.text-3xl.text-gray-800.mb-4').text
						except Exception:
							job_title = ''
						job_data['job title'] = job_title
						try:
							company = driver.find_element(By.CSS_SELECTOR, 'span.text-xl.font-semibold.text-gray-700.flex-none').text
							if company.startswith('@ '):
								company = company[2:]
							elif company.startswith('@'):
								company = company[1:]
						except Exception:
							company = ''
						job_data['company'] = company
						try:
							salary = driver.find_element(By.XPATH, "//span[contains(@class, 'rounded') and contains(@class, 'font-bold') and contains(text(), '/yr')]").text
						except Exception:
							salary = ''
						if not salary or salary.strip() == '':
							salary = 'N/A'
						job_data['salary'] = salary						
						try:
							job_position = driver.find_element(By.XPATH, "//span[contains(@class, 'rounded') and contains(@class, 'font-bold') and text()='Full Time']").text
						except Exception:
							job_position = ''
						job_data['Job position'] = job_position
						try:
							remote = driver.find_element(By.XPATH, "//span[contains(@class, 'rounded') and contains(@class, 'font-bold') and text()='Remote']").text
							job_data['Remote'] = 'Yes'
						except Exception:
							job_data['Remote'] = 'No'
						try:
							responsibilities = driver.find_element(By.XPATH, "//div[contains(@class, 'flex') and contains(@class, 'flex-col') and .//span[contains(text(), 'Responsibilities:')]]/span[2]").text
						except Exception:
							responsibilities = ''
						job_data['Responsibilities'] = responsibilities
						try:
							requirements = driver.find_element(By.XPATH, "//div[contains(@class, 'flex') and contains(@class, 'flex-col') and contains(@class, 'space-y-3') and .//span[contains(@class, 'font-bold') and contains(text(), 'Requirements Summary:')]]/span[2]").text
						except Exception:
							requirements = ''
						job_data['Requirements Summary'] = requirements
						try:
							tools = driver.find_element(By.XPATH, "//div[contains(@class, 'flex') and contains(@class, 'flex-col') and contains(@class, 'space-y-3') and .//span[contains(@class, 'font-bold') and contains(text(), 'Technical Tools Mentioned:')]]/span[2]").text
						except Exception:
							tools = ''
						job_data['Technical Tools Mentioned'] = tools
						# Save only job data to CSV (no log/debug messages)
						job_data_upper = {k.upper(): v for k, v in job_data.items()}
						if 'APPLY LAZY SCROLLING...' in job_data_upper.values():
							pass  # Do not save log/debug messages
						else:
							try:
								existing = pd.read_csv('jobs.csv')
								df = pd.concat([existing, pd.DataFrame([job_data_upper])], ignore_index=True)
							except Exception:
								df = pd.DataFrame([job_data_upper])
							df.to_csv('jobs.csv', index=False, na_rep='N/A')
							print('Job data extracted and saved to jobs.csv')
						# Close the job tab and switch back to main tab
						driver.close()
						driver.switch_to.window(driver.window_handles[0])
						# Close any open dialog on the main tab
						try:
							header = WebDriverWait(driver, 5).until(
								EC.visibility_of_element_located((By.CSS_SELECTOR, 'header.chakra-modal__header'))
							)
							close_btns = header.find_elements(By.CSS_SELECTOR, r'button.rounded-lg.p-2.text-black.hover\:bg-gray-200.flex-none.outline-none')
							if close_btns:
								close_btns[-1].click()
								print('Closed dialog box using last "X" button.')
							else:
								print('No close button found.')
						except Exception as e:
							print(f'Could not close dialog box: {e}')
					except Exception as e:
						print(f"Could not find 'Full View' link: {e}")
						anchors = header.find_elements(By.TAG_NAME, 'a')
						print(f"Found {len(anchors)} anchor(s) in header:")
						for a in anchors:
							print(a.get_attribute('outerHTML'))
				except Exception as e:
					print(f"Dialog/modal or 'Full View' link did not appear: {e}")
			except Exception as e:
				print(f"Found job card but could not click: {e}")
	else:
		print("No job cards found.")
finally:
	driver.quit()
