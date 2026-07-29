from nasagent.llm.messages import ChatMessage


def test_chat_message_to_openai_dict() -> None:
    message = ChatMessage(role="user", content="check storage")

    assert message.to_openai_dict() == {"role": "user", "content": "check storage"}
