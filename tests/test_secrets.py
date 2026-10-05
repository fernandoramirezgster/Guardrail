from app.detectors.secrets import SecretsDetector


def test_detects_aws_key():
    result = SecretsDetector().detect("AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF")
    assert result.detected


def test_detects_private_key():
    result = SecretsDetector().detect("-----BEGIN PRIVATE KEY-----")
    assert result.detected


def test_detects_password_assignment():
    result = SecretsDetector().detect("password=SuperSecret123")
    assert result.detected
