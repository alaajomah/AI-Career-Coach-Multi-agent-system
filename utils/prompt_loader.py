from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

def load_prompt(filename: str):
    template = Path(f"prompts/{filename}").read_text(encoding="utf-8")
    return ChatPromptTemplate.from_template(template)