import os
from yandex_cloud_ml_sdk import YCloudML


def generate_summary(transcribed_text: str, folder_id: str) -> str:
    api_key = os.environ.get("YANDEX_API_KEY")
    if not api_key:
        raise Exception("YANDEX_API_KEY environment variable must be set")
    
    sdk = YCloudML(folder_id=folder_id, auth=api_key)
    model = sdk.models.completions("yandexgpt")
    
    prompt = f"""Создай структурированный конспект лекции на основе следующей транскрипции:

{transcribed_text}

Конспект должен содержать:
- Основные темы и разделы
- Ключевые концепции и определения
- Важные выводы

Оформи конспект в ясной, организованной форме, подходящей для учебных заметок. Ответ должен быть на русском языке."""
    
    result = model.configure(temperature=0.6).run(prompt)
    
    for alternative in result:
        return alternative.text
    
    raise Exception("No summary generated")
