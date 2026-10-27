from dataclasses import dataclass, field


@dataclass
class Document:
    id: str       # из шапки файла: "account"
    title: str    # "Managing your account"
    body: str     # всё после шапки
    path: str     # "kb/12_account.md"


@dataclass
class Chunk:
    id: str       # "account#closing-my-account"
    doc_id: str   # "account"
    text: str     # "Managing your account › Closing my account\n..."
    metadata: dict = field(default_factory=dict)