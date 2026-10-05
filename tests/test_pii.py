from app.detectors.pii import PIIDetector


def test_detects_email():
    result = PIIDetector().detect("Correo: usuario@example.com")
    assert result.detected
    assert any(m["type"] == "email" for m in result.matches)


def test_detects_colombian_phone():
    result = PIIDetector().detect("Teléfono: 300 123 4567")
    assert result.detected
    assert any(m["type"] == "phone" for m in result.matches)
    assert not any(m["type"] == "colombian_id" for m in result.matches)


def test_detects_colombian_phone_without_spaces():
    result = PIIDetector().detect("Teléfono: 3001234567")
    assert result.detected
    assert [m["type"] for m in result.matches] == ["phone"]


def test_detects_colombian_id_when_labeled():
    result = PIIDetector().detect("Cédula: 1234567890")
    assert result.detected
    assert any(m["type"] == "colombian_id" for m in result.matches)


def test_detects_standalone_colombian_id():
    result = PIIDetector().detect("Documento 123456789")
    assert result.detected
    assert any(m["type"] == "colombian_id" for m in result.matches)


def test_sanitizes_email():
    result = PIIDetector().detect("Contacto: usuario@example.com")
    assert "[REDACTED:email]" in result.sanitized
