from __future__ import annotations

from dataclasses import dataclass
import os
import re
import tempfile
from pathlib import Path
from typing import Optional


try:  # pragma: no cover - platform specific dependency
    import pythoncom  # type: ignore
except Exception:  # pragma: no cover - pythoncom is optional outside Windows
    pythoncom = None


HEADER_PREFIX_LEN = 28


def _decode_signed_value(reader: "_ByteReader") -> int:
    first = reader.read_u8()
    if first != 255:
        return first - 128

    low = reader.read_u8()
    high = reader.read_u8()
    return ((high << 8) | low) - 32768


def _decode_unsigned_value(reader: "_ByteReader") -> int:
    first = reader.read_u8()
    if first != 255:
        return first

    low = reader.read_u8()
    high = reader.read_u8()
    return (high << 8) | low


def _superscript_text(text: str) -> str:
    mapping = {
        "0": "⁰",
        "1": "¹",
        "2": "²",
        "3": "³",
        "4": "⁴",
        "5": "⁵",
        "6": "⁶",
        "7": "⁷",
        "8": "⁸",
        "9": "⁹",
        "+": "⁺",
        "-": "⁻",
        "=": "⁼",
        "(": "⁽",
        ")": "⁾",
        "n": "ⁿ",
        "i": "ⁱ",
        "′": "′",
        "″": "″",
    }
    if text and all(ch in mapping for ch in text):
        return "".join(mapping[ch] for ch in text)
    return f"^({text})" if text else ""


def _subscript_text(text: str) -> str:
    mapping = {
        "0": "₀",
        "1": "₁",
        "2": "₂",
        "3": "₃",
        "4": "₄",
        "5": "₅",
        "6": "₆",
        "7": "₇",
        "8": "₈",
        "9": "₉",
        "+": "₊",
        "-": "₋",
        "=": "₌",
        "(": "₍",
        ")": "₎",
        "a": "ₐ",
        "e": "ₑ",
        "h": "ₕ",
        "i": "ᵢ",
        "j": "ⱼ",
        "k": "ₖ",
        "l": "ₗ",
        "m": "ₘ",
        "n": "ₙ",
        "o": "ₒ",
        "p": "ₚ",
        "r": "ᵣ",
        "s": "ₛ",
        "t": "ₜ",
        "u": "ᵤ",
        "v": "ᵥ",
        "x": "ₓ",
    }
    if text and all(ch in mapping for ch in text):
        return "".join(mapping[ch] for ch in text)
    return f"_({text})" if text else ""


@dataclass
class _ByteReader:
    data: bytes
    pos: int = 0
    _pending_nibble_byte: int | None = None

    def eof(self) -> bool:
        return self.pos >= len(self.data)

    def read_u8(self) -> int:
        if self.pos >= len(self.data):
            raise EOFError("unexpected end of MTEF stream")
        value = self.data[self.pos]
        self.pos += 1
        return value

    def peek_u8(self) -> int:
        if self.pos >= len(self.data):
            return 0
        return self.data[self.pos]

    def read_bytes(self, length: int) -> bytes:
        if self.pos + length > len(self.data):
            raise EOFError("unexpected end of MTEF stream")
        chunk = self.data[self.pos : self.pos + length]
        self.pos += length
        return chunk

    def read_nibble(self) -> int:
        if self._pending_nibble_byte is None:
            self._pending_nibble_byte = self.read_u8()
            return self._pending_nibble_byte >> 4

        nibble = self._pending_nibble_byte & 0x0F
        self._pending_nibble_byte = None
        return nibble

    def align_to_byte(self) -> None:
        self._pending_nibble_byte = None

    def read_cstring(self) -> str:
        start = self.pos
        while self.pos < len(self.data) and self.data[self.pos] != 0:
            self.pos += 1
        text = self.data[start : self.pos].decode("latin1", errors="ignore")
        if self.pos < len(self.data):
            self.pos += 1
        return text

    def read_nudge(self) -> None:
        dx = self.read_u8()
        dy = self.read_u8()
        if dx == 128 and dy == 128:
            self.read_u8()
            self.read_u8()
            self.read_u8()
            self.read_u8()

    def read_simple_u16(self) -> int:
        low = self.read_u8()
        high = self.read_u8()
        return (high << 8) | low

    def read_variation(self) -> int:
        first = self.read_u8()
        if first & 0x80:
            second = self.read_u8()
            return (first & 0x7F) | (second << 8)
        return first

    def skip_dimensional_array(self) -> None:
        count = self.read_u8()
        for _ in range(count):
            self.read_nibble()
            while True:
                nibble = self.read_nibble()
                if nibble == 0xF:
                    break
        self.align_to_byte()


def _skip_eqn_prefs(reader: _ByteReader) -> None:
    reader.read_u8()  # options, unused in v5
    reader.skip_dimensional_array()
    reader.skip_dimensional_array()

    style_count = reader.read_u8()
    for _ in range(style_count):
        index = _decode_unsigned_value(reader)
        if index != 0:
            reader.read_u8()


def _skip_font_style_def(reader: _ByteReader) -> None:
    _decode_unsigned_value(reader)
    reader.read_u8()


def _skip_font_def(reader: _ByteReader) -> None:
    _decode_unsigned_value(reader)
    reader.read_cstring()


def _skip_color_def(reader: _ByteReader) -> None:
    options = reader.read_u8()
    value_count = 4 if options & 0x01 else 3
    for _ in range(value_count):
        reader.read_simple_u16()
    if options & 0x04:
        reader.read_cstring()


def _skip_color(reader: _ByteReader) -> None:
    _decode_unsigned_value(reader)


def _skip_ruler(reader: _ByteReader) -> None:
    stop_count = reader.read_u8()
    for _ in range(stop_count):
        reader.read_u8()
        reader.read_simple_u16()


def _skip_future_record(reader: _ByteReader) -> None:
    length = _decode_unsigned_value(reader)
    reader.read_bytes(length)


def _parse_char(reader: _ByteReader, options: int) -> str:
    if options & 0x08:
        reader.read_nudge()

    _decode_signed_value(reader)  # typeface

    mt_code = None
    font_8 = None
    font_16 = None

    if not options & 0x20:
        mt_code = reader.read_simple_u16()
    if options & 0x04:
        font_8 = reader.read_u8()
    if options & 0x10:
        font_16 = reader.read_simple_u16()

    if mt_code is not None and mt_code != 0:
        special = {
            0x2212: "−",
            0x00B1: "±",
            0x2032: "′",
            0x02B9: "′",
            0x2019: "′",
            0x00B4: "′",
        }
        result = special.get(mt_code, chr(mt_code))
        if options & 0x01:
            # Preserve embellishment records by parsing them into the current token
            # sequence instead of discarding them. Some exam equations encode prime
            # marks and trailing formula pieces through this path.
            embellished_tokens = [result] if result else []
            try:
                while reader.peek_u8() != 0:
                    _parse_record(reader, embellished_tokens, stop_at_end=True)
                if reader.peek_u8() == 0:
                    reader.read_u8()
            except EOFError:
                return "".join(embellished_tokens)
            return "".join(embellished_tokens)
        return result

    if font_16 is not None:
        return chr(font_16)
    if font_8 is not None:
        return chr(font_8)

    result = ""
    if mt_code is not None:
        result = chr(mt_code)

    if options & 0x01:
        # Preserve embellishment records by parsing them into the current token
        # sequence instead of discarding them. Some exam equations encode prime
        # marks and trailing formula pieces through this path.
        embellished_tokens = [result] if result else []
        try:
            while reader.peek_u8() != 0:
                _parse_record(reader, embellished_tokens, stop_at_end=True)
            if reader.peek_u8() == 0:
                reader.read_u8()
        except EOFError:
            return "".join(embellished_tokens)
        return "".join(embellished_tokens)

    return result


def _parse_line(reader: _ByteReader, options: int) -> str:
    if options & 0x08:
        reader.read_nudge()
    if options & 0x04:
        reader.read_simple_u16()
    if options & 0x02:
        _skip_ruler(reader)
    if options & 0x01:
        return ""

    tokens: list[str] = []
    _parse_object_list(reader, tokens)
    return "".join(tokens)


def _parse_pile(reader: _ByteReader, options: int) -> str:
    if options & 0x08:
        reader.read_nudge()
    reader.read_u8()  # halign
    reader.read_u8()  # valign
    if options & 0x02:
        _skip_ruler(reader)

    lines: list[str] = []
    _parse_object_list(reader, lines)
    return "\n".join(line for line in lines if line)


def _parse_matrix(reader: _ByteReader, options: int) -> str:
    if options & 0x08:
        reader.read_nudge()
    reader.read_u8()  # valign
    reader.read_u8()  # h_just
    reader.read_u8()  # v_just
    rows = _decode_unsigned_value(reader)
    cols = _decode_unsigned_value(reader)
    reader.read_u8()  # row_parts
    reader.read_u8()  # col_parts

    cells: list[str] = []
    _parse_object_list(reader, cells)
    if rows and cols and len(cells) >= rows * cols:
        rendered_rows = []
        index = 0
        for _ in range(rows):
            rendered_rows.append(" | ".join(cells[index : index + cols]))
            index += cols
        return " ; ".join(rendered_rows)
    return " ".join(cell for cell in cells if cell)


def _parse_embell(reader: _ByteReader, options: int, out_tokens: list[str]) -> str:
    if options & 0x08:
        reader.read_nudge()
    embellishment_code = reader.read_u8()
    if options & 0x01:
        _parse_object_list(reader, [])
    text_tokens: list[str] = []
    _parse_object_list(reader, text_tokens)

    # Some MathType prime/mark embellishments are encoded as empty embellishment
    # records that modify the previous token rather than contributing text on
    # their own. Preserve the preceding symbol instead of dropping the mark.
    if not text_tokens and embellishment_code == 5 and out_tokens:
        out_tokens[-1] = f"{out_tokens[-1]}′"
        return ""

    return "".join(text_tokens)


def _first_non_empty(values: list[str]) -> str:
    for value in values:
        if value:
            return value
    return ""


def _normalize_fraction_like(text: str) -> str:
    normalized = re.sub(r"\s+", "", text)
    if not normalized:
        return ""

    match = re.fullmatch(r"\((.+)\)/\((.+)\)", normalized)
    if match:
        return f"{match.group(1)}/{match.group(2)}"

    if "/" in normalized:
        return normalized

    if len(normalized) >= 4 and normalized[-2:].isalpha() and normalized[-2:] == normalized[-2:].upper():
        return f"{normalized[:-2]}/{normalized[-2:]}"

    return normalized


def _wrap_fraction_side_if_needed(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return text

    compact = re.sub(r"\s+", "", stripped)
    if len(compact) >= 2 and compact[0] == "(" and compact[-1] == ")":
        depth = 0
        for index, char in enumerate(compact):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(compact) - 1:
                    break
        else:
            return stripped

    depth = 0
    for char in compact:
        if char in "([{":
            depth += 1
            continue
        if char in ")]}":
            depth = max(depth - 1, 0)
            continue
        if depth == 0 and char in "+-\u2212\u00b7\u22c5*/":
            return f"({stripped})"

    return stripped


def _parse_template(reader: _ByteReader, options: int, out_tokens: list[str]) -> None:
    if options & 0x08:
        reader.read_nudge()

    selector = reader.read_u8()
    variation = reader.read_variation()
    template_options = reader.read_u8()
    slots: list[str] = []
    _parse_object_list(reader, slots)

    if selector in {27, 28, 29}:
        base = out_tokens.pop() if out_tokens else ""
        sub = _first_non_empty(slots[:1])
        sup = _first_non_empty(slots[1:2]) if len(slots) > 1 else ""
        if selector == 27:
            out_tokens.append(f"{base}{_subscript_text(sub)}")
            return
        if selector == 28:
            out_tokens.append(f"{base}{_superscript_text(sup or sub)}")
            return
        out_tokens.append(f"{base}{_subscript_text(sub)}{_superscript_text(sup)}")
        return

    if selector == 10:
        if variation == 1:
            index = _first_non_empty(slots[:1])
            radicand = _first_non_empty(slots[1:]) or _first_non_empty(slots[:1])
            if index:
                out_tokens.append(f"√[{index}]({radicand})")
            else:
                out_tokens.append(f"√({radicand})")
        else:
            radicand = _first_non_empty(slots)
            out_tokens.append(f"√{radicand}" if radicand else "√()")
        return

    if selector == 11:
        numerator = _first_non_empty(slots[:1])
        denominator = _first_non_empty(slots[1:2] if len(slots) > 1 else [])
        if len(slots) == 3 and slots[1] == "=":
            left = _normalize_fraction_like(slots[0])
            right = _normalize_fraction_like(slots[2])
            if left and right:
                out_tokens.append(f"{left}={right}")
                return
        if numerator and denominator:
            out_tokens.append(
                f"{_wrap_fraction_side_if_needed(_normalize_fraction_like(numerator))}/"
                f"{_wrap_fraction_side_if_needed(_normalize_fraction_like(denominator))}"
            )
        else:
            out_tokens.append(_normalize_fraction_like(numerator or denominator))
        return

    if selector in {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}:
        left_map = {
            0: "⟨",
            1: "(",
            2: "{",
            3: "[",
            4: "|",
            5: "‖",
            6: "⌊",
            7: "⌈",
            8: "⟦",
            9: "(",
        }
        right_map = {
            0: "⟩",
            1: ")",
            2: "}",
            3: "]",
            4: "|",
            5: "‖",
            6: "⌋",
            7: "⌉",
            8: "⟧",
            9: ")",
        }
        main = _first_non_empty(slots[:1])
        out_tokens.append(f"{left_map.get(selector, '(')}{main}{right_map.get(selector, ')')}")
        return

    if selector == 15:
        main = _first_non_empty(slots[:1])
        out_tokens.append(main)
        return

    out_tokens.append("".join(slot for slot in slots if slot))


def _parse_record(reader: _ByteReader, out_tokens: list[str], stop_at_end: bool) -> bool:
    if reader.eof():
        return False

    record_type = reader.read_u8()
    if record_type == 0:
        return False

    if record_type == 10 or record_type == 11 or record_type == 12 or record_type == 13 or record_type == 14:
        return True
    if record_type == 8:
        _skip_font_style_def(reader)
        return True
    if record_type == 15:
        _skip_color(reader)
        return True
    if record_type == 16:
        _skip_color_def(reader)
        return True
    if record_type == 17:
        _skip_font_def(reader)
        return True
    if record_type == 18:
        _skip_eqn_prefs(reader)
        return True
    if record_type == 19:
        reader.read_cstring()
        return True
    if record_type >= 100:
        _skip_future_record(reader)
        return True

    options = reader.read_u8()
    if record_type == 1:
        out_tokens.append(_parse_line(reader, options))
        return True
    if record_type == 2:
        out_tokens.append(_parse_char(reader, options))
        return True
    if record_type == 3:
        _parse_template(reader, options, out_tokens)
        return True
    if record_type == 4:
        out_tokens.append(_parse_pile(reader, options))
        return True
    if record_type == 5:
        out_tokens.append(_parse_matrix(reader, options))
        return True
    if record_type == 6:
        out_tokens.append(_parse_embell(reader, options, out_tokens))
        return True
    if record_type == 7:
        _skip_ruler(reader)
        return True

    return True


def _parse_object_list(reader: _ByteReader, out_tokens: list[str]) -> None:
    while not reader.eof():
        if reader.peek_u8() == 0:
            reader.read_u8()
            return
        if not _parse_record(reader, out_tokens, stop_at_end=True):
            return


def _parse_equation_native_stream(stream_bytes: bytes) -> str | None:
    if len(stream_bytes) <= HEADER_PREFIX_LEN:
        return None

    reader = _ByteReader(stream_bytes)
    reader.pos = HEADER_PREFIX_LEN

    try:
        version = reader.read_u8()
        if version != 5:
            return None
        reader.read_u8()  # generating platform
        reader.read_u8()  # generating product
        reader.read_u8()  # product version
        reader.read_u8()  # product subversion
        reader.read_cstring()  # app key
        reader.read_u8()  # equation options

        tokens: list[str] = []
        while not reader.eof():
            if reader.peek_u8() == 0:
                reader.read_u8()
                break
            if not _parse_record(reader, tokens, stop_at_end=False):
                break

        text = "".join(tokens).strip()
        return text or None
    except EOFError:
        text = "".join(tokens).strip()
        return text or None
    except ValueError:
        return None


def _read_equation_native_stream(ole_bytes: bytes) -> Optional[bytes]:
    if pythoncom is None:  # pragma: no cover - handled in runtime tests
        return None

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as temp_file:
            temp_file.write(ole_bytes)
            temp_path = Path(temp_file.name)

        storage = pythoncom.StgOpenStorage(str(temp_path), None, 0x20)
        enum = storage.EnumElements(0)
        while True:
            item = enum.Next(1)
            if not item:
                break
            name, *_rest = item[0]
            if name != "Equation Native":
                continue
            stream = storage.OpenStream(name, None, 0x10, 0)
            return stream.Read(1024 * 1024)
    except Exception:
        return None
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def extract_mathtype_equation_text(ole_bytes: bytes) -> str | None:
    native_stream = _read_equation_native_stream(ole_bytes)
    if not native_stream:
        return None

    return _parse_equation_native_stream(native_stream)
