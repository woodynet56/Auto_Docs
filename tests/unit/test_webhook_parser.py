from app.services.webhook_parser import parse_whatsapp_messages


def synthetic_payload(message_type: str = "document") -> dict[str, object]:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"display_phone_number": "15550001000"},
                            "messages": [
                                {
                                    "id": "wamid.SYNTHETIC001",
                                    "from": "15550002000",
                                    "timestamp": "1785800000",
                                    "type": message_type,
                                    "context": {"id": "wamid.SYNTHETIC000"},
                                    "text": {"body": "must not be retained"},
                                }
                            ],
                        },
                    }
                ]
            }
        ],
    }


def test_parser_extracts_only_required_metadata() -> None:
    messages = parse_whatsapp_messages(synthetic_payload())
    assert len(messages) == 1
    assert messages[0].provider_message_id == "wamid.SYNTHETIC001"
    assert messages[0].context_message_id == "wamid.SYNTHETIC000"
    assert "must not be retained" not in messages[0].model_dump_json()
    assert messages[0].content is not None
    assert messages[0].content.get_secret_value() == "must not be retained"


def test_parser_ignores_statuses_and_invalid_messages() -> None:
    assert parse_whatsapp_messages({"object": "other"}) == []
    assert parse_whatsapp_messages({"object": "whatsapp_business_account", "entry": "bad"}) == []
    assert parse_whatsapp_messages(synthetic_payload("location")) == []
    payload = synthetic_payload()
    payload["entry"][0]["changes"][0]["value"]["messages"][0]["timestamp"] = "invalid"  # type: ignore[index]
    assert parse_whatsapp_messages(payload) == []
