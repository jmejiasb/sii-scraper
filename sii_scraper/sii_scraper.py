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
    """
    Clase encargada de obtener facturas de compra desde el portal del SII.

    Automatiza el inicio de sesión, la navegación hacia el Registro de Compras y
    Ventas, la selección de RUTs asociados, la consulta de documentos aceptados y
    pendientes, y la construcción de un DataFrame crudo con la información obtenida.

    Esta clase solo realiza scraping web y no limpia datos ni interactúa con la base
    de datos.
    """

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
        """
        Inicializa el scraper SII y configura el navegador Selenium.

        Args:
            user: Usuario o RUT utilizado para iniciar sesión en SII.
            pwd: Contraseña asociada al usuario SII.
            headless: Indica si Chrome debe ejecutarse sin interfaz gráfica.
            use_certificate: Indica si se debe usar el flujo de ingreso con certificado.
            month: Mes opcional a consultar en el Registro de Compras y Ventas.
            year: Año opcional a consultar en el Registro de Compras y Ventas.
            max_retries: Cantidad máxima de reintentos para operaciones puntuales.
        """

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
        """
        Inicia sesión en SII usando Clave Unica.

        Abre la página de autenticación, selecciona el ingreso con clave tributaria,
        ingresa las credenciales y envía el formulario de inicio de sesión.

        Returns:
            None
        """

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
        """
        Inicia sesión en SII usando certificado digital.

        Abre la página de autenticación con certificado, acepta la alerta del navegador
        si aparece y continúa el flujo de ingreso.

        Returns:
            None
        """

        self.driver.get(
            "https://zeusr.sii.cl/AUT2000/InicioAutenticacion/IngresoCertificado.html?https://misiir.sii.cl/cgi_misii/siihome.cgi")

        try:
            self.wait.until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert.accept()
        except TimeoutException:
            self.log.info("No apareció alerta de certificado, continuando.")

    def _navigate_to_purchase_registry(self) -> None:
        """
        Navega desde el menú principal del SII hasta el Registro de Compras y Ventas.

        Ingresa al menú de servicios online, selecciona Factura Electrónica y abre la
        opción correspondiente al Registro de Compras y Ventas.

        Returns:
            None
        """

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
        """
        Procesa una sección de documentos pendientes.

        Abre la sección indicada, extrae las filas de la tabla de documentos pendientes y
        vuelve a la vista anterior al finalizar.

        Args:
            wait: Instancia de WebDriverWait utilizada para esperas explícitas.
            link_xpath: XPath del enlace de la sección a procesar.
            status: Estado que se asignará a los documentos obtenidos.
            doc_type: Tipo de documento que se asignará a los documentos obtenidos.
            rut_value: RUT de la empresa actualmente seleccionada.
            all_rows: Lista donde se acumulan las filas obtenidas.

        Returns:
            None
        """

        if not self._open_document_section(wait, link_xpath, status, doc_type, rut_value):
            return

        self._scrape_pending_table(rut_value, status, doc_type, all_rows)

        self._go_back(wait)

    def _scrape_section(self, wait, link_xpath: str, status: str, doc_type: str, rut_value: str, all_rows: list) -> None:
        """
        Procesa una sección de documentos aceptados.

        Abre la sección indicada, extrae todas las páginas de la tabla de documentos y
        vuelve a la vista anterior al finalizar.

        Args:
            wait: Instancia de WebDriverWait utilizada para esperas explícitas.
            link_xpath: XPath del enlace de la sección a procesar.
            status: Estado que se asignará a los documentos obtenidos.
            doc_type: Tipo de documento que se asignará a los documentos obtenidos.
            rut_value: RUT de la empresa actualmente seleccionada.
            all_rows: Lista donde se acumulan las filas obtenidas.

        Returns:
            None
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
        """
        Abre una sección de documentos si contiene registros disponibles.

        Busca el enlace de la sección, lee la cantidad de documentos asociada, omite la
        sección si no tiene registros y realiza el clic con reintentos cuando es
        necesario. Al abrir la tabla, configura la cantidad de filas visibles en 100.

        Args:
            wait: Instancia de WebDriverWait utilizada para esperas explícitas.
            link_xpath: XPath del enlace de la sección.
            status: Estado del documento utilizado para logs.
            doc_type: Tipo de documento utilizado para logs.
            rut_value: RUT de la empresa actualmente seleccionada.

        Returns:
            bool: True si la sección fue abierta correctamente, False si debe omitirse.
        """

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
                    f"Click interceptado en {doc_type}. Intento {attempt}/{self.max_retries}"
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
        """
        Vuelve desde una tabla de documentos a la vista anterior.

        Busca el botón Volver, lo lleva al centro de la pantalla y realiza el clic,
        usando JavaScript como respaldo si el clic normal es interceptado.

        Args:
            wait: Instancia de WebDriverWait utilizada para esperas explícitas.

        Returns:
            None
        """

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
        """
        Extrae documentos desde una tabla paginada.

        Lee las filas visibles de la tabla de compras, agrega los documentos obtenidos a
        la lista acumuladora y avanza por las páginas disponibles hasta llegar al final.

        Args:
            wait: Instancia de WebDriverWait utilizada para esperas explícitas.
            rut_value: RUT de la empresa actualmente seleccionada.
            status: Estado que se asignará a los documentos obtenidos.
            doc_type: Tipo de documento que se asignará a los documentos obtenidos.
            all_rows: Lista donde se acumulan las filas obtenidas.

        Returns:
            None
        """

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
        """
        Extrae documentos desde la tabla de documentos pendientes.

        Lee las filas visibles de la tabla de compras pendientes, obtiene los datos del
        proveedor y construye las filas con la estructura esperada según el tipo de
        documento.

        Args:
            rut_value: RUT de la empresa actualmente seleccionada.
            status: Estado que se asignará a los documentos obtenidos.
            doc_type: Tipo de documento que se asignará a los documentos obtenidos.
            all_rows: Lista donde se acumulan las filas obtenidas.

        Returns:
            None
        """

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
        Abre la pestaña de documentos pendientes.

        Espera a que desaparezca el indicador de carga, ubica la pestaña Pendientes y la
        abre, usando JavaScript como respaldo si el clic normal es interceptado.

        Args:
            wait: Instancia de WebDriverWait utilizada para esperas explícitas.

        Returns:
            None
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
        """
        Cierra el popup asociado al cambio de RUT si aparece.

        Busca brevemente el modal de alerta del SII y lo cierra si está presente. Si el
        popup no aparece, continúa sin realizar ninguna acción.

        Returns:
            None
        """

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
        """
        Espera a que se carguen las opciones de RUT disponibles.

        Reintenta la espera hasta que el selector de RUT tenga opciones suficientes para
        procesar empresas asociadas al usuario autenticado.

        Returns:
            None

        Raises:
            TimeoutException: Si las opciones de RUT no se cargan después de los reintentos.
        """

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
        """
        Selecciona el mes y/o año de consulta si fueron definidos.

        Si el scraper fue inicializado con month o year, selecciona esos valores en los
        controles del Registro de Compras y Ventas.

        Returns:
            None
        """

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
        """
        Ejecuta la consulta para el RUT seleccionado.

        Busca el botón Consultar del formulario y realiza el clic, usando JavaScript como
        respaldo si el clic normal es interceptado.

        Returns:
            None
        """

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
        """
        Procesa todos los documentos disponibles para el RUT seleccionado.

        Cierra popups si aparecen, ejecuta la consulta, procesa las secciones de
        documentos aceptados, abre la pestaña de pendientes y procesa las secciones de
        documentos pendientes disponibles.

        Args:
            wait: Instancia de WebDriverWait utilizada para esperas explícitas.
            rut_value: RUT de la empresa actualmente seleccionada.
            all_rows: Lista donde se acumulan las filas obtenidas.

        Returns:
            None
        """

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
        """
        Ejecuta el flujo de inicio de sesión correspondiente.

        Usa el ingreso con certificado si use_certificate está activo; de lo contrario,
        usa el ingreso con usuario y contraseña.

        Returns:
            None
        """
        if self.use_certificate:
            self._login_and_navigate_with_cert()
        else:
            self._login_and_navigate()

    def _close(self) -> None:
        """
        Cierra la sesión del SII y libera el navegador.

        Intenta cerrar sesión desde el portal y luego cerrar el WebDriver, registrando
        advertencias si alguna de las acciones falla.

        Returns:
            None
        """

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
            self.log.warning(
                f"No se pudo cerrar sesión correctamente: {type(e).__name__}: {e}")

        try:
            self.driver.quit()
        except Exception as e:
            self.log.warning(
                f"No se pudo cerrar el navegador correctamente: {type(e).__name__}: {e}")

    def scrape_all(self) -> pd.DataFrame:
        """
        Obtiene documentos para todos los RUTs disponibles del usuario autenticado.

        Inicia sesión, navega al Registro de Compras y Ventas, espera las opciones de
        RUT, selecciona el periodo si corresponde y procesa cada RUT disponible. Si
        ocurre un error general, retorna los datos parciales obtenidos hasta ese momento.

        Returns:
            pd.DataFrame: DataFrame crudo con los documentos obtenidos desde SII.
        """

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
        """
        Obtiene documentos para un RUT específico.

        Inicia sesión, navega al Registro de Compras y Ventas, selecciona el periodo si
        corresponde, selecciona el RUT indicado y procesa sus documentos aceptados y
        pendientes.

        Args:
            rut: RUT específico que se desea consultar.

        Returns:
            pd.DataFrame: DataFrame crudo con los documentos obtenidos para el RUT indicado.
        """

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
