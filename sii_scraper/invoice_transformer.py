import pandas as pd

class InvoiceTransformer:
    """
    Clase encargada de limpiar y normalizar las facturas obtenidas desde SII.

    Recibe el DataFrame crudo generado por el scraper web, conserva las columnas
    necesarias, normaliza textos, transforma fechas a UTC, convierte montos a
    enteros y deja los datos listos para ser sincronizados con MongoDB.

    Esta clase no realiza scraping ni operaciones contra la base de datos.
    """
    def clean_and_normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpia y normaliza el DataFrame de facturas del SII.

        Selecciona las columnas utilizadas por el sistema, normaliza campos de texto,
        convierte fechas desde la zona horaria de Chile a UTC, transforma montos a
        enteros y estandariza el tipo de pago.

        Args:
            df: DataFrame crudo retornado por el scraper SII.

        Returns:
            pd.DataFrame: DataFrame limpio y normalizado, listo para guardarse en MongoDB.
        """

        df = df.copy()

        df = df[[
            "supplier_id", "supplier_name", "number", "date", "date_accepted",
            "type", "exent_total", "net_total", "iva", "other_tax",
            "total", "rut_holding", "status", "doc_type"
        ]]

        cols = ["supplier_id", "supplier_name", "type", "status", "doc_type"]

        df[cols] = (
            df[cols]
            .fillna("")
            .apply(lambda s: s.str.replace(".", "", regex=False)
                .str.lower())
        )

        df["supplier_id"] = df["supplier_id"].str.upper()

        df["other_tax"] = df["other_tax"].fillna(0)

        df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")

        df["date_accepted"] = pd.to_datetime(
            df["date_accepted"], format="%d/%m/%Y %H:%M:%S")

        df["date"] = (
            (df["date"] + pd.Timedelta(hours=6))
            .dt.tz_localize("America/Santiago") 
            .dt.tz_convert("UTC")
        )

        df["date_accepted"] = (
            df["date_accepted"]
            .dt.tz_localize("America/Santiago") 
            .dt.tz_convert("UTC")
        )

        df["type"] = df["type"].map({"p": "contado"}).fillna("")

        int_cols = ["exent_total", "net_total", "iva", "other_tax", "total"]

        for col in int_cols:
            df[col] = (
                df[col]
                .str.replace(".", "")
                    .fillna("0")
                    .astype(str)
                    .str.replace(".", "", regex=False)
                    .replace("", "0")
                    .astype("int64")
            )

        return df