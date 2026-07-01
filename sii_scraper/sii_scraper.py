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
    HEADERS = [
        "type_purchase", "supplier_id", "supplier_name", "number", "date", "date_accepted", "type", "exent_total", "net_total", "iva", "other_tax", "iva_not",
        "code_iva_not", "total", "total_activo", "iva_activo", "iva_comun", "tax_no_credit", "iva_no_retenido", "type_document_ref", "folio_ref",
        "tabaco_puro", "tabaco_cigarrillos", "tabaco_elaborado", "nce_or_nde", "rut_holding", "status", "doc_type"
    ]

    ACCEPTED_DOCUMENTS = [
        {
            "xpath": "//a[contains(text(),'Factura Electrónica') and @ui-sref]",
            "status": "accepted",
            "doc_type": "invoice",
        },
        {
            "xpath": "//a[contains(text(),'Factura no Afecta o Exenta Electrónica') and @ui-sref]",
            "status": "accepted_exempt",
            "doc_type": "invoice",
        },
        {
            "xpath": "//a[contains(text(),'Nota de Crédito Electrónica') and @ui-sref]",
            "status": "accepted",
            "doc_type": "credit_note",
        }
    ]

    PENDING_DOCUMENTS = [
        {
            "xpath": "//a[@ui-sref and contains(normalize-space(.), 'Factura Electrónica')]",
            "status": "pending",
            "doc_type": "invoice",
        },
        {
            "xpath": "//a[@ui-sref and contains(normalize-space(.), 'Factura no Afecta o Exenta Electrónica')]",
            "status": "pending_exempt",
            "doc_type": "invoice",
        },
        {
            "xpath": "//a[@ui-sref and contains(normalize-space(.), 'Nota de Crédito Electrónica')]",
            "status": "pending",
            "doc_type": "credit_note",
        },
    ]

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

    def _login_and_navigate(self) -> None:
        self.driver.get(
            "https://zeusr.sii.cl//AUT2000/InicioAutenticacion/IngresoRutClave.html?https://misiir.sii.cl/cgi_misii/siihome.cgi")

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

    def _login_and_navigate_with_cert(self) -> None:

        self.driver.get(
            "https://zeusr.sii.cl/AUT2000/InicioAutenticacion/IngresoCertificado.html?https://misiir.sii.cl/cgi_misii/siihome.cgi")

        try:
            self.wait.until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert.accept()
        except TimeoutException:
            self.log.info("No apareció alerta de certificado, continuando.")

    def _navigate_to_purchase_registry(self) -> None:

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

    def _scrape_pending(self, wait, link_xpath: str, status: str, doc_type: str, rut_value: str, all_rows: list) -> None:

        if not self._open_document_section(wait, link_xpath, status, doc_type, rut_value):
            return

        self._scrape_pending_table(rut_value, status, doc_type, all_rows)

        self._go_back(wait)

    def _scrape_section(self, wait, link_xpath: str, status: str, doc_type: str, rut_value: str, all_rows: list) -> None:
        """
        Clicks the link identified by link_xpath, scrapes all rows into all_rows
        tagging them with (rut_value, status, doc_type), then clicks “Volver” to go back.
        """

        if not self._open_document_section(wait, link_xpath, status, doc_type, rut_value):
            return

        self._scrape_table_pages(wait, rut_value, status, doc_type, all_rows)

        self._go_back(wait)

    def _open_document_section(
        self,
        wait,
        link_xpath: str,
        status: str,
        doc_type: str,
        rut_value: str,
    ) -> bool:
        try:
            link_el = wait.until(
                EC.element_to_be_clickable((By.XPATH, link_xpath))
            )
        except TimeoutException:
            self.log.info(
                f"No se encontró link {status} - {doc_type} para RUT {rut_value}, omitiendo."
            )
            return False

        try:
            count_td = link_el.find_element(
                By.XPATH,
                ".//ancestor::td/following-sibling::td[1]",
            )
            count = int(count_td.text.replace(".", "").strip() or 0)
        except (NoSuchElementException, ValueError):
            self.log.warning(
                f"No se pudo leer la cantidad de documentos {doc_type} para RUT {rut_value}, omitiendo."
            )
            return False

        if count <= 0:
            self.log.info(
                f"{doc_type} tiene cantidad {count} para RUT {rut_value}, omitiendo."
            )
            return False

        for attempt in range(1, self.max_retries + 1):
            try:
                wait.until(
                    EC.invisibility_of_element_located(
                        (By.CSS_SELECTOR, "div.modal-backdrop")
                    )
                )

                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    link_el,
                )

                link_el.click()
                break

            except ElementClickInterceptedException:
                self.log.warning(
                    f"Click interceptado en {doc_type}. "
                    f"Intento {attempt}/{self.max_retries}"
                )

                try:
                    modal = self.driver.find_element(By.ID, "alert-modal")
                    modal.find_element(
                        By.CSS_SELECTOR,
                        ".modal-footer .btn-danger",
                    ).click()
                except NoSuchElementException:
                    pass

                wait.until(
                    EC.invisibility_of_element_located(
                        (By.CSS_SELECTOR, "div.modal-backdrop")
                    )
                )
        else:
            self.log.warning(
                f"No se pudo abrir sección {doc_type} para RUT {rut_value}, omitiendo."
            )
            return False

        length_sel = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "select[name='tableCompra_length']")
            )
        )

        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            length_sel,
        )

        Select(length_sel).select_by_value("100")

        return True

    def _go_back(self, wait) -> None:

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

    def _scrape_table_pages(self, wait, rut_value, status, doc_type, all_rows) -> None:

        while True:
            rows = self.driver.find_elements(
                By.CSS_SELECTOR, "#tableCompra tbody tr")

            for tr in rows:
                tds = tr.find_elements(By.TAG_NAME, "td")

                if len(tds) < 2:
                    continue

                try:
                    supplier_link = tds[1].find_element(By.TAG_NAME, "a")
                except NoSuchElementException:
                    self.log.debug("Fila sin link de proveedor, omitiendo.")
                    continue

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

            except Exception as e:
                self.log.debug(
                    f"No se pudo avanzar a la siguiente página: {type(e).__name__}: {e}")
                break

    def _scrape_pending_table(
        self,
        rut_value: str,
        status: str,
        doc_type: str,
        all_rows: list,
    ) -> None:

        for tr in self.driver.find_elements(By.CSS_SELECTOR, "#tableCompra tbody tr"):

            tds = tr.find_elements(By.TAG_NAME, "td")

            if len(tds) < 3:
                continue

            supplier_link = ""

            try:
                supplier_link = tds[1].find_element(By.TAG_NAME, "a")
            except NoSuchElementException:
                try:
                    supplier_link = tds[2].find_element(By.TAG_NAME, "a")
                except NoSuchElementException:
                    self.log.debug("Fila sin link de proveedor, omitiendo.")
                    continue

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

    def _click_pendientes(self, wait) -> None:
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
            self.log.warning(
                "Click interceptado en pestaña Pendientes, usando click por JavaScript")
            self.driver.execute_script("arguments[0].click();", elem)

        wait.until(
            EC.invisibility_of_element_located((By.ID, "esperaDialog"))
        )

    def _dismiss_rut_popup_if_present(self) -> None:
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

    def _wait_for_rut_options(self) -> None:

        for attempt in range(1, self.max_retries + 1):
            try:
                self.wait.until(
                    lambda d: len(
                        d.find_elements(By.CSS_SELECTOR,
                                        "select[name='rut'] option")
                    ) > 2
                )
                return
            except TimeoutException:
                self.log.warning(
                    f"Esperando opciones de RUT. Intento {attempt}/{self.max_retries}"
                )

        raise TimeoutException("No se cargaron las opciones de RUT")

    def _select_period_if_needed(self) -> None:
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

    def _click_consultar(self) -> None:
        consult_btn = self.driver.find_element(
            By.CSS_SELECTOR,
            "form[name='formContribuyente'] button[type='submit']"
        )

        try:
            consult_btn.click()
        except ElementClickInterceptedException:
            self.driver.execute_script(
                "arguments[0].click();", consult_btn)

    def _scrape_selected_rut(self, wait, rut_value: str, all_rows: list) -> None:
        self.log.info(f"Obteniendo facturas para RUT {rut_value!r}")

        self._dismiss_rut_popup_if_present()

        wait.until(
            EC.invisibility_of_element_located((By.ID, "esperaDialog"))
        )

        self._click_consultar()

        for doc in self.ACCEPTED_DOCUMENTS:
            self._scrape_section(
                wait,
                doc["xpath"],
                status=doc["status"],
                doc_type=doc["doc_type"],
                rut_value=rut_value,
                all_rows=all_rows,
            )

        self._click_pendientes(wait)

        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//td[@ng-if=\"(row.rsmnLink)\"]")
                )
            )
        except TimeoutException:
            self.log.warning(
                f"No hay tabla de documentos pendientes para RUT {rut_value}, omitiendo."
            )
            return

        for doc in self.PENDING_DOCUMENTS:
            self._scrape_pending(
                wait,
                doc["xpath"],
                status=doc["status"],
                doc_type=doc["doc_type"],
                rut_value=rut_value,
                all_rows=all_rows,
            )

    def _login(self) -> None:
        if self.use_certificate:
            self._login_and_navigate_with_cert()
        else:
            self._login_and_navigate()

    def _close(self) -> None:
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
            self.log.warning(f"No se pudo cerrar sesión correctamente: {type(e).__name__}: {e}")

        try:
            self.driver.quit()
        except Exception as e:
            self.log.warning(f"No se pudo cerrar el navegador correctamente: {type(e).__name__}: {e}")

    def scrape_all(self) -> pd.DataFrame:

        all_rows = []

        try:
            self._login()

            self._navigate_to_purchase_registry()

            self._wait_for_rut_options()

            rut_select = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "rut")))
            select = Select(rut_select)
            option_count = len(select.options)

            wait = WebDriverWait(self.driver, 10)

            self._select_period_if_needed()

            for idx in range(1, option_count):
                try:

                    rut_select = self.wait.until(
                        EC.element_to_be_clickable((By.NAME, "rut")))

                    sel = Select(rut_select)
                    sel.select_by_index(idx)

                    rut_value = sel.first_selected_option.get_attribute(
                        "value")

                    self._scrape_selected_rut(wait, rut_value, all_rows)

                except TimeoutException as e:
                    self.log.warning(
                        f"Timeout processing RUT index {idx}, continuing: {e}")
                    continue

                except Exception as e:
                    self.log.warning(
                        f"Error processing RUT index {idx}, continuing: {type(e).__name__}: {e}")
                    continue
            
            return pd.DataFrame(all_rows, columns=self.HEADERS, dtype=str)

        except Exception as e:
            self.log.exception(
                f"Fatal scraper error, returning partial data: "
                f"{type(e).__name__}: {e}"
            )

        finally:
            self._close()
        
        return pd.DataFrame(all_rows, columns=self.HEADERS, dtype=str)

    def scrape_one(self, rut) -> pd.DataFrame:

        try:
            self._login()

            self._navigate_to_purchase_registry()

            self._wait_for_rut_options()

            rut_select = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "rut")))

            all_rows = []

            wait = WebDriverWait(self.driver, 10)

            self._select_period_if_needed()

            sel = Select(rut_select)
            sel.select_by_value(rut)

            rut_value = sel.first_selected_option.get_attribute("value")

            self._scrape_selected_rut(wait, rut_value, all_rows)

            return pd.DataFrame(all_rows, columns=self.HEADERS, dtype=str)

        finally:
            self._close()
