from pathlib import Path


class ProgressStore:
    """
    Clase encargada de guardar el progreso temporal del scraper SII.

    Permite registrar qué usuarios ya fueron procesados durante una corrida,
    para evitar repetirlos si el proceso continúa después de un error parcial.
    """

    def __init__(self, file_path: str = "sii_progress.txt"):
        self.file_path = Path(file_path)

    def load_completed_users(self) -> set[str]:
        """
        Carga los usuarios que ya fueron procesados.

        Returns:
            set[str]: Conjunto de usuarios registrados como completados.
        """
        if not self.file_path.exists():
            return set()

        return set(
            line.strip()
            for line in self.file_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    def mark_user_completed(self, user: str) -> None:
        """
        Marca un usuario como procesado.

        Args:
            user: Usuario SII que se debe registrar como completado.

        Returns:
            None
        """
        with self.file_path.open("a", encoding="utf-8") as file:
            file.write(f"{user}\n")

    def clear(self) -> None:
        """
        Elimina el archivo de progreso.

        Returns:
            None
        """
        if self.file_path.exists():
            self.file_path.unlink()
