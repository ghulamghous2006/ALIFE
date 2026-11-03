"""Controlled configuration for website and application tools."""

WEBSITE_REGISTRY: dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "leetcode": "https://leetcode.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
}

APPLICATION_REGISTRY: dict[str, str] = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "vscode": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "whatsapp": r"C:\Users\%USERNAME%\AppData\Local\WhatsApp\WhatsApp.exe",
}


def normalize_key(value: str) -> str:
    """Normalize a lookup key for websites and applications."""
    return value.strip().lower().replace(" ", "").replace("-", "").replace("_", "")


def resolve_website(name: str) -> str | None:
    """Resolve a website name to an approved URL."""
    key = normalize_key(name)
    for registry_key, url in WEBSITE_REGISTRY.items():
        if normalize_key(registry_key) == key:
            return url
    return None


def resolve_application(name: str) -> str | None:
    """Resolve an application name to a configured executable path."""
    key = normalize_key(name)
    aliases = {
        "vscode": "vscode",
        "visualstudiocode": "vscode",
        "code": "vscode",
        "chrome": "chrome",
        "googlechrome": "chrome",
        "whatsapp": "whatsapp",
    }
    registry_key = aliases.get(key, key)
    return APPLICATION_REGISTRY.get(registry_key)
