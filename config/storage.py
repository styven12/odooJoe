"""
Stockage des fichiers statiques tolérant aux manifestes absents ou périmés.

En production (Render), collectstatic s'exécute au build et au démarrage, le
manifeste est donc présent et les URL hachées servies normalement. Ce
sous-classement évite toutefois tout crash 500 (ValueError « could not be
found with ...ManifestStaticFilesStorage ») si une entrée ou le fichier manque
(ex. collectstatic pas encore exécuté) : l'URL non hachée est renvoyée à la
place, la page s'affiche sans CSS au pire cas.
"""
from whitenoise.storage import CompressedManifestStaticFilesStorage


class TolerantManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError:
            # Manifeste absent ou entrée manquante : URL non hachée.
            return name

    def url(self, name, force=False):
        try:
            return super().url(name, force=force)
        except ValueError:
            return self.base_url + name
