from __future__ import annotations

from typing import Optional

import pytest

from pygoose import Document, Encrypted, encryption
from pygoose.fields.encrypted import (
    EncryptionKeyNotSet,
    decrypt_value,
    encrypt_value,
    generate_encryption_key,
    rotate_encryption_key,
)


@pytest.fixture(autouse=True)
def reset_key():
    """Reset encryption key before and after each test."""
    encryption.reset()
    yield
    encryption.reset()


class SecretDoc(Document):
    name: str
    ssn: Encrypted[str]


class OptionalSecretDoc(Document):
    name: str
    ssn: Optional[Encrypted[str]] = None


async def test_set_and_get_encryption_key():
    key = generate_encryption_key()
    encryption.set_key(key)
    assert encryption.get_key() == key.encode()


async def test_generate_key_valid():
    key = generate_encryption_key()
    # Fernet keys are 44 chars base64
    assert len(key) == 44


async def test_encrypt_decrypt_roundtrip():
    encryption.set_key(generate_encryption_key())
    ct = encrypt_value("secret123")
    assert ct != "secret123"
    assert decrypt_value(ct) == "secret123"


async def test_encrypted_field_stored_as_ciphertext():
    encryption.set_key(generate_encryption_key())
    doc = await SecretDoc.create(name="Alice", ssn="123-45-6789")

    # Read raw from collection
    raw = await SecretDoc.get_collection().find_one({"_id": doc.id})
    assert raw["ssn"] != "123-45-6789"
    assert raw["name"] == "Alice"


async def test_encrypted_field_decrypted_on_load():
    encryption.set_key(generate_encryption_key())
    doc = await SecretDoc.create(name="Alice", ssn="123-45-6789")

    loaded = await SecretDoc.get(doc.id)
    assert loaded.ssn == "123-45-6789"


async def test_encrypted_field_update_via_save():
    encryption.set_key(generate_encryption_key())
    doc = await SecretDoc.create(name="Alice", ssn="123-45-6789")

    raw_before = await SecretDoc.get_collection().find_one({"_id": doc.id})

    loaded = await SecretDoc.get(doc.id)
    loaded.ssn = "999-99-9999"
    await loaded.save()

    raw_after = await SecretDoc.get_collection().find_one({"_id": doc.id})
    assert raw_after["ssn"] != raw_before["ssn"]
    assert raw_after["ssn"] != "999-99-9999"

    reloaded = await SecretDoc.get(doc.id)
    assert reloaded.ssn == "999-99-9999"


async def test_no_key_raises():
    with pytest.raises(EncryptionKeyNotSet):
        await SecretDoc.create(name="Alice", ssn="123-45-6789")


async def test_encrypted_none_skipped():
    encryption.set_key(generate_encryption_key())
    doc = await OptionalSecretDoc.create(name="Alice")

    raw = await OptionalSecretDoc.get_collection().find_one({"_id": doc.id})
    assert raw.get("ssn") is None

    loaded = await OptionalSecretDoc.get(doc.id)
    assert loaded.ssn is None


async def test_key_rotation():
    key_a = generate_encryption_key()
    key_b = generate_encryption_key()

    encryption.set_key(key_a)
    doc = await SecretDoc.create(name="Alice", ssn="123-45-6789")

    count = await rotate_encryption_key(SecretDoc, key_a, key_b)
    assert count == 1

    # Key B is now active after rotation
    loaded = await SecretDoc.get(doc.id)
    assert loaded.ssn == "123-45-6789"


async def test_encrypted_field_not_queryable():
    encryption.set_key(generate_encryption_key())
    await SecretDoc.create(name="Alice", ssn="123-45-6789")

    # Querying by plaintext won't match (stored as ciphertext)
    result = await SecretDoc.find_one(ssn="123-45-6789")
    assert result is None
