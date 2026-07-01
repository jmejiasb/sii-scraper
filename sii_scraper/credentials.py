import os
import re


class Credentials:
    """
    Clase encargada de cargar credenciales SII desde variables de entorno.

    Busca pares SII_USER_N / SII_PASS_N y retorna un diccionario con usuario y
    contraseña para cada cuenta configurada.
    """

    def load_all_credentials(self) -> dict[str, str]:
        """
        Carga todas las credenciales SII disponibles en variables de entorno.

        Busca variables con formato SII_USER_N y su contraseña correspondiente
        SII_PASS_N, usando el mismo número N para emparejarlas.

        Returns:
            dict[str, str]: Diccionario donde la llave es el usuario SII y el
            valor es su contraseña.
        """
        creds = {}

        for var, val in os.environ.items():
            match = re.match(r"SII_USER_(\d+)", var)

            if not match:
                continue

            idx = match.group(1)
            user = val
            password = os.getenv(f"SII_PASS_{idx}")

            if password:
                creds[user] = password

        return creds