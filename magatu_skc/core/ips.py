"""IPSパッチ生成 - 元ROMと改造後ROMの差分パッチ"""


def create_ips_patch(original: bytes, modified: bytes) -> bytes:
    """元ROMと改造後ROMからIPSパッチを生成

    IPS形式:
        "PATCH" (5 bytes header)
        [3-byte offset][2-byte length][N-byte data] のレコードを連続
        "EOF"  (終端)

    Args:
        original: 元ROMのバイト列
        modified: 改造後ROMのバイト列

    Returns:
        IPSパッチのバイト列
    """
    # サイズが違っても許容（拡張ROM変換対応）
    # original より modified が大きい場合、拡張部分は丸ごと追加レコードとして書く

    result = bytearray(b"PATCH")

    common_len = min(len(original), len(modified))
    i = 0
    while i < common_len:
        # 差分の開始位置を探す
        if original[i] == modified[i]:
            i += 1
            continue

        start = i
        # 差分が連続する範囲を取得
        while i < common_len and original[i] != modified[i]:
            i += 1
        end = i

        # データを抽出
        diff_data = bytes(modified[start:end])
        offset = start

        # IPS は 3バイトオフセット + 2バイト長
        # 長さ 0xFFFF を超える場合は分割
        write_pos = 0
        while write_pos < len(diff_data):
            chunk = diff_data[write_pos:write_pos + 0xFFFF]
            chunk_offset = offset + write_pos
            # オフセット 0x454F46 ("EOF") は使えないので避ける
            if chunk_offset == 0x454F46:
                # 1バイト戻して開始 → ただし簡易対応：エラーにする
                raise ValueError("Cannot generate IPS: offset conflicts with EOF marker")

            result.append((chunk_offset >> 16) & 0xff)
            result.append((chunk_offset >> 8) & 0xff)
            result.append(chunk_offset & 0xff)
            result.append((len(chunk) >> 8) & 0xff)
            result.append(len(chunk) & 0xff)
            result.extend(chunk)
            write_pos += 0xFFFF

    # サイズ拡張部分: modified[common_len..] を 0xFFFF 単位の連続レコードとして書く
    if len(modified) > len(original):
        ext_offset = common_len
        ext_data = bytes(modified[common_len:])
        write_pos = 0
        while write_pos < len(ext_data):
            chunk = ext_data[write_pos:write_pos + 0xFFFF]
            chunk_offset = ext_offset + write_pos
            if chunk_offset == 0x454F46:
                raise ValueError("Cannot generate IPS: offset conflicts with EOF marker")
            result.append((chunk_offset >> 16) & 0xff)
            result.append((chunk_offset >> 8) & 0xff)
            result.append(chunk_offset & 0xff)
            result.append((len(chunk) >> 8) & 0xff)
            result.append(len(chunk) & 0xff)
            result.extend(chunk)
            write_pos += 0xFFFF

    result.extend(b"EOF")
    return bytes(result)


def save_ips_patch(original: bytes, modified: bytes, path: str):
    """IPSパッチをファイルに保存"""
    patch = create_ips_patch(original, modified)
    with open(path, "wb") as f:
        f.write(patch)


class IpsError(ValueError):
    """IPSパッチの形式不正・適用失敗 (フォールバック禁止・明示中止)"""


def parse_ips_records(patch: bytes) -> list:
    """IPSパッチを解析してレコード列を返す。

    Returns:
        [(offset, data_bytes), ...]  RLE は展開済バイト列にして返す。

    Raises:
        IpsError: "PATCH" ヘッダ無し / 途中で壊れている等
    """
    if patch[:5] != b"PATCH":
        raise IpsError("IPS ヘッダ \"PATCH\" がありません (不正な .ips)。")
    recs = []
    i = 5
    n = len(patch)
    while i + 3 <= n:
        if patch[i:i + 3] == b"EOF":
            i += 3
            return recs
        offset = (patch[i] << 16) | (patch[i + 1] << 8) | patch[i + 2]
        i += 3
        if i + 2 > n:
            raise IpsError("IPS レコードが途中で切れています (size欠落)。")
        size = (patch[i] << 8) | patch[i + 1]
        i += 2
        if size == 0:  # RLE レコード
            if i + 3 > n:
                raise IpsError("IPS RLE レコードが途中で切れています。")
            rle = (patch[i] << 8) | patch[i + 1]
            val = patch[i + 2]
            i += 3
            recs.append((offset, bytes([val]) * rle))
        else:
            if i + size > n:
                raise IpsError("IPS データレコードが途中で切れています。")
            recs.append((offset, bytes(patch[i:i + size])))
            i += size
    # EOF を見ずに末尾へ達した = 破損 (フォールバックせず中止)
    raise IpsError("IPS が \"EOF\" 終端なしで終わっています (破損の可能性)。")


def apply_ips_patch(rom_data, patch: bytes,
                     max_total_size: int = 1 << 24) -> bytearray:
    """ROM バイト列に IPS パッチを適用した新しい bytearray を返す。

    - RLE 対応。ROM 末尾を越えるレコードは標準 IPS 同様に伸長。
    - 異常 (ヘッダ無し・破損・極端な肥大) は IpsError で中止
      (CLAUDE.md: フォールバック禁止・明示エラー)。

    Args:
        rom_data: 元 ROM (bytes / bytearray)
        patch:    .ips のバイト列
        max_total_size: 伸長後の上限 (暴走 .ips 防御)
    """
    recs = parse_ips_records(patch)
    if not recs:
        raise IpsError("IPS にレコードがありません (空パッチ)。")
    out = bytearray(rom_data)
    for offset, data in recs:
        end = offset + len(data)
        if end > max_total_size:
            raise IpsError(
                f"IPS が ROM を {end} バイトへ肥大させようとしました "
                f"(上限 {max_total_size})。安全のため中止。")
        if end > len(out):
            out.extend(b"\x00" * (end - len(out)))
        out[offset:end] = data
    return out
