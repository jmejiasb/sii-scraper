import logging

import pandas as pd
from pymongo.database import Database


class InvoiceRepository:
    """
    Repositorio encargado de sincronizar facturas de proveedores en MongoDB.

    Centraliza las operaciones contra la colección invoices_supplier, insertando
    documentos nuevos y actualizando el estado de documentos ya existentes.
    """

    def __init__(self, db: Database):
        """
        Inicializa el repositorio de facturas.

        Args:
            db: Instancia de la base de datos MongoDB.
        """
        self.inv_supplier = db.invoices_supplier
        self.log = logging.getLogger(self.__class__.__name__)

    def sync_invoices(self, df: pd.DataFrame) -> tuple[int, int]:
        """
        Sincroniza facturas limpias con MongoDB.

        Para cada factura, busca un documento existente usando supplier_id y
        number. Si existe, actualiza su estado. Si no existe, inserta el
        documento completo.

        Args:
            df: DataFrame de facturas limpio y normalizado.

        Returns:
            tuple[int, int]: Cantidad de facturas insertadas y actualizadas.
        """
        if df.empty:
            return 0, 0

        inserted = 0
        updated = 0

        for _, row in df.iterrows():
            data = row.to_dict()

            filt = {
                "supplier_id": data["supplier_id"],
                "number": data["number"],
            }

            result = self.inv_supplier.update_one(
                filt,
                {"$set": {"status": data["status"]}},
            )

            if result.matched_count:
                updated += 1
            else:
                self.inv_supplier.insert_one(data)
                inserted += 1

        self.log.info(
            f"Sincronización finalizada. Insertadas: {inserted}, actualizadas: {updated}"
        )

        return inserted, updated
