"""SuteFoto T40X BLE protocol encoder.

Reverse engineered from BLE HCI snoop logs of the official "SS LED" app.
Every value below has been verified byte-for-byte against a real capture.

Envelope shared by all commands:
    FA <opcode> 00 00 00 <payload...> <checksum> 8A

checksum = sum(opcode byte + the three 00 bytes + payload) % 256
"""
from __future__ import annotations

HEADER = 0xFA
FOOTER = 0x8A

OPCODE_CCT = 0x06
OPCODE_HSI = 0x07
OPCODE_RGBCW = 0x08
OPCODE_FX = 0x09


def _build(opcode: int, payload: bytes) -> bytes:
    body = bytes([opcode, 0x00, 0x00, 0x00]) + payload
    checksum = sum(body) % 256
    return bytes([HEADER]) + body + bytes([checksum, FOOTER])


def build_hsi(intensity: int, hue: int, saturation: int) -> bytes:
    """intensity: 0-100, hue: 0-255 (degrees), saturation: 0-100."""
    intensity = max(0, min(100, int(intensity)))
    hue = max(0, min(255, int(hue)))
    saturation = max(0, min(100, int(saturation)))
    return _build(OPCODE_HSI, bytes([intensity, 0x00, hue, saturation]))


def build_cct(intensity: int, color_temp_k: int, gm_compensation: int) -> bytes:
    """intensity: 0-100, color_temp_k: 2800-10000, gm_compensation: -10..10."""
    intensity = max(0, min(100, int(intensity)))
    color_temp_k = max(2800, min(10000, int(color_temp_k)))
    gm_byte = int(gm_compensation) & 0xFF
    ct_hi = (color_temp_k >> 8) & 0xFF
    ct_lo = color_temp_k & 0xFF
    return _build(OPCODE_CCT, bytes([intensity, ct_hi, ct_lo, gm_byte]))


def build_rgbcw(
    red: int, green: int, blue: int, less_warm: int, more_warm: int
) -> bytes:
    """All params 0-100."""
    vals = [max(0, min(100, int(v))) for v in (red, green, blue, less_warm, more_warm)]
    return _build(OPCODE_RGBCW, bytes(vals))


def build_fx(effect_id: int, frequency: int, intensity: int) -> bytes:
    """effect_id: 1-10, frequency: 1-10, intensity: 10-100."""
    effect_id = max(1, min(10, int(effect_id)))
    frequency = max(1, min(10, int(frequency)))
    intensity = max(10, min(100, int(intensity)))
    return _build(OPCODE_FX, bytes([effect_id, frequency, intensity]))
