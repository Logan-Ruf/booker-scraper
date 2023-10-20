import os
from datetime import date, timedelta, datetime
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytz


class BookerScraper:
    def __init__(self,
                 driver,
                 start_date: date,
                 end_date: date,
                 wait_time=60,
                 date_time_format='%b %-d, %Y  %-I:%M %p',
                 date_format='%m/%d/%Y',
                 download_dir='/Downloads/',
                 export_period=11,
                 destination_dir=None,
                 locations=None,
                 ):
        self.driver = driver
        self.start_date = start_date
        self.end_date = end_date
        self.wait_time = wait_time
        self.date_time_format = date_time_format
        self.date_format = date_format
        self.export_period = timedelta(days=export_period)
        self.download_dir = download_dir
        self.destination_dir = destination_dir
        self.timezone = pytz.timezone('America/Los_Angeles')
        self.locations = locations or {
            'll': {
                'id': '36085',
                'appointments_view_id': 57651,
                'orders_view_id': 57650,
            },
            'cda': {
                'id': '51309',
                'appointments_view_id': 57707,
                'orders_view_id': 57738,
            }
        }
        self.urls = {
            'signin': 'https://signin.booker.com/',
            'locations': 'https://app.secure-booker.com/App/BrandAdmin/Spas/SearchSpas.aspx',
            'customers': 'https://app.secure-booker.com/App/SpaAdmin/Customers/SearchCustomers.aspx',
            'appointments': 'https://app.secure-booker.com/App/SpaAdmin/Appointments/SearchAppointments.aspx',
            'orders': 'https://app.secure-booker.com/App/SpaAdmin/Orders/Orders/SearchOrders.aspx',
        }

    ###############################
    # UTILITY FUNCTIONS
    ###############################
    def wait_for_element(self, query: tuple, timeout: int = None, quit_on_fail: bool = True):
        timeout = timeout or self.wait_time
        try:
            i = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(query)
            )
            return i
        except Exception as e:
            if quit_on_fail:
                self.driver.quit()
                raise e
            else:
                print(f'Element not found for query: {query}')
                return None

    def wait_for_element_to_be_clickable(self, element, timeout=None):
        timeout = timeout or self.wait_time
        print('Waiting for element to be clickable.')
        try:
            i = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(element)
            )
            return i
        except Exception as e:
            self.driver.quit()
            raise e

    def wait_for_loader(self, query, short_wait=None, long_wait=None):
        short_wait = short_wait or self.wait_time / 2
        long_wait = long_wait or self.wait_time
        try:
            WebDriverWait(self.driver, short_wait, poll_frequency=0.1).until(
                EC.presence_of_element_located(query),
            )
            WebDriverWait(self.driver, long_wait).until_not(
                EC.presence_of_element_located(query)
            )
        except Exception as e:
            print('Loader not found')
            raise Exception(e)

    def change_export_view(self, value):
        try:
            view_select = self.wait_for_element((By.ID, 'ctl00_ctl00_content_content_ddlViewing'))
            view_select.click()
            view_select.find_element(By.XPATH, f'//option[@value="{value}"]').click()
            self.wait_for_element((By.XPATH, f'//option[@value="{value}" and @selected="selected"]'))
        except Exception as e:
            print(e)
            raise Exception('Error changing view')

    def get_time_string(self, time_object):
        return time_object.strftime(self.date_time_format).replace('AM', 'am').replace('PM', 'pm')

    def get_date_string(self, time_object):
        return time_object.strftime(self.date_format)

    def get_file_date_string(self, time):
        return time.strftime('%Y-%m-%d')

    def search_for_export_button(self, time):
        time_string = self.get_time_string(time)
        print(f'Searching for export button with time {time_string}')
        if self.wait_for_element((By.XPATH, f"//a[string()='{time_string}']"), quit_on_fail=False):
            print(f'Found export at {time_string}')
            return time_string
        else:
            print(f'Export not found at {time_string}')
            return None

    def get_download_dir_filecount(self):
        files = [file for file in os.listdir(self.download_dir) if 'crdownload' not in file.lower() and 'Chrome' not in file]
        return len(files)

    def wait_until_filecount_reached(self, count: int, timeout: int = None):
        print(f'Waiting for file count to reach {count}')
        timeout = timeout or self.wait_time
        for i in range(timeout):
            if self.get_download_dir_filecount() >= count:
                return True
            sleep(1)
        return False

    def move_file(self, type, location=None, start_date=None, end_date=None):
        # Skip if no destination dir
        if self.destination_dir is None:
            return
        # Validate type
        print(f'Moving {type} file')
        file_types = ['Customer', 'Appointment', 'Order']
        if type not in file_types:
            raise Exception(f'File type must be one of {file_types}')
        # Create subdirectory if it doesn't exist
        sub_dir = os.path.join(self.destination_dir, type)
        if not os.path.exists(sub_dir):
            os.mkdir(sub_dir)
        if location is not None:
            sub_dir = os.path.join(sub_dir, location)
            if not os.path.exists(sub_dir):
                os.mkdir(sub_dir)
        # Set destination file name
        dest_file_name = type
        if start_date:
            dest_file_name += f' {self.get_file_date_string(start_date).replace("/", "_")}'
            if end_date:
                dest_file_name += f'-{self.get_file_date_string(end_date).replace("/", "_")}'
        # Get file name
        file_name = [file for file in os.listdir(self.download_dir) if type in file]
        if len(file_name) == 0:
            raise Exception(f'No file found for type {type}')
        elif len(file_name) > 1:
            raise Exception(f'Multiple files found for type {type}')
        # Move file
        src = os.path.join(self.download_dir, file_name[0])
        dest = os.path.join(sub_dir, f'{dest_file_name}.csv')
        print(f'Moving file {src} to {dest}')
        os.rename(src, dest)

    ###############################
    # NAVIGATION
    ###############################
    def navigate_to_appointments_page(self):
        print('Navigating to appointments page.')
        self.driver.get(self.urls['appointments'])

    def navigate_to_orders_page(self):
        print('Navigating to orders page.')
        self.driver.get(self.urls['orders'])

    def navigate_to_locations_page(self):
        print('Navigating to locations page.')
        self.driver.get(self.urls['locations'])

    def navigate_to_customers_page(self):
        print('Navigating to customers page.')
        self.driver.get(self.urls['customers'])

    def select_location(self, location_code):
        self.navigate_to_locations_page()
        print('Selecting location.')
        location_select = self.wait_for_element((By.XPATH, f"//a[@href='Impersonate.aspx?SpaID={location_code}']"))
        location_select.click()
        sleep(1)

    ###############################
    # AUTHENTICATION
    ###############################
    def account_selection(self, account_name):
        print('Selecting account.')
        self.driver.get(self.urls['signin'])
        account_field = self.wait_for_element((By.ID, 'AccountName'))
        account_field.send_keys(account_name)
        self.driver.find_element(By.XPATH, "//button[@type='submit']").click()

    def user_login(self, username, password):
        print('Logging in.')
        username_field = self.wait_for_element((By.ID, 'Username'))
        password_field = self.driver.find_element(By.ID, 'Password')

        username_field.send_keys(username)
        password_field.send_keys(password)

        self.driver.find_element(By.XPATH, "//button[@type='submit']").click()

    def login(self, account_name, username, password):
        self.account_selection(account_name)
        self.user_login(username, password)

    ###############################
    # CUSTOMERS
    ###############################
    def customers_start_export(self, view_id=57514):
        print('Starting customers export.')
        self.change_export_view(view_id)
        # export button
        self.driver.find_element(By.ID, 'ctl00_ctl00_content_content_btnExport').click()
        start_time = datetime.now(self.timezone) + timedelta(seconds=15)  # Booker seems to round up sometimes. This hits the correct time the first time more often
        print(f'Export started at {self.get_time_string(start_time)}')
        sleep(5)
        ok_button = self.wait_for_element((By.XPATH, '//input[@value="Ok" and @class="xSubmitPrimary"]'),
                                          quit_on_fail=False)
        if ok_button:
            print('Export started, clicking ok.')
            ok_button.click()
            sleep(2)
        else:
            print('Export started, no ok button found.')
        return start_time

    def customers_download_export(self, time):
        time_string = self.get_time_string(time)
        print(f'Looking for export started near {time_string}')

        export_time = self.search_for_export_button(time)
        # Check for race condition
        if export_time is None:
            export_time = self.search_for_export_button(time + timedelta(minutes=1))
        if export_time is None:
            export_time = self.search_for_export_button(time - timedelta(minutes=1))

        if export_time is None:
            raise Exception('Export not found')


        button_text = export_time
        print('Waiting for export to finish')
        sleep(3)
        self.driver.refresh()
        sleep(1)
        export_download_button = None
        for i in range(0, 10):
            export_download_button = self.wait_for_element(
                (By.XPATH, f"//a[string()='{button_text}' and @title='download .csv file']"),
                timeout=60 * 5,
                quit_on_fail=False
            )
            if export_download_button is not None:
                break
            else:
                self.driver.refresh()
                print('Export not found. Refreshing page.')

        if export_download_button is None:
            raise Exception('Customer Export Button not found to be clickable')
        export_download_button.click()
        print('Customer export download started')

    def customer_flow(self, view_id=57514):
        filecount = self.get_download_dir_filecount()

        self.select_location(self.locations['ll']['id'])
        self.navigate_to_customers_page()
        export_time = self.customers_start_export(view_id)
        self.customers_download_export(export_time)
        sleep(1)
        print('Waiting for download to finish')
        if not self.wait_until_filecount_reached(filecount + 1):
            raise Exception('Customer download did not finish in a timely manner')
        print('Customer download finished')
        self.move_file('Customer', start_date=export_time)

    def customer_added_today_flow(self):
        self.customer_flow(59300)

    def customer_added_last_year_flow(self):
        self.customer_flow(59301)

    def customer_added_last_week_flow(self):
        self.customer_flow(59303)


    ###############################
    # APPOINTMENTS
    ###############################
    def appointments_export_chunked(self, start_date, end_date):
        start_string = self.get_date_string(start_date)
        end_string = self.get_date_string(end_date)
        print(f'Exporting appointments from {start_string} to {end_string}')
        self.wait_for_element((By.ID, 'ctl00_ctl00_content_content_txtDate'))
        self.driver.execute_script(f"$('#ctl00_ctl00_content_content_txtDate').val('{start_string} - {end_string}');")
        sleep(0.1)
        self.driver.execute_script("""
            let event = new Event('change');
            document.querySelector('#ctl00_ctl00_content_content_txtDate').dispatchEvent(event);
            """)

        self.wait_for_loader((By.XPATH, '//div[@class="reports-overlay-words"]'))
        self.driver.find_element(By.ID, 'ctl00_ctl00_content_content_btnExport').click()

    def appointments_export(self, location):
        current_time = self.start_date
        while current_time < self.end_date + self.export_period:
            file_count = self.get_download_dir_filecount()
            query_end = current_time + self.export_period - timedelta(days=1)
            self.appointments_export_chunked(current_time, query_end)
            # Wait for file download to show up in directory
            if not self.wait_until_filecount_reached(file_count + 1):
                raise Exception('Appointment download did not finish in a timely manner')
            self.move_file('Appointment', location=location, start_date=current_time, end_date=query_end)
            current_time += self.export_period

    def appointments_flow(self, location, date_type='date_on'):
        self.select_location(location['id'])
        self.navigate_to_appointments_page()

        if date_type == 'date_created':
            value = 'ApptCreatedOn'
            try:
                view_select = self.wait_for_element((By.ID, 'ctl00_ctl00_content_content_ddlDateType'))
                view_select.click()
                view_select.find_element(By.XPATH, f'//option[@value="{value}"]').click()
                self.wait_for_element((By.XPATH, f'//option[@value="{value}" and @selected="selected"]'))
            except Exception as e:
                print(e)
                raise Exception('Error changing view')

        self.change_export_view(location['appointments_view_id'])
        self.appointments_export(location=location['id'])

    ###############################
    # ORDERS
    ###############################
    def orders_export_chunked(self, start_time: date, end_time: date):
        start_string = self.get_date_string(start_time)
        end_string = self.get_date_string(end_time)
        print(f'Exporting orders from {start_string} to {end_string}')
        self.wait_for_element((By.ID, 'ctl00_ctl00_content_content_txtDateCreated'))
        self.driver.execute_script(f"$('#ctl00_ctl00_content_content_txtDateCreated').val('{start_string} - {end_string}');")
        sleep(0.1)
        self.driver.execute_script("""
            let event = new Event('change');
            document.querySelector('#ctl00_ctl00_content_content_txtDateCreated').dispatchEvent(event);
            """)
        sleep(0.2)
        # wait_for_loader(driver, (By.XPATH, '//div[@class="reports-overlay-words"]'))
        self.wait_for_element((By.ID, 'ctl00_ctl00_content_content_btnExport')).click()

    def orders_export(self, location=None):
        current_time = self.start_date
        while current_time < self.end_date + self.export_period:
            file_count = self.get_download_dir_filecount()
            query_end = current_time + self.export_period - timedelta(days=1)
            self.orders_export_chunked(current_time, query_end)
            # Wait for file download to show up in directory
            if not self.wait_until_filecount_reached(file_count + 1, self.wait_time*2):
                raise Exception('Order download did not finish in a timely manner')
            self.move_file('Order', location=location, start_date=current_time, end_date=query_end)
            current_time += self.export_period

    def orders_flow(self, location):
        self.select_location(location['id'])
        self.navigate_to_orders_page()
        self.change_export_view(location['orders_view_id'])
        self.orders_export(location['id'])