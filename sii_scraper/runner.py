import logging

from selenium.common.exceptions import TimeoutException

from sii_scraper.sii_scraper import SiiScraper


class SiiScraperRunner:
    """
    Orquestador principal del scraper SII.

    Coordina la carga de credenciales, el control de progreso, la ejecución del
    scraper web, la limpieza de datos y la sincronización de facturas con MongoDB.
    """

    def __init__(
        self,
        credentials,
        progress_store,
        transformer,
        repository,
        headless: bool = True,
        use_certificate: bool = False,
    ):
        """
        Inicializa el runner con las dependencias necesarias.

        Args:
            credentials: Componente encargado de cargar credenciales SII.
            progress_store: Componente encargado de guardar usuarios procesados.
            transformer: Componente encargado de limpiar y normalizar facturas.
            repository: Repositorio encargado de sincronizar facturas en MongoDB.
            headless: Indica si Selenium debe ejecutarse en modo headless.
            use_certificate: Indica si el scraper debe usar autenticación con certificado.
        """
        self.credentials = credentials
        self.progress_store = progress_store
        self.transformer = transformer
        self.repository = repository
        self.headless = headless
        self.use_certificate = use_certificate
        self.log = logging.getLogger(self.__class__.__name__)

    def run(self, month: str | None = None, year: str | None = None) -> None:
        """
        Ejecuta el proceso completo de scraping y sincronización.

        Carga las credenciales disponibles, omite usuarios ya marcados como
        completados, ejecuta el scraper SII por cada usuario, limpia los datos
        obtenidos, sincroniza las facturas con MongoDB y registra el usuario como
        completado al finalizar correctamente.

        Args:
            month: Mes opcional a consultar en SII.
            year: Año opcional a consultar en SII.

        Returns:
            None
        """
        completed_users = self.progress_store.load_completed_users()
        creds = self.credentials.load_all_credentials()

        if not creds:
            raise RuntimeError(
                "No se encontraron credenciales SII configuradas.")

        self.log.info("Obteniendo datos de facturas desde SII")

        for user, password in creds.items():
            if user in completed_users:
                self.log.info(f"Usuario omitido, ya completado: {user}")
                continue

            self.log.info(f"Scraping facturas para {user}")

            try:
                scraper_kwargs = {
                    "headless": self.headless,
                    "use_certificate": self.use_certificate,
                }

                if month is not None:
                    scraper_kwargs["month"] = month

                if year is not None:
                    scraper_kwargs["year"] = year

                scraper = SiiScraper(
                    user=user,
                    pwd=password,
                    **scraper_kwargs,
                )

                df = scraper.scrape_all()
                df["sii_user"] = user

                df_cleaned = self.transformer.clean_and_normalize(df)

                inserted, updated = self.repository.sync_invoices(df_cleaned)

                self.progress_store.mark_user_completed(user)

                self.log.info(
                    f"Usuario finalizado: {user}. "
                    f"Insertadas: {inserted}, actualizadas: {updated}"
                )

            except TimeoutException:
                self.log.warning(
                    f"Timeout scraping {user}, continuando con el siguiente usuario")
                continue

            except Exception as e:
                self.log.warning(
                    f"Error scraping {user}: {type(e).__name__}: {e}")
                continue

        self.progress_store.clear()
