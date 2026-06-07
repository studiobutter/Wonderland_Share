"""Translation utility module for multi-language support."""
import json
import logging
from pathlib import Path
from typing import Dict, Optional

import discord
from discord import app_commands

LOCALES_PATH = Path("locales")
logger = logging.getLogger(__name__)

class Translator(app_commands.Translator):
    """Custom translator class that implements discord.app_commands.Translator."""
    _instance = None
    _translations: Dict[str, Dict[str, str]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Translator, cls).__new__(cls)
            cls._instance._load_translations()
        return cls._instance

    def _load_translations(self):
        """Loads translation files from the locales directory."""
        for file in LOCALES_PATH.glob("*.json"):
            lang = file.stem
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self._translations[lang] = json.load(f)
                logger.info("Loaded translations for: %s", lang)
            except Exception as e: # pylint: disable=broad-exception-caught
                logger.error("Failed to load translations for %s: %s", lang, e)

    def get_lang_code(self, locale: discord.Locale) -> str:
        """Maps a Discord locale to a supported language code."""
        val = str(locale).lower()
        
        # English variants
        if val.startswith('en'):
            return "en"
        
        # Traditional Chinese variants
        if val in ('zh-tw', 'zh-hk', 'zh-mo'):
            return "zh-TW"
        
        # Vietnamese
        if val == 'vi':
            return "vi"
        
        # Specific enum check as fallback
        if locale in (discord.Locale.taiwan_chinese, discord.Locale.hong_kong_chinese):
            return "zh-TW"
        if locale == discord.Locale.vietnamese:
            return "vi"
            
        return "en"

    def get_api_lang_code(self, lang_code: str, interaction: Optional[discord.Interaction] = None) -> str:
        """Resolves a bot language code to a HoYoLAB API compatible xx-xx locale."""
        if lang_code == "auto" and interaction:
            val = str(interaction.locale).lower()
            if val.startswith('en'): return "en-us"
            if val in ('zh-tw', 'zh-hk', 'zh-mo'): return "zh-tw"
            if val == 'vi': return "vi-vn"
            if val == 'ja': return "ja-jp"
            if val == 'ko': return "ko-kr"
            if val == 'fr': return "fr-fr"
            if val == 'de': return "de-de"
            if val == 'es': return "es-es"
            if val == 'pt': return "pt-pt"
            if val == 'ru': return "ru-ru"
            if val == 'th': return "th-th"
            if val == 'id': return "id-id"
            if val.startswith('zh'): return "zh-cn"
            return "en-us"
        
        # Map supported bot languages to their API equivalents
        mapping = {
            "en": "en-us",
            "zh-TW": "zh-tw",
            "vi": "vi-vn"
        }
        return mapping.get(lang_code, "en-us")

    async def translate(self, string: app_commands.locale_str, locale: discord.Locale, 
                        context: app_commands.TranslationContext) -> Optional[str]:
        """Translates a string into the target locale."""
        try:
            # Don't translate command or parameter names to avoid invalid names
            if context.location in (app_commands.TranslationContextLocation.command_name, 
                                    app_commands.TranslationContextLocation.parameter_name,
                                    app_commands.TranslationContextLocation.group_name):
                return None

            lang = self.get_lang_code(locale)
            translation = self.get_translation(string.message, lang)
            
            # If translation is the same as the key, return None to let Discord handle it
            if translation == string.message:
                return None
                
            return translation
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Error in translate method (locale=%s, key=%s): %s", 
                         locale, string.message, e)
            return None

    def get_translation(self, key: str, lang: str = "en") -> str:
        """Gets a translation for a specific key and language."""
        # Fallback to English if language not found
        translations = self._translations.get(lang, self._translations.get("en", {}))
        return translations.get(key, self._translations.get("en", {}).get(key, key))

translator = Translator()

def _(key: str, lang: str = "en", interaction: Optional[discord.Interaction] = None) -> str:
    """Helper function to translate a key."""
    try:
        if lang == "auto" and interaction:
            lang = translator.get_lang_code(interaction.locale)
        elif lang == "auto":
            lang = "en"
        return translator.get_translation(key, lang)
    except Exception: # pylint: disable=broad-exception-caught
        return key
