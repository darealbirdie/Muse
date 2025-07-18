import os
import json
from database import db  # Use your existing global db instance

TRANSLATIONS = {}

async def t(user_id: int, key: str, **kwargs) -> str:
    lang = await db.get_user_ui_language(user_id)
    if lang not in TRANSLATIONS:
        lang = "en"
    
    # Handle nested keys like "ACHIEVEMENTS.first_translation.name"
    keys = key.split('.')
    translations = TRANSLATIONS.get(lang, {})
    fallback_translations = TRANSLATIONS.get("en", {})
    
    # Navigate through nested structure
    for k in keys:
        if isinstance(translations, dict) and k in translations:
            translations = translations[k]
        else:
            translations = None
            break
    
    # If not found in user language, try English fallback
    if translations is None:
        translations = fallback_translations
        for k in keys:
            if isinstance(translations, dict) and k in translations:
                translations = translations[k]
            else:
                translations = key  # Return key if not found
                break
    
    # Format the message if it's a string
    if isinstance(translations, str):
        return translations.format(**kwargs)
    else:
        return str(translations)

def t_sync(lang: str, key: str, **kwargs) -> str:
    """Synchronous version for command registration"""
    if lang not in TRANSLATIONS:
        lang = "en"
    
    # Handle nested keys like "ACHIEVEMENTS.first_translation.name"
    keys = key.split('.')
    translations = TRANSLATIONS.get(lang, {})
    fallback_translations = TRANSLATIONS.get("en", {})
    
    # Navigate through nested structure
    for k in keys:
        if isinstance(translations, dict) and k in translations:
            translations = translations[k]
        else:
            translations = None
            break
    
    # If not found in user language, try English fallback
    if translations is None:
        translations = fallback_translations
        for k in keys:
            if isinstance(translations, dict) and k in translations:
                translations = translations[k]
            else:
                translations = key  # Return key if not found
                break
    
    # Format the message if it's a string
    if isinstance(translations, str):
        return translations.format(**kwargs)
    else:
        return str(translations)