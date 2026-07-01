import pandas as pd
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException


class SiiScraper:

    DEFAULT_WAIT = 15

    def __init__(self, user: str, pwd: str, headless: bool = False, use_certificate=False, month: str | None = None, year: str | None = None, max_retries: int = 3):

        options = Options()

        self.user = user
        self.pwd = pwd
        self.log = logging.getLogger(self.__class__.__name__)
        self.max_retries = max_retries

        self.use_certificate = use_certificate

        if headless:
            options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        # recommended for Linux
        options.add_argument("--disable-gpu")
        # recommended in many CI systems
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--log-level=3")

        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.fonts": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.password_manager_leak_detection": False,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        }

        options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, self.DEFAULT_WAIT)
        self.month = month
        self.year = year

    def login_and_navigate(self):
        self.driver.get(
            "https://zeusr.sii.cl//AUT2000/InicioAutenticacion/IngresoRutClave.html?https://misiir.sii.cl/cgi_misii/siihome.cgi")

        attempt = 1

        for attempt in range(1, self.max_retries + 1):
            try:
                login_link = WebDriverWait(self.driver, self.wait._timeout).until(
                    EC.element_to_be_clickable((By.ID, "myHref"))
                )
                # scroll into view just in case
                login_link.click()
                break  # success — exit the function
            except TimeoutException:
                self.log.warning(
                    f"Intento {attempt}/{self.max_retries} para hacer click en login_link agotó el tiempo.")
                if attempt < self.max_retries:
                    time.sleep(1)  # give it a moment before retrying
                else:
                    raise

        run_input = self.wait.until(
            EC.element_to_be_clickable((By.ID, "uname"))
        )
        run_input.clear()
        run_input.send_keys(self.user)

        pwd_input = self.wait.until(
            EC.element_to_be_clickable((By.ID, "pword"))
        )
        pwd_input.clear()
        pwd_input.send_keys(self.pwd)

        submit_btn = self.wait.until(
            EC.element_to_be_clickable((By.ID, "login-submit"))
        )
        submit_btn.click()

        services_menu = self.wait.until(
            EC.presence_of_element_located((By.LINK_TEXT, "Servicios online"))
        )
        self.log.info("Menú servicios online")

        actions = ActionChains(self.driver)
        actions.move_to_element(services_menu).click().perform()

        factura_link = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Factura electrónica"))
        )
        self.log.info("Menú factura electrónica")

        # 4) Click it
        factura_link.click()

        accordion_link = self.wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "p.accordion_special a[href='1039-3256.html']"
        )))

        # 2. Click it
        accordion_link.click()

        registro = self.wait.until(EC.element_to_be_clickable((
            By.LINK_TEXT,
            "Ingresar al Registro de Compras y Ventas"
        )))

        registro.click()

        self.log.info("Ingresando al registro de compras y ventas")

    def login_and_navigate_with_cert(self):

        self.driver.get(
            "https://zeusr.sii.cl/AUT2000/InicioAutenticacion/IngresoCertificado.html?https://misiir.sii.cl/cgi_misii/siihome.cgi")

        self.wait.until(EC.alert_is_present())

        alert = self.driver.switch_to.alert
        alert.accept()

        services_menu = self.wait.until(
            EC.presence_of_element_located((By.LINK_TEXT, "Servicios online"))
        )
        self.log.info("Menu servicios online")

        actions = ActionChains(self.driver)
        actions.move_to_element(services_menu).click().perform()

        factura_link = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Factura electrónica"))
        )
        self.log.info("Menu factura electronica")

        # 4) Click it
        factura_link.click()

        accordion_link = self.wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "p.accordion_special a[href='1039-3256.html']"
        )))

        # 2. Click it
        accordion_link.click()

        registro = self.wait.until(EC.element_to_be_clickable((
            By.LINK_TEXT,
            "Ingresar al Registro de Compras y Ventas"
        )))

        registro.click()

        self.log.info("Ingresando al registro de compras y ventas")

    def _scrape_pending(self, wait, link_xpath: str, status: str, doc_type: str, rut_value: str, all_rows: list):

        try:
            link_el = wait.until(
                EC.element_to_be_clickable((By.XPATH, link_xpath))
            )
        except:
            self.log.warning(f"→ No {status} - {doc_type} link for RUT {rut_value}, skipping.")
            return

        try:
            count_td = link_el.find_element(
                By.XPATH,
                ".//ancestor::td/following-sibling::td[1]"
            )
            # strip dots and parse
            count = int(count_td.text.replace(".", "").strip() or 0)
        except (NoSuchElementException, ValueError):
            self.log.warning(f"→ Couldn't read count next to {doc_type} for RUT {rut_value}, skipping.")
            return

        if count <= 0:
            self.log.warning(f"→ {doc_type} count is {count} for RUT {rut_value}, not scraping.")
            return

        for attempt in range(2):
            try:
                # ensure no leftover backdrops
                wait.until(EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "div.modal-backdrop")
                ))
                # scroll into view then click
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", link_el)
                link_el.click()
                break
            except ElementClickInterceptedException:
                self.log.warning("→ Click intercepted by backdrop, retrying…")
                # try to dismiss any open alert-modal
                try:
                    modal = self.driver.find_element(By.ID, "alert-modal")
                    modal.find_element(
                        By.CSS_SELECTOR, ".modal-footer .btn-danger").click()
                except NoSuchElementException:
                    pass
                # then wait a moment for backdrop to disappear
                wait.until(EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "div.modal-backdrop")
                ))
        else:
            self.log.warning(f"→ Failed to click {doc_type} after retry, skipping.")
            return

        length_sel = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "select[name='tableCompra_length']"))
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", length_sel)
        Select(length_sel).select_by_value("100")

        for tr in self.driver.find_elements(By.CSS_SELECTOR, "#tableCompra tbody tr"):

            tds = tr.find_elements(By.TAG_NAME, "td")

            supplier_link = ""
            try:
                supplier_link = tds[1].find_element(By.TAG_NAME, "a")
            except NoSuchElementException:
                supplier_link = tds[2].find_element(By.TAG_NAME, "a")

            supplier_id = supplier_link.text.strip()
            supplier_name = supplier_link.get_attribute("data-original-title")

            row = []

            if (doc_type == "credit_note"):
                row = [
                    tds[0].text.strip(),
                    supplier_id,
                    supplier_name,
                    *[td.text.strip() for td in tds[2:6]],
                    "",
                    *[td.text.strip() for td in tds[6:-1]],
                    0,
                    0,
                    0,
                    tds[-1].text.strip(),
                    rut_value,
                    status,
                    doc_type
                ]

            else:

                row = [
                    tds[1].text.strip(),
                    supplier_id,
                    supplier_name,
                    *[td.text.strip() for td in tds[3:7]],
                    "",
                    *[td.text.strip() for td in tds[7:-1]],
                    0,
                    0,
                    0,
                    tds[-1].text.strip(),
                    rut_value,
                    status,
                    doc_type
                ]

            all_rows.append(row)

        volver_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[ng-click='doTheBack()']")
            )
        )

        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            volver_btn,
        )

        try:
            volver_btn.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", volver_btn)

    def _scrape_section(self, wait, link_xpath: str, status: str, doc_type: str, rut_value: str, all_rows: list):
        """
        Clicks the link identified by link_xpath, scrapes all rows into all_rows
        tagging them with (rut_value, status, doc_type), then clicks “Volver” to go back.
        """

        try:
            link_el = wait.until(
                EC.element_to_be_clickable((By.XPATH, link_xpath))
            )
        except:
            self.log.warning(
                f"→ No {status} - {doc_type} link for RUT {rut_value}, skipping.")
            return

        try:
            count_td = link_el.find_element(
                By.XPATH,
                ".//ancestor::td/following-sibling::td[1]"
            )
            # strip dots and parse
            count = int(count_td.text.replace(".", "").strip() or 0)
        except (NoSuchElementException, ValueError):
            self.log.warning(
                f"→ Couldn't read count next to {doc_type} for RUT {rut_value}, skipping.")
            return

        if count <= 0:
            self.log.warning(
                f"→ {doc_type} count is {count} for RUT {rut_value}, not scraping.")
            return

        attempt = 1
        for attempt in range(1, self.max_retries + 1):
            try:
                # ensure no leftover backdrops
                wait.until(EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "div.modal-backdrop")
                ))
                # scroll into view then click
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", link_el)
                link_el.click()
                break
            except ElementClickInterceptedException:
                self.log.warning("→ Click intercepted by backdrop, retrying…")
                # try to dismiss any open alert-modal
                try:
                    modal = self.driver.find_element(By.ID, "alert-modal")
                    modal.find_element(
                        By.CSS_SELECTOR, ".modal-footer .btn-danger").click()
                except NoSuchElementException:
                    pass
                # then wait a moment for backdrop to disappear
                wait.until(EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "div.modal-backdrop")
                ))
                attempt += 1
        else:
            self.log.info(f"→ Failed to click {doc_type} after retry, skipping.")
            return

        length_sel = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "select[name='tableCompra_length']"))
        )

        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", length_sel)
        Select(length_sel).select_by_value("100")

        self._scrape_table_pages(wait, rut_value, status, doc_type, all_rows)

        volver_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[ng-click='doTheBack()']")
            )
        )

        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            volver_btn,
        )

        try:
            volver_btn.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", volver_btn)

    def _scrape_table_pages(self, wait, rut_value, status, doc_type, all_rows):
        while True:
            rows = self.driver.find_elements(
                By.CSS_SELECTOR, "#tableCompra tbody tr")

            for tr in rows:
                tds = tr.find_elements(By.TAG_NAME, "td")
                if not tds:
                    continue

                supplier_link = tds[1].find_element(By.TAG_NAME, "a")
                supplier_id = supplier_link.text.strip()
                supplier_name = supplier_link.get_attribute(
                    "data-original-title")

                row = [
                    tds[0].text.strip(),
                    supplier_id,
                    supplier_name,
                    *[td.text.strip() for td in tds[2:]],
                    rut_value,
                    status,
                    doc_type,
                ]

                all_rows.append(row)

            try:
                next_li = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "#tableCompra_paginate li.paginate_button.next"
                )

                classes = next_li.get_attribute("class") or ""
                if "disabled" in classes:
                    break

                current_first_row = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "#tableCompra tbody tr"
                ).text

                next_a = next_li.find_element(By.TAG_NAME, "a")
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", next_a
                )
                self.driver.execute_script("arguments[0].click();", next_a)

                wait.until(
                    lambda d: d.find_element(
                        By.CSS_SELECTOR, "#tableCompra tbody tr"
                    ).text != current_first_row
                )

            except Exception:
                break

    def _click_pendientes(self, wait):
        """
        Wait for the “Pendientes” tab to be clickable, then click it.
        """

        wait.until(
            EC.invisibility_of_element_located((By.ID, "esperaDialog"))
        )

        pendientes_locator = (
            By.XPATH,
            "//a[@ui-sref='compraPendiente' and normalize-space(strong/text())='Pendientes']"
        )

        elem = wait.until(EC.presence_of_element_located(pendientes_locator))
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", elem)

        wait.until(EC.element_to_be_clickable(pendientes_locator))
        try:
            elem.click()
        except ElementClickInterceptedException:
            self.log.warning("Click interceptado en pestaña Pendientes, usando click por JavaScript")
            self.driver.execute_script("arguments[0].click();", elem)

        wait.until(
            EC.invisibility_of_element_located((By.ID, "esperaDialog"))
        )

    def _dismiss_rut_popup_if_present(self):
        try:
            popup_btn = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#alert-modal .modal-footer button")
                )
            )
            self.driver.execute_script("arguments[0].click();", popup_btn)

            WebDriverWait(self.driver, 5).until(
                EC.invisibility_of_element_located((By.ID, "alert-modal"))
            )

        except TimeoutException:
            pass

    def scrape_all(self) -> pd.DataFrame:

        all_rows = []
        headers = [
            "type_purchase", "supplier_id", "supplier_name", "number", "date", "date_accepted", "type", "exent_total", "net_total", "iva", "other_tax", "iva_not",
            "code_iva_not", "total", "total_activo", "iva_activo", "iva_comun", "tax_no_credit", "iva_no_retenido", "type_document_ref", "folio_ref",
            "tabaco_puro", "tabaco_cigarrillos", "tabaco_elaborado", "nce_or_nde", "rut_holding", "status", "doc_type"
        ]

        try:
            if self.use_certificate:
                self.login_and_navigate_with_cert()
            else:
                self.login_and_navigate()

            try:
                self.wait.until(lambda d: len(
                    d.find_elements(By.CSS_SELECTOR,
                                    "select[name='rut'] option")
                ) > 2)

            except TimeoutException:
                self.wait.until(lambda d: len(
                    d.find_elements(By.CSS_SELECTOR,
                                    "select[name='rut'] option")
                ) > 2)

            # Convertir esto a un for loop
            rut_select = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "rut")))
            select = Select(rut_select)
            option_count = len(select.options)

            wait = WebDriverWait(self.driver, 10)

            if (self.month):
                periodoMes = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "periodoMes")))
                month_sel = Select(periodoMes)
                month_sel.select_by_value(self.month)

            if (self.year):

                periodoAnyo = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'select[ng-model="periodoAnho"]')))
                year_sel = Select(periodoAnyo)
                year_sel.select_by_value(self.year)

            for idx in range(1, option_count):
                try:

                    rut_select = self.wait.until(
                        EC.element_to_be_clickable((By.NAME, "rut")))

                    select = Select(rut_select)

                    sel = Select(rut_select)
                    # index 0 = placeholder, 1 = first RUT, 2 = second RUT
                    sel.select_by_index(idx)
                    # time.sleep(5)

                    rut_value = sel.first_selected_option.get_attribute(
                        "value")
                    # (or use .text if you prefer the visible text)
                    self.log.info(f"Obteniendo facturas para RUT {rut_value!r}")

                    self._dismiss_rut_popup_if_present()

                    wait.until(
                        EC.invisibility_of_element_located(
                            (By.ID, "esperaDialog"))
                    )

                    # 2) Click “Consultar”
                    consult_btn = self.driver.find_element(
                        By.CSS_SELECTOR,
                        "form[name='formContribuyente'] button[type='submit']"
                    )

                    try:
                        consult_btn.click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script(
                            "arguments[0].click();", consult_btn)

                    self._scrape_section(
                        wait,
                        "//a[contains(text(),'Factura Electrónica') and @ui-sref]",
                        status="accepted",
                        doc_type="invoice",
                        rut_value=rut_value,
                        all_rows=all_rows
                    )

                    self._scrape_section(
                        wait,
                        "//a[contains(text(),'Factura no Afecta o Exenta Electrónica') and @ui-sref]",
                        status="accepted_exempt",
                        doc_type="invoice",
                        rut_value=rut_value,
                        all_rows=all_rows
                    )

                    self._scrape_section(
                        wait,
                        "//a[contains(text(),'Nota de Crédito Electrónica') and @ui-sref]",
                        status="accepted",
                        doc_type="credit_note",
                        rut_value=rut_value,
                        all_rows=all_rows
                    )

                    self._click_pendientes(wait)

                    try:
                        wait.until(EC.presence_of_element_located(
                            (By.XPATH, "//td[@ng-if=\"(row.rsmnLink)\"]")
                        ))
                    except TimeoutException:
                        self.log.warning(
                            f"→ No pending‐documents table for RUT {rut_value}, skipping.")
                        continue

                    self._scrape_pending(
                        wait,
                        "//a[@ui-sref and contains(normalize-space(.), 'Factura Electrónica')]",
                        status="pending",
                        doc_type="invoice",
                        rut_value=rut_value,
                        all_rows=all_rows,
                    )

                    self._scrape_pending(
                        wait,
                        "//a[@ui-sref and contains(normalize-space(.), 'Factura no Afecta o Exenta Electrónica')]",
                        status="pending_exempt",
                        doc_type="invoice",
                        rut_value=rut_value,
                        all_rows=all_rows,
                    )

                    self._scrape_pending(
                        wait,
                        "//a[@ui-sref and contains(normalize-space(.), 'Nota de Crédito Electrónica')]",
                        status="pending",
                        doc_type="credit_note",
                        rut_value=rut_value,
                        all_rows=all_rows,
                    )

                except TimeoutException as e:
                    self.log.warning(
                        f"Timeout processing RUT index {idx}, continuing: {e}")
                    continue

                except Exception as e:
                    self.log.warning(
                        f"Error processing RUT index {idx}, continuing: {type(e).__name__}: {e}")
                    continue

        except Exception as e:
            self.log.exception(
                f"Fatal scraper error, returning partial data: "
                f"{type(e).__name__}: {e}"
            )

        finally:
            try:
                logout_link = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//a[@href='https://zeusr.sii.cl/cgi_AUT2000/autTermino.cgi']",
                        )
                    )
                )
                logout_link.click()
            except Exception as e:
                self.log.warning(f"Could not logout cleanly: {type(e).__name__}: {e}")

            try:
                self.driver.quit()
            except Exception as e:
                self.log.warning(
                    f"Could not quit driver cleanly: {type(e).__name__}: {e}")

        return pd.DataFrame(all_rows, columns=headers, dtype=str)

    def scrape_one(self, rut) -> pd.DataFrame:

        try:
            self.login_and_navigate()

            try:
                self.wait.until(lambda d: len(
                    d.find_elements(By.CSS_SELECTOR,
                                    "select[name='rut'] option")
                ) > 2)

            except TimeoutException:
                self.wait.until(lambda d: len(
                    d.find_elements(By.CSS_SELECTOR,
                                    "select[name='rut'] option")
                ) > 2)

            # Convertir esto a un for loop
            rut_select = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "rut")))
            select = Select(rut_select)
            option_count = len(select.options)

            all_rows = []
            headers = [
                "type_purchase", "supplier_id", "supplier_name", "number", "date", "date_accepted", "type", "exent_total", "net_total", "iva", "other_tax", "iva_not",
                "code_iva_not", "total", "total_activo", "iva_activo", "iva_comun", "tax_no_credit", "iva_no_retenido", "type_document_ref", "folio_ref",
                "tabaco_puro", "tabaco_cigarrillos", "tabaco_elaborado", "nce_or_nde", "rut_holding", "status", "doc_type"
            ]

            wait = WebDriverWait(self.driver, 10)

            sel = Select(rut_select)
            sel.select_by_value(rut)

            rut_value = sel.first_selected_option.get_attribute("value")
            self.log.info(f"Obteniendo facturas para RUT {rut_value!r}")

            self.wait.until(
                EC.invisibility_of_element_located((By.ID, "esperaDialog"))
            )

            # 2) Click “Consultar”
            consult_btn = self.driver.find_element(
                By.CSS_SELECTOR,
                "form[name='formContribuyente'] button[type='submit']"
            )

            try:
                consult_btn.click()
            except ElementClickInterceptedException:
                self.driver.execute_script(
                    "arguments[0].click();", consult_btn)

            self._scrape_section(
                wait,
                "//a[contains(text(),'Factura Electrónica') and @ui-sref]",
                status="accepted",
                doc_type="invoice",
                rut_value=rut_value,
                all_rows=all_rows
            )

            self._scrape_section(
                wait,
                "//a[contains(text(),'Factura no Afecta o Exenta Electrónica') and @ui-sref]",
                status="accepted_exempt",
                doc_type="invoice",
                rut_value=rut_value,
                all_rows=all_rows
            )

            self._scrape_section(
                wait,
                "//a[contains(text(),'Nota de Crédito Electrónica') and @ui-sref]",
                status="accepted",
                doc_type="credit_note",
                rut_value=rut_value,
                all_rows=all_rows
            )

            self._click_pendientes(wait)

            try:
                wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//td[@ng-if=\"(row.rsmnLink)\"]")
                ))
            except TimeoutException:
                self.log.warning(
                    f"→ No pending‐documents table for RUT {rut_value}, skipping.")
                return

            self._scrape_pending(
                wait,
                "//a[@ui-sref and contains(normalize-space(.), 'Factura Electrónica')]",
                status="pending",
                doc_type="invoice",
                rut_value=rut_value,
                all_rows=all_rows,
            )

            self._scrape_pending(
                wait,
                "//a[@ui-sref and contains(normalize-space(.), 'Factura no Afecta o Exenta Electrónica')]",
                status="pending_exempt",
                doc_type="invoice",
                rut_value=rut_value,
                all_rows=all_rows,
            )

            self._scrape_pending(
                wait,
                "//a[@ui-sref and contains(normalize-space(.), 'Nota de Crédito Electrónica')]",
                status="pending",
                doc_type="credit_note",
                rut_value=rut_value,
                all_rows=all_rows,
            )

            if all_rows:
                df = pd.DataFrame(all_rows, columns=headers, dtype=str)
                return df
        finally:
            self.driver.quit()
