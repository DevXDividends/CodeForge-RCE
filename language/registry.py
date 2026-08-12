from .config import LanguageConfig


class LanguageRegistry:

    def __init__(self):
        self._languages: dict[str, LanguageConfig] = {}

    def register(
        self,
        config: LanguageConfig,
    ):

        key = config.name.lower()

        self._languages[key] = config

    def get(
        self,
        language: str,
    ) -> LanguageConfig:

        key = language.lower()

        if key not in self._languages:
            raise ValueError(
                f"Unsupported language: {language}"
            )

        return self._languages[key]

    def supported_languages(self):
        return list(
            self._languages.keys()
        )